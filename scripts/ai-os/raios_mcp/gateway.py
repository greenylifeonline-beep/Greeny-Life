"""RAIOS MCP V1 gateway: 8 tools, Streamable HTTP, no second WAL, no shell."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = "greenylifeonline-beep/Greeny-Life"
BRANCH = "v9-neurolingua-semantic-kernel"
LAW = "MCP_GATEWAY_NE_TRUTH_AUTHORITY"
V1_TOOLS = (
    "get_head",
    "read_board",
    "read_inbox",
    "read_receipt",
    "get_diff",
    "post_opinion",
    "send_packet",
    "ack_packet",
)
WRITE_TOOLS = {"post_opinion", "send_packet", "ack_packet"}
WRITE_IDENTITY = (
    "actor_id",
    "actor_role",
    "instance_role",
    "session_id",
    "packet_id",
    "correlation_id",
    "repository",
    "branch",
    "requested_head",
    "authority_scope",
    "write_intent",
    "execution_intent",
    "promotion_intent",
    "created_at",
    "expires_at",
    "payload_hash",
)
SECRET_RE = re.compile(
    r"DATABASE_URL\s*=\s*\S+|APP_SESSION_SECRET\s*=\s*\S+|gl_session\s*=\s*\S+|postgres(?:ql)?://\S+",
    re.I,
)
BEARER_TOKEN_RE = re.compile(r"(?:^|[^A-Za-z])Bearer [A-Za-z0-9\-._~+/]{16,}")
PROVEN_TRUE_RE = re.compile(r"GL00[45]_PROVEN\s*=\s*true", re.I)


class GatewayError(Exception):
    def __init__(self, code: str, message: str, http: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.http = http


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_dt(value: str) -> datetime:
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    dt = datetime.fromisoformat(text)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(raw) for raw in path.read_text(encoding="utf-8").splitlines() if raw.strip()]


def append_jsonl(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(rec, ensure_ascii=False) + "\n")


def git(root: Path, *args: str) -> str:
    r = subprocess.run(["git", *args], cwd=root, text=True, capture_output=True)
    return (r.stdout or "").strip()


def mcp_to_opencode_seam(root: Path | None = None) -> dict[str, Any]:
    """Minimum existing MCP→OpenCode bind. Surfaces CODE_MODEL on get_head. No new tools. No shell."""
    binary = shutil.which("opencode")
    registry: dict[str, Any] = {}
    path = (root or Path.cwd()) / ".ai-os" / "MODEL-REGISTRY.json"
    if path.is_file():
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload = {}
        if isinstance(payload, dict):
            registry = payload
    declared = ((registry.get("bridges") or {}).get("execution") or {})
    return {
        "control_tool": "get_head",
        "control": "raios-mcp",
        "execution": "opencode",
        "uses_role": str(declared.get("uses_role") or "CODE_MODEL"),
        "present": binary is not None,
        "binary": binary,
        "install": False,
        "new_mcp_tools": False,
        "shell_via_mcp": False,
        "execution_proven": False,
        "mcp_tool_count": len(V1_TOOLS),
        "duplicate_mcp": False,
        "status": "BINARY_PRESENT_NOT_EXECUTED" if binary else str(declared.get("status") or "PREP_NOT_INSTALLED"),
        "declared_version": declared.get("declared_version"),
        "registry": ".ai-os/MODEL-REGISTRY.json",
    }


def payload_hash_of(arguments: dict) -> str:
    body = {k: arguments[k] for k in arguments if k not in {"payload_hash", "signature"}}
    return sha256_text(json.dumps(body, ensure_ascii=False, sort_keys=True, default=str))


@dataclass
class Actor:
    actor_id: str
    actor_role: str
    instance_role: str
    tools: list[str]
    deny: list[str]
    token_sha256: str
    scopes: list[str]
    expires_at: str | None


@dataclass
class Gateway:
    root: Path
    policy: dict
    actors: dict[str, Actor]
    audit_path: Path | None = None
    _packet_ids: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        self.audit_path = self.audit_path or (self.root / ".ai-os" / "mcp" / "AUDIT.jsonl")
        for row in load_jsonl(self.root / ".ai-os" / "mcp" / "packets.jsonl"):
            if row.get("packet_id"):
                self._packet_ids.add(row["packet_id"])

    @classmethod
    def from_root(cls, root: Path, tokens: dict[str, str] | None = None, grants: list[dict] | None = None) -> "Gateway":
        policy = load_json(root / ".ai-os" / "mcp" / "POLICY.json", {})
        loaded: list[dict] = list(grants or [])
        if tokens:
            loaded.extend({"actor_id": k, "token": v} for k, v in tokens.items())
        token_file = root / ".ai-os" / "mcp" / "tokens.local.json"
        if not loaded and token_file.exists():
            loaded = list(load_json(token_file, {}).get("actors") or [])
        token_by_id = {row["actor_id"]: row for row in loaded}
        actors = {}
        for actor_id, spec in (policy.get("actors") or {}).items():
            if actor_id == "C0":
                continue
            grant = token_by_id.get(actor_id) or {}
            policy_tools = list(spec.get("tools") or [])
            requested_scopes = list(grant.get("scopes") or policy_tools)
            scopes = [s for s in requested_scopes if s in policy_tools and s in V1_TOOLS]
            raw = str(grant.get("token") or "")
            actors[actor_id] = Actor(
                actor_id=actor_id,
                actor_role=spec["actor_role"],
                instance_role=spec["instance_role"],
                tools=policy_tools,
                deny=list(spec.get("deny") or []),
                token_sha256=sha256_text(raw) if raw else "",
                scopes=scopes,
                expires_at=grant.get("expires_at"),
            )
        return cls(root=root, policy=policy, actors=actors)

    def authenticate(self, token: str | None) -> Actor:
        if not token:
            raise GatewayError("UNAUTHENTICATED", "missing token", 401)
        digest = sha256_text(token)
        for actor in self.actors.values():
            if actor.token_sha256 and actor.token_sha256 == digest:
                if actor.actor_id == "C0":
                    raise GatewayError("C0_SEAT_ABOLISHED", "C0 is not a live seat", 403)
                if actor.expires_at and parse_dt(actor.expires_at) <= datetime.now(timezone.utc):
                    raise GatewayError("EXPIRED", "token expired", 401)
                return actor
        raise GatewayError("UNAUTHENTICATED", "unknown token", 401)

    def tool_schemas(self) -> list[dict]:
        return [
            {
                "name": name,
                "description": f"RAIOS V1 {name}. Streamable HTTP. {LAW}. Never writes GL005_PROVEN.",
                "inputSchema": {"type": "object", "additionalProperties": True},
            }
            for name in V1_TOOLS
        ]

    def call(self, actor: Actor, tool: str, arguments: dict[str, Any] | None) -> dict:
        arguments = dict(arguments or {})
        try:
            result = self._call(actor, tool, arguments)
            self._audit(actor, tool, "ok", arguments)
            return result
        except GatewayError as err:
            self._audit(actor, tool, err.code, arguments)
            raise

    def _call(self, actor: Actor, tool: str, arguments: dict[str, Any]) -> dict:
        forbidden = set(self.policy.get("forbidden_tools") or []) | {
            "shell",
            "bash",
            "run_command",
            "run_sandboxed_command",
        }
        if tool in forbidden:
            raise GatewayError("TOOL_NOT_FOUND", f"tool {tool} is not registered", 404)
        if tool not in V1_TOOLS:
            raise GatewayError("TOOL_NOT_FOUND", f"{tool} is not in V1", 404)
        if tool in actor.deny or tool not in actor.tools or tool not in actor.scopes:
            raise GatewayError("CAPABILITY_DENIED", f"{actor.actor_id} cannot {tool}", 403)
        self._bind_identity(actor, tool, arguments)
        return getattr(self, f"tool_{tool}")(actor, arguments)

    def _bind_identity(self, actor: Actor, tool: str, arguments: dict[str, Any]) -> None:
        if "head" in arguments and "requested_head" not in arguments:
            arguments["requested_head"] = arguments["head"]
        claimed = str(arguments.get("actor_id") or actor.actor_id).upper()
        if claimed == "C0":
            raise GatewayError("C0_SEAT_ABOLISHED", "C0 is not a live seat", 403)
        if claimed != actor.actor_id:
            raise GatewayError("IDENTITY_MISMATCH", "actor_id does not match token", 403)
        if arguments.get("actor_role") and str(arguments["actor_role"]).upper() != actor.actor_role.upper():
            raise GatewayError("ESCALATION_DENIED", "actor_role does not match token", 403)
        arguments["actor_id"] = actor.actor_id
        arguments["actor_role"] = actor.actor_role
        arguments.setdefault("instance_role", actor.instance_role)
        promo = str(arguments.get("promotion_intent") or "NONE").upper()
        if promo not in {"NONE", "NO", "FALSE"}:
            raise GatewayError("ESCALATION_DENIED", "promotion_intent is not allowed on the connector", 403)
        exec_intent = str(arguments.get("execution_intent") or "NONE").upper()
        if exec_intent not in {"NONE", "NO", "FALSE"}:
            raise GatewayError("ESCALATION_DENIED", "V1 connector does not execute", 403)
        if tool not in WRITE_TOOLS:
            return
        missing = [key for key in WRITE_IDENTITY if not str(arguments.get(key) or "").strip()]
        if missing:
            raise GatewayError("MISSING_IDENTITY", "missing " + ",".join(missing), 400)
        if arguments["packet_id"] == arguments["correlation_id"]:
            raise GatewayError("INVALID_PACKET", "packet_id must not equal correlation_id", 400)
        if arguments["packet_id"] in self._packet_ids:
            raise GatewayError("REPLAY", "packet_id already used", 409)
        if parse_dt(arguments["expires_at"]) <= datetime.now(timezone.utc):
            raise GatewayError("EXPIRED", "envelope expired", 401)
        live_head = git(self.root, "rev-parse", "HEAD")
        if arguments["requested_head"] != live_head:
            raise GatewayError("STALE_HEAD", "requested_head does not match live HEAD", 409)
        live_branch = git(self.root, "branch", "--show-current") or BRANCH
        if arguments["branch"] not in {live_branch, BRANCH}:
            raise GatewayError("STALE_HEAD", "branch does not match live branch", 409)
        if arguments["repository"] not in {REPO, "greenylifeonline-beep/greeny-life", REPO.lower()}:
            raise GatewayError("IDENTITY_MISMATCH", "repository does not match", 403)
        blob = json.dumps(arguments, ensure_ascii=False)
        if SECRET_RE.search(blob) or BEARER_TOKEN_RE.search(blob):
            raise GatewayError("SECRET_REJECTED", "secrets are forbidden in packets", 400)
        if arguments.get("gl005_proven") or arguments.get("gl004_proven") or arguments.get("pass") is True:
            raise GatewayError("FORBIDDEN_FIELD", "gateway cannot write PASS/proven", 403)
        expected = payload_hash_of(arguments)
        if arguments["payload_hash"] != expected:
            raise GatewayError("PAYLOAD_HASH_MISMATCH", "payload_hash does not match body", 400)

    def _audit(self, actor: Actor, tool: str, status: str, arguments: dict) -> None:
        append_jsonl(
            self.audit_path,
            {
                "ts": utc(),
                "actor_id": actor.actor_id,
                "tool": tool,
                "status": status,
                "packet_id": arguments.get("packet_id"),
                "gl005_proven": False,
            },
        )

    def _receipt(self, payload: dict) -> dict:
        body = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        out = dict(payload)
        out["receipt_sha256"] = sha256_text(body)
        out["gl005_proven"] = False
        out["law"] = LAW
        out["ok"] = True
        return out

    def _store_packet(self, actor: Actor, arguments: dict, intent: str, body: dict) -> dict:
        rec = {
            "schema": "raios.mcp-packet.v1",
            "packet_id": arguments["packet_id"],
            "correlation_id": arguments["correlation_id"],
            "session_id": arguments.get("session_id"),
            "ts": utc(),
            "from": actor.actor_id,
            "to": body.get("to") or [],
            "intent": intent,
            "requested_head": arguments.get("requested_head"),
            "payload_hash": arguments.get("payload_hash"),
            "body": body,
            "gl005_proven": False,
        }
        append_jsonl(self.root / ".ai-os" / "mcp" / "packets.jsonl", rec)
        self._packet_ids.add(arguments["packet_id"])
        return rec

    def tool_get_head(self, actor: Actor, arguments: dict) -> dict:
        return self._receipt(
            {
                "tool": "get_head",
                "head": git(self.root, "rev-parse", "HEAD"),
                "branch": git(self.root, "branch", "--show-current") or BRANCH,
                "repository": REPO,
                "actor_id": actor.actor_id,
                "mcp_to_opencode": mcp_to_opencode_seam(self.root),
            }
        )

    def tool_read_board(self, actor: Actor, arguments: dict) -> dict:
        now = self.root / ".ai-os" / "board" / "NOW.md"
        opinions = load_jsonl(self.root / ".ai-os" / "board" / "opinions.jsonl")
        return self._receipt(
            {
                "tool": "read_board",
                "text": now.read_text(encoding="utf-8") if now.exists() else "",
                "opinions": opinions[-20:],
            }
        )

    def tool_read_inbox(self, actor: Actor, arguments: dict) -> dict:
        packets = [
            row
            for row in load_jsonl(self.root / ".ai-os" / "mcp" / "packets.jsonl")
            if actor.actor_id in (row.get("to") or []) or row.get("from") == actor.actor_id
        ]
        return self._receipt(
            {
                "tool": "read_inbox",
                "packets": packets[-50:],
                "github_inbox": load_jsonl(self.root / ".ai-os" / "mail" / "INBOX.jsonl")[-50:],
                "c1_outbox": load_jsonl(self.root / ".ai-os" / "mail" / "OUTBOX.jsonl")[-50:],
            }
        )

    def tool_read_receipt(self, actor: Actor, arguments: dict) -> dict:
        name = str(arguments.get("name") or arguments.get("receipt") or "").strip()
        if not name:
            raise GatewayError("MISSING_IDENTITY", "receipt name required", 400)
        receipts = (self.root / ".ai-os" / "receipts").resolve()
        path = (receipts / name).resolve()
        if receipts not in path.parents and path != receipts:
            raise GatewayError("PATH_TRAVERSAL", "receipt path escapes receipts/", 403)
        if not path.is_file():
            raise GatewayError("NOT_FOUND", f"receipt not found: {name}", 404)
        return self._receipt({"tool": "read_receipt", "name": name, "text": path.read_text(encoding="utf-8")[:20000]})

    def tool_get_diff(self, actor: Actor, arguments: dict) -> dict:
        rel = str(arguments.get("path") or ".ai-os/board").strip().lstrip("/")
        if rel.startswith("..") or "tokens.local" in rel or rel.endswith(".env"):
            raise GatewayError("PATH_TRAVERSAL", "diff path refused", 403)
        root = self.root.resolve()
        path = (self.root / rel).resolve()
        if root != path and root not in path.parents:
            raise GatewayError("PATH_TRAVERSAL", "diff path escapes repository", 403)
        text = git(self.root, "diff", "--", rel)
        return self._receipt({"tool": "get_diff", "path": rel, "diff": text[:20000], "raw_shell": False})

    def tool_post_opinion(self, actor: Actor, arguments: dict) -> dict:
        text = str(arguments.get("text") or arguments.get("message") or "").strip()
        if not text:
            raise GatewayError("EMPTY_TEXT", "opinion text required", 400)
        if PROVEN_TRUE_RE.search(text):
            raise GatewayError("FORBIDDEN_FIELD", "opinion cannot grant proven", 403)
        rec = {
            "schema": "raios.board-opinion.v1",
            "id": str(uuid.uuid4()),
            "ts": utc(),
            "code": actor.actor_id,
            "from": actor.actor_role,
            "text": text,
            "knowledge_state": "DISCOVERED",
            "packet_id": arguments["packet_id"],
            "correlation_id": arguments["correlation_id"],
            "wal_status": "GATEWAY_DID_NOT_WRITE_WAL",
            "gl005_proven": False,
        }
        board = self.root / ".ai-os" / "board"
        append_jsonl(board / "opinions.jsonl", rec)
        now_path = board / "NOW.json"
        state = load_json(now_path, {})
        state["updated_at"] = rec["ts"]
        now_path.parent.mkdir(parents=True, exist_ok=True)
        now_path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        md = board / "NOW.md"
        prev = md.read_text(encoding="utf-8") if md.exists() else ""
        md.write_text(prev + f"\n### {rec['ts']} — {rec['code']} {rec['from']}\n\n{text}\n\n", encoding="utf-8")
        self._store_packet(actor, arguments, "post_opinion", rec)
        wal = self.root / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
        return self._receipt(
            {
                "tool": "post_opinion",
                "opinion_id": rec["id"],
                "wal_status": rec["wal_status"],
                "wal_written": False,
                "cognitive_wal_exists_after": wal.exists(),
            }
        )

    def tool_send_packet(self, actor: Actor, arguments: dict) -> dict:
        to = arguments.get("to") or []
        if isinstance(to, str):
            to = [x.strip() for x in to.split(",") if x.strip()]
        text = str(arguments.get("text") or arguments.get("message") or "").strip()
        if not text or not to:
            raise GatewayError("EMPTY_TEXT", "to and text required", 400)
        rec = self._store_packet(actor, arguments, "send_packet", {"to": to, "text": text})
        if actor.actor_id == "C1":
            append_jsonl(
                self.root / ".ai-os" / "mail" / "OUTBOX.jsonl",
                {
                    "schema": "raios.mail-envelope.v1",
                    "id": rec["packet_id"],
                    "ts": rec["ts"],
                    "from": "C1",
                    "to": to,
                    "text": text,
                    "gl005_proven": False,
                    "law": "MAIL_PASSES_NE_PROVES",
                },
            )
        return self._receipt({"tool": "send_packet", "packet_id": rec["packet_id"], "to": to})

    def tool_ack_packet(self, actor: Actor, arguments: dict) -> dict:
        target = str(arguments.get("target_packet_id") or arguments.get("causation_id") or "").strip()
        status = str(arguments.get("status") or "READ").upper()
        if not target:
            raise GatewayError("MISSING_IDENTITY", "target_packet_id required", 400)
        if status == "EXECUTED":
            raise GatewayError("FORBIDDEN_FIELD", "EXECUTED is Repair-receipt only", 403)
        rec = self._store_packet(actor, arguments, "ack_packet", {"causation_id": target, "status": status, "moved": False})
        return self._receipt({"tool": "ack_packet", "packet_id": rec["packet_id"], "causation_id": target, "moved": False})


def write_envelope(actor: Actor, head: str, extra: dict | None = None) -> dict:
    packet_id = str(uuid.uuid4())
    created = utc()
    env = {
        "actor_id": actor.actor_id,
        "actor_role": actor.actor_role,
        "instance_role": actor.instance_role,
        "session_id": "sess_" + uuid.uuid4().hex[:8],
        "packet_id": packet_id,
        "correlation_id": "evt_" + uuid.uuid4().hex[:8],
        "repository": REPO,
        "branch": BRANCH,
        "requested_head": head,
        "authority_scope": ",".join(actor.scopes),
        "write_intent": "OPINION_ONLY",
        "execution_intent": "NONE",
        "promotion_intent": "NONE",
        "created_at": created,
        "expires_at": "2099-01-01T00:00:00+00:00",
        "evidence_refs": [],
    }
    if extra:
        env.update(extra)
    env["payload_hash"] = payload_hash_of(env)
    return env
