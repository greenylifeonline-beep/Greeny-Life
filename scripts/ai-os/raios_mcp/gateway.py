# RAIOS_UNIVERSAL_CONNECTOR_FABRIC_V3
# RAIOS_EXTERNAL_PRINCIPAL_PROFILE_V1
"""RAIOS MCP gateway: nine public tools, one execution plane, no shell."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = "greenylifeonline-beep/Greeny-Life"
BRANCH = "ai-evolution-202608051809"
LAW = "MCP_GATEWAY_NE_TRUTH_AUTHORITY"
GIT_TIMEOUT_SECONDS = 5.0
V1_TOOLS = (
    "get_head",
    "read_board",
    "read_inbox",
    "read_receipt",
    "get_diff",
    "post_opinion",
    "send_packet",
    "ack_packet",
    "execute_scoped_task",
)
REGISTERED_TOOLS = V1_TOOLS
WRITE_TOOLS = {"post_opinion", "send_packet", "ack_packet", "execute_scoped_task"}
PASSIVE_EXECUTION = {"NONE", "NO", "FALSE"}
DELEGATED_EXECUTION = {"DELEGATED", "STATUS", "CANCEL"}
GRANT_MAX_SECONDS = 900
LOOPBACK_READ_TOOLS = (
    "get_head",
    "read_board",
    "read_inbox",
    "read_receipt",
    "get_diff",
)
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
    return json.loads(path.read_text(encoding="utf-8-sig"))



# RAIOS_EXTERNAL_CONNECTOR_REBIND_V1
EXTERNAL_REBIND_REL = Path(".ai-os") / "mcp" / "EXTERNAL-CONNECTORS.json"

def write_json_atomic(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp." + uuid.uuid4().hex)
    temp.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    temp.replace(path)


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(raw) for raw in path.read_text(encoding="utf-8-sig").splitlines() if raw.strip()]


def append_jsonl(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(rec, ensure_ascii=False) + "\n")


def git(root: Path, *args: str) -> str:
    """Bound every gateway Git operation. A timeout is not an empty success."""
    env = os.environ.copy()
    env.pop("GIT_DIR", None)
    env.pop("GIT_WORK_TREE", None)
    try:
        r = subprocess.run(
            ["git", *args],
            cwd=root,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=GIT_TIMEOUT_SECONDS,
            check=False,
            env=env,
        )
    except subprocess.TimeoutExpired as err:
        raise GatewayError("GIT_TIMEOUT", "Git exceeded its execution deadline", 504) from err
    except OSError as err:
        raise GatewayError("GIT_UNAVAILABLE", "Git could not be started", 503) from err
    if r.returncode != 0:
        raise GatewayError("GIT_FAILED", "Git could not read repository state", 503)
    return (r.stdout or "").strip()


def read_canonical_head(root: Path | None = None) -> tuple[str, str]:
    """Repository head from the Git files. Launch PATH and env are not the head."""
    base = root or Path.cwd()
    git_dir = base / ".git"
    def verified(value: str) -> tuple[str, str]:
        value = value.strip()
        if re.fullmatch(r"[0-9a-fA-F]{40}", value):
            return value.lower(), "git-file"
        return "unknown", "unknown"
    try:
        raw = (git_dir / "HEAD").read_text(encoding="utf-8").strip()
        if not raw.startswith("ref:"):
            return verified(raw)
        ref = raw.split(":", 1)[1].strip()
        if not ref.startswith("refs/") or any(part in {"", ".", ".."} for part in ref.split("/")):
            return "unknown", "unknown"
        if not re.fullmatch(r"refs/[A-Za-z0-9_./-]+", ref):
            return "unknown", "unknown"
        ref_path = git_dir.joinpath(*ref.split("/"))
        try:
            return verified(ref_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            for line in (git_dir / "packed-refs").read_text(encoding="utf-8").splitlines():
                if line.startswith(("#", "^")) or " " not in line:
                    continue
                sha, name = line.split(" ", 1)
                if name.strip() == ref:
                    return verified(sha)
    except (OSError, UnicodeError):
        pass
    return "unknown", "unknown"


def stable_runtime_profile() -> Path | None:
    """Profile that owns the live C5 generation file. Presence is a file check, not a constant."""
    candidates: list[Path] = []
    for key in ("RAIOS_STABLE_USER_PROFILE", "USERPROFILE", "HOME"):
        raw = os.environ.get(key)
        if raw:
            candidates.append(Path(raw))
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate).lower()
        if key in seen:
            continue
        seen.add(key)
        marker = candidate / ".raios" / "runtime" / "continuity" / "c5-service" / "current-generation.json"
        if marker.is_file():
            return candidate
    return None


def resolve_opencode_binary() -> str | None:
    """Find the installed OpenCode shim. A missing file stays absent."""
    found = shutil.which("opencode")
    if found:
        path = Path(found)
        cmd = path.with_name("opencode.CMD")
        if cmd.is_file():
            return str(cmd)
        if path.is_file():
            return str(path)
    profile = stable_runtime_profile()
    if profile is None:
        return None
    npm = profile / "AppData" / "Roaming" / "npm"
    for name in ("opencode.CMD", "opencode.cmd", "opencode.exe"):
        candidate = npm / name
        if candidate.is_file():
            return str(candidate)
    return None


_OPENCODE_VERSION_CACHE: dict[str, str | None] = {}


def observed_opencode_version(binary: str) -> str | None:
    if binary in _OPENCODE_VERSION_CACHE:
        return _OPENCODE_VERSION_CACHE[binary]
    target = Path(binary)
    sibling = target.with_name("node_modules").joinpath("opencode-ai", "bin", "opencode.exe")
    if not sibling.is_file():
        sibling = target.parent.joinpath("node_modules", "opencode-ai", "bin", "opencode.exe")
    if sibling.is_file():
        target = sibling
    env = os.environ.copy()
    profile = stable_runtime_profile()
    if profile is not None:
        env["USERPROFILE"] = str(profile)
        env["HOME"] = str(profile)
        env["APPDATA"] = str(profile / "AppData" / "Roaming")
        env["LOCALAPPDATA"] = str(profile / "AppData" / "Local")
    try:
        completed = subprocess.run(
            [str(target), "--version"],
            cwd=str(target.parent),
            text=True,
            capture_output=True,
            timeout=12,
            check=False,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired):
        _OPENCODE_VERSION_CACHE[binary] = None
        return None
    text = ((completed.stdout or "") + "\n" + (completed.stderr or "")).strip()
    match = re.search(r"\d+\.\d+\.\d+", text)
    version = match.group(0) if match else None
    _OPENCODE_VERSION_CACHE[binary] = version
    return version


def mcp_to_opencode_seam(root: Path | None = None) -> dict[str, Any]:
    """Minimum existing MCP→OpenCode bind. Surfaces CODE_MODEL on get_head. No new tools. No shell."""
    binary = resolve_opencode_binary()
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
        "observed_version": observed_opencode_version(binary) if binary else None,
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
        seat_map = load_json(root / ".ai-os" / "mcp" / "SEAT-MAP.json", {})
        if seat_map.get("knowledge_state") == "CANONICAL" and isinstance(seat_map.get("seats"), dict):
            policy = dict(policy)
            policy["actors"] = {
                actor_id: {
                    "actor_role": spec["actor_role"],
                    "instance_role": spec["instance_role"],
                    "tools": list(spec.get("tools") or []),
                    "deny": list(spec.get("deny") or []),
                    "notes": spec.get("notes") or spec.get("name_en"),
                }
                for actor_id, spec in seat_map["seats"].items()
            }
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
            scopes = [s for s in requested_scopes if s in policy_tools and s in REGISTERED_TOOLS]
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


    def _external_rebind_state(self) -> dict:
        path = self.root / EXTERNAL_REBIND_REL
        default = {
            "schema": "raios.external-connectors.v1",
            "version": 1,
            "bindings": [],
            "pending": [],
        }
        try:
            state = load_json(path, default)
        except (OSError, json.JSONDecodeError, UnicodeError) as err:
            raise GatewayError(
                "CONNECTOR_STATE_INVALID",
                "external connector state is unreadable; preserve runtime state and reconcile it",
                503,
            ) from err
        if not isinstance(state, dict):
            raise GatewayError(
                "CONNECTOR_STATE_INVALID",
                "external connector state must be an object",
                503,
            )

        bindings = state.get("bindings")
        pending = state.get("pending")

        if bindings is None:
            bindings = []
        if pending is None:
            pending = []

        if not isinstance(bindings, list) or not isinstance(pending, list):
            raise GatewayError(
                "CONNECTOR_STATE_INVALID",
                "external connector bindings and pending state must be arrays",
                503,
            )

        # Historical/corrupt non-object rows must not take down every connector.
        # Ignore only malformed rows in-memory; never rewrite or destroy runtime
        # state during authentication.
        state = dict(state)
        state["bindings"] = [row for row in bindings if isinstance(row, dict)]
        state["pending"] = [row for row in pending if isinstance(row, dict)]
        state.setdefault("schema", "raios.external-connectors.v1")
        state.setdefault("version", 1)
        return state

    def external_connector_health(self) -> dict[str, Any]:
        """Non-secret connector readiness projection for health/self-heal."""
        result = {
            "state_valid": False,
            "contract_valid": False,
            "binding_count": 0,
            "pending_count": 0,
            "active_binding_count": 0,
            "chatgpt_native_binding_active": False,
            "chatgpt_native_delegate_token_present": False,
            "chatgpt_native_delegate_binding_matches": False,
            "token_store_valid": False,
            "error": None,
        }
        try:
            state = self._external_rebind_state()
        except GatewayError as err:
            result["error"] = err.code
            return result

        result["state_valid"] = True
        bindings = list(state.get("bindings") or [])
        pending = list(state.get("pending") or [])
        result["binding_count"] = len(bindings)
        result["pending_count"] = len(pending)

        active_ids = {
            str(row.get("connector_id") or "")
            for row in bindings
            if isinstance(row, dict)
            and str(row.get("status") or "").upper() in {"ACTIVE", "GRACE"}
        }
        result["active_binding_count"] = len(active_ids)
        result["chatgpt_native_binding_active"] = "CHATGPT_NATIVE" in active_ids

        # The native tunnel injects the CHATGPT_NATIVE_DELEGATE token from
        # tokens.local.json. Compare only its SHA-256 digest against the active
        # binding and expose booleans; never expose the token or fingerprint.
        token_path = self.root / ".ai-os" / "mcp" / "tokens.local.json"
        try:
            token_doc = load_json(token_path, {})
            actors = (
                token_doc.get("actors")
                if isinstance(token_doc, dict)
                else None
            )
            if isinstance(actors, list):
                result["token_store_valid"] = True
                delegate_token = ""
                for row in actors:
                    if (
                        isinstance(row, dict)
                        and str(row.get("actor_id") or "") == "CHATGPT_NATIVE_DELEGATE"
                    ):
                        delegate_token = str(row.get("token") or "")
                        break
                result["chatgpt_native_delegate_token_present"] = bool(delegate_token)
                if delegate_token:
                    digest = sha256_text(delegate_token)
                    result["chatgpt_native_delegate_binding_matches"] = any(
                        isinstance(row, dict)
                        and str(row.get("connector_id") or "") == "CHATGPT_NATIVE"
                        and str(row.get("status") or "").upper() in {"ACTIVE", "GRACE"}
                        and str(row.get("fingerprint_sha256") or "") == digest
                        for row in bindings
                    )
        except (OSError, json.JSONDecodeError, UnicodeError):
            result["token_store_valid"] = False

        try:
            contract = load_json(
                self.root / ".ai-os" / "mcp" / "EXTERNAL-CONNECTOR-CONTRACT.json",
                {},
            )
        except (OSError, json.JSONDecodeError, UnicodeError):
            result["error"] = "CONNECTOR_CONTRACT_INVALID"
            return result

        profiles = (
            contract.get("external_principal_profiles")
            if isinstance(contract, dict)
            else None
        )
        if not isinstance(profiles, dict):
            result["error"] = "CONNECTOR_CONTRACT_INVALID"
            return result

        result["contract_valid"] = True
        result["profile_count"] = len(profiles)
        return result

    def _actor_from_external_binding(self, digest: str) -> Actor | None:
        state = self._external_rebind_state()
        now = datetime.now(timezone.utc)

        try:
            contract = load_json(
                self.root / ".ai-os" / "mcp" / "EXTERNAL-CONNECTOR-CONTRACT.json",
                {},
            )
        except (OSError, json.JSONDecodeError, UnicodeError) as err:
            raise GatewayError(
                "CONNECTOR_CONTRACT_INVALID",
                "external connector contract is unreadable",
                503,
            ) from err

        profiles = (
            contract.get("external_principal_profiles")
            if isinstance(contract, dict)
            else {}
        ) or {}
        if not isinstance(profiles, dict):
            raise GatewayError(
                "CONNECTOR_CONTRACT_INVALID",
                "external principal profiles must be an object",
                503,
            )

        for row in list(state.get("bindings") or []):
            if str(row.get("fingerprint_sha256") or "") != digest:
                continue

            status = str(row.get("status") or "").upper()

            if status not in {"ACTIVE", "GRACE"}:
                continue

            expiry = row.get("expires_at")
            grace_until = row.get("grace_until")

            try:
                if expiry and parse_dt(str(expiry)) <= now:
                    continue

                if (
                    status == "GRACE"
                    and grace_until
                    and parse_dt(str(grace_until)) <= now
                ):
                    continue
            except (TypeError, ValueError):
                # One malformed historical binding must not crash every
                # external connector request. Fail this row closed and allow
                # normal rebind lifecycle to recover the presented identity.
                continue

            connector_id = str(row.get("connector_id") or "")
            principal = str(row.get("principal") or "")

            profile = profiles.get(connector_id)

            if not isinstance(profile, dict):
                continue

            if str(profile.get("principal") or "") != principal:
                continue

            # External principals are explicitly not council seats.
            if bool(profile.get("seat")):
                continue

            tools = [
                str(x)
                for x in list(profile.get("tools") or [])
                if str(x) in REGISTERED_TOOLS
            ]

            scopes = [
                str(x)
                for x in list(profile.get("scopes") or [])
                if str(x) in V1_TOOLS
            ]

            deny = [
                str(x)
                for x in list(profile.get("deny") or [])
            ]

            if not tools:
                continue

            return Actor(
                actor_id=principal,
                actor_role=str(
                    profile.get("actor_role")
                    or "EXTERNAL_DELEGATED_CLIENT"
                ),
                instance_role=str(
                    profile.get("instance_role")
                    or connector_id.lower()
                ),
                tools=tools,
                deny=deny,
                token_sha256=digest,
                scopes=scopes,
                expires_at=str(expiry) if expiry else None,
            )

        return None

    def _record_pending_external_rebind(self, digest: str) -> None:
        path = self.root / EXTERNAL_REBIND_REL
        state = self._external_rebind_state()
        pending = list(state.get("pending") or [])

        now = utc()
        matched = None

        for row in pending:
            if (
                str(row.get("fingerprint_sha256") or "") == digest
                and str(row.get("status") or "").upper() == "PENDING"
            ):
                matched = row
                break

        if matched is None:
            matched = {
                "fingerprint_sha256": digest,
                "status": "PENDING",
                "first_seen_at": now,
                "last_seen_at": now,
                "seen_count": 1,
                "secret_material_persisted": False,
            }
            pending.append(matched)
        else:
            matched["last_seen_at"] = now
            matched["seen_count"] = int(matched.get("seen_count") or 0) + 1

        # Bound state size; this is state, not a second WAL.
        pending = pending[-128:]

        state["pending"] = pending
        state["updated_at"] = now
        try:
            write_json_atomic(path, state)
        except OSError as err:
            raise GatewayError(
                "CONNECTOR_REBIND_STATE_UNAVAILABLE",
                "connector rebind state could not be persisted",
                503,
            ) from err

        try:
            append_jsonl(
                self.audit_path,
                {
                    "ts": now,
                    "event": "EXTERNAL_CONNECTOR_PENDING_REBIND",
                    "fingerprint_sha256": digest,
                    "secret_material_persisted": False,
                    "gl005_proven": False,
                },
            )
        except OSError as err:
            raise GatewayError(
                "AUDIT_UNAVAILABLE",
                "connector rebind audit could not be written",
                503,
            ) from err


    def authenticate(self, token: str | None) -> Actor:
        if not token:
            raise GatewayError("UNAUTHENTICATED", "missing token", 401)

        digest = sha256_text(token)

        # Generation 0 / legacy primary credential.
        for actor in self.actors.values():
            if actor.token_sha256 and actor.token_sha256 == digest:
                if actor.actor_id == "C0":
                    raise GatewayError(
                        "C0_SEAT_ABOLISHED",
                        "C0 is not a live seat",
                        403,
                    )
                if (
                    actor.expires_at
                    and parse_dt(actor.expires_at)
                    <= datetime.now(timezone.utc)
                ):
                    raise GatewayError("EXPIRED", "token expired", 401)
                return actor

        # Universal connector generations.
        rebound = self._actor_from_external_binding(digest)
        if rebound is not None:
            return rebound

        # Never persist the presented secret: fingerprint only.
        self._record_pending_external_rebind(digest)

        raise GatewayError(
            "CLIENT_REAUTH_REQUIRED",
            "credential fingerprint captured for C1 connector rebind",
            401,
        )

    def loopback_reader(self) -> Actor:
        return Actor(
            actor_id="LOOPBACK_READ",
            actor_role="LOCAL_CLIENT",
            instance_role="loopback",
            tools=list(LOOPBACK_READ_TOOLS),
            deny=["post_opinion", "send_packet", "ack_packet", "execute_scoped_task"],
            token_sha256="",
            scopes=list(LOOPBACK_READ_TOOLS),
            expires_at=None,
        )

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
        except Exception as err:
            status = err.code if isinstance(err, GatewayError) else "INTERNAL_ERROR"
            self._audit(actor, tool, status, arguments)
            raise
        self._audit(actor, tool, "ok", arguments)
        return result

    # RAIOS_EXECUTION_HOTPATH_NO_GIT_SUBPROCESS_V2
    def _git_branch(self, *, head_source: str) -> str:
        """Resolve canonical branch from .git metadata without spawning Git."""
        if head_source == "git-file":
            try:
                git_dir=self.root / ".git"

                if git_dir.is_file():
                    meta=git_dir.read_text(encoding="utf-8").strip()

                    if meta.lower().startswith("gitdir:"):
                        target=meta.split(":",1)[1].strip()
                        git_dir=(self.root / target).resolve()

                raw=(git_dir / "HEAD").read_text(
                    encoding="utf-8"
                ).strip()

                prefix="ref: refs/heads/"

                if raw.startswith(prefix):
                    name=raw[len(prefix):].strip()

                    if (
                        name
                        and not name.startswith("/")
                        and ".." not in name
                    ):
                        return name

            except (OSError,UnicodeError):
                pass

        return BRANCH


    def close(self) -> None:
        return None

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
        if tool == "execute_scoped_task":
            # RAIOS_SERVER_OWNED_EXECUTION_PAYLOAD_HASH_V2
            arguments["payload_hash"] = payload_hash_of(arguments)
        return getattr(self, f"tool_{tool}")(actor, arguments)


    def _normalize_system_owned_envelope(
        self,
        actor: Actor,
        tool: str,
        arguments: dict,
    ) -> None:
        """
        Universal Connector Fabric V3.

        External clients express business intent only.
        RAIOS owns protocol identity, live runtime truth,
        envelope metadata and integrity fields.
        """
        if tool not in WRITE_TOOLS:
            return

        # Authenticated identity is authoritative.
        # A client cannot impersonate C1/C2/etc by supplying fields.
        arguments["actor_id"] = actor.actor_id
        arguments["actor_role"] = actor.actor_role
        arguments["instance_role"] = actor.instance_role

        # Runtime truth comes from the live canonical tree.
        # RAIOS_WRITE_HOTPATH_NO_GIT_SUBPROCESS_V1
        live_head, _head_source = read_canonical_head(self.root)
        live_branch = self._git_branch(head_source=_head_source)

        arguments["repository"] = REPO
        arguments["branch"] = live_branch
        arguments["requested_head"] = live_head
        arguments["authority_scope"] = ",".join(actor.scopes)

        # IDs are system generated, never trusted from a connector.
        arguments["session_id"] = "sess_" + uuid.uuid4().hex
        arguments["packet_id"] = "pkt_" + uuid.uuid4().hex
        arguments["correlation_id"] = "corr_" + uuid.uuid4().hex[:20]

        # Cognitive connector writes are never executable or promotional.
        if tool == "post_opinion":
            arguments["write_intent"] = "OPINION_ONLY"
        elif tool == "ack_packet":
            arguments["write_intent"] = "ACK_ONLY"
        else:
            arguments["write_intent"] = "MESSAGE_ONLY"

        if tool == "execute_scoped_task":
            requested_intent = str(
                arguments.get("operation")
                or arguments.get("execution_intent")
                or "DELEGATED"
            ).upper()
            if requested_intent not in DELEGATED_EXECUTION:
                raise GatewayError(
                    "ESCALATION_DENIED",
                    "execute_scoped_task operation is not admitted",
                    403,
                )
            arguments["execution_intent"] = requested_intent
        else:
            arguments["execution_intent"] = "NONE"
        arguments["promotion_intent"] = "NONE"

        now = datetime.now(timezone.utc)

        arguments["created_at"] = now.isoformat()
        arguments["expires_at"] = datetime.fromtimestamp(
            now.timestamp() + 900,
            timezone.utc,
        ).isoformat()

        # Integrity is calculated last by RAIOS.
        arguments.pop("payload_hash", None)
        arguments["payload_hash"] = payload_hash_of(arguments)


    def _bind_identity(self, actor: Actor, tool: str, arguments: dict[str, Any]) -> None:
        self._normalize_system_owned_envelope(actor, tool, arguments)
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
        if tool == "execute_scoped_task" and exec_intent in PASSIVE_EXECUTION:
            arguments["execution_intent"] = "DELEGATED"
            exec_intent = "DELEGATED"
        if exec_intent in DELEGATED_EXECUTION:
            if tool not in {"execute_scoped_task", "send_packet"}:
                raise GatewayError(
                    "ESCALATION_DENIED",
                    "governed execution is admitted on execute_scoped_task",
                    403,
                )
        elif exec_intent not in PASSIVE_EXECUTION:
            raise GatewayError("ESCALATION_DENIED", "V1 connector does not execute a shell", 403)
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
        live_head, _head_source = read_canonical_head(self.root)
        if arguments["requested_head"] != live_head:
            raise GatewayError("STALE_HEAD", "requested_head does not match live HEAD", 409)
        live_branch = self._git_branch(head_source=_head_source)
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
        if tool != "execute_scoped_task" and arguments["payload_hash"] != expected:
            raise GatewayError("PAYLOAD_HASH_MISMATCH", "payload_hash does not match body", 400)

    def _audit(self, actor: Actor, tool: str, status: str, arguments: dict) -> None:
        try:
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
        except OSError as err:
            raise GatewayError(
                "AUDIT_UNAVAILABLE",
                "Audit record could not be written. The operation may have completed; "
                "reconcile mutation outcomes before retrying.",
                503,
            ) from err

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
        head, head_source = read_canonical_head(self.root)
        branch = self._git_branch(head_source=head_source)
        return self._receipt(
            {
                "tool": "get_head",
                "head": head,
                "head_source": head_source,
                "branch": branch,
                "repository": REPO,
                "actor_id": actor.actor_id,
                "mcp_to_opencode": mcp_to_opencode_seam(self.root),
            }
        )

    def tool_read_board(self, actor: Actor, arguments: dict) -> dict:
        now_path = self.root / ".ai-os" / "board" / "NOW.md"
        opinions = load_jsonl(self.root / ".ai-os" / "board" / "opinions.jsonl")
        src = Path(__file__).resolve().parents[3] / "src"
        if str(src) not in sys.path:
            sys.path.insert(0, str(src))
        try:
            tasks_doc = json.loads((self.root / ".ai-os" / "state" / "TASKS.json").read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            tasks_doc = {"tasks": []}
        from raios.command_center.board_now import now_tasks, render_md
        now_rows = now_tasks(list(tasks_doc.get("tasks") or []))
        canonical = render_md(tasks_doc, now_rows)
        legacy = now_path.read_text(encoding="utf-8") if now_path.exists() else ""
        text = canonical
        if legacy.strip():
            text = canonical + "\n\n## legacy NOW.md (not authority)\n\n" + legacy
        return self._receipt(
            {
                "tool": "read_board",
                "text": text,
                "legacy_now_md": legacy[:8000],
                "legacy_now_md_authoritative": False,
                "tasks_now": now_rows,
                "active_program_id": tasks_doc.get("active_program_id"),
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

    def _execution_scope(self, actor: Actor, capability: str) -> str:
        return f"native:{actor.actor_id}:{capability}"

    def _fabric(self):
        src = str((self.root / "src").resolve())
        if src not in sys.path:
            sys.path.insert(0, src)
        from raios.c1c5 import capabilities, receipts
        from raios.command_fabric.lease import CommandLeaseAdapter

        return capabilities, receipts, CommandLeaseAdapter

    def _nonce_seen(self, digest: str) -> bool:
        path = self.root / ".ai-os" / "mcp" / "execution-nonces.jsonl"
        return any(row.get("nonce_sha256") == digest for row in load_jsonl(path))

    def _remember_nonce(self, digest: str, actor: Actor, task_id: str) -> None:
        append_jsonl(
            self.root / ".ai-os" / "mcp" / "execution-nonces.jsonl",
            {"ts": utc(), "actor_id": actor.actor_id, "task_id": task_id, "nonce_sha256": digest},
        )

    def _grant_deadline(self, arguments: dict) -> datetime:
        grant_exp = str(arguments.get("grant_expires_at") or "").strip()
        if not grant_exp:
            raise GatewayError("MISSING_IDENTITY", "grant_expires_at is required", 400)
        expires = parse_dt(grant_exp)
        now = datetime.now(timezone.utc)
        if expires <= now or (expires - now).total_seconds() > GRANT_MAX_SECONDS:
            raise GatewayError("EXPIRED", "delegated grant must expire within 15 minutes", 401)
        return expires

    def _consume_nonce(self, actor: Actor, arguments: dict, task_id: str) -> None:
        nonce = str(arguments.get("nonce") or "").strip()
        if len(nonce) < 16:
            raise GatewayError("MISSING_IDENTITY", "nonce is required", 400)
        digest = sha256_text(nonce)
        if self._nonce_seen(digest):
            raise GatewayError("REPLAY", "nonce already used", 409)
        self._remember_nonce(digest, actor, task_id)

    def _select_executor(self, capability: str) -> dict:
        """One RAIOS execution plane. Local and cloud are domains, not a second brain."""
        return {
            "domain": "LOCAL",
            "plane": "c1c5.capabilities",
            "capability": capability,
            "cloud_dispatched": False,
            "second_plane": False,
            "reasons": [
                "capability_allowlist",
                "read_only_contract",
                "local_available",
                "same_raios",
            ],
        }

    def _record_execution_deprecation(self, actor: Actor, arguments: dict) -> None:
        append_jsonl(
            self.root / ".ai-os" / "mcp" / "execution-deprecation.jsonl",
            {
                "schema": "raios.mcp-execution-deprecation.v1",
                "ts": utc(),
                "tool": "send_packet",
                "status": "TEMPORARY_COMPATIBILITY",
                "replacement": "execute_scoped_task",
                "actor_id": actor.actor_id,
                "task_id": arguments.get("task_id"),
                "capability": arguments.get("capability"),
            },
        )

    def _delegated_execution(self, actor: Actor, arguments: dict, intent: str, *, require_fence: bool = False) -> dict:
        capabilities, receipts, lease_cls = self._fabric()
        capability = str(arguments.get("capability") or "").strip()
        task_id = str(arguments.get("task_id") or "").strip()
        idem = str(arguments.get("idempotency_key") or "").strip()
        if any(token in capability.casefold() for token in ("shell", "bash", "cmd", "powershell")):
            raise GatewayError("CAPABILITY_DENIED", "shell capabilities are not admitted", 403)
        if intent == "DELEGATED" and capability not in capabilities.CONTRACTS:
            raise GatewayError("CAPABILITY_DENIED", "capability is not on the existing allowlist", 403)
        if intent != "CANCEL" and (not task_id or not idem):
            raise GatewayError("MISSING_IDENTITY", "task_id and idempotency_key are required", 400)
        receipt_dir = self.root / ".ai-os" / "receipts" / "command-fabric" / "native-execution"
        if intent == "STATUS":
            found = receipts.load(idem, directory=receipt_dir)
            if not found:
                raise GatewayError("NOT_FOUND", "execution receipt not found", 404)
            if found.get("ACTOR_BOUND") != actor.actor_id:
                raise GatewayError("CAPABILITY_DENIED", "receipt belongs to another actor", 403)
            return {"operation": "STATUS", "receipt": found, "invoked": False, "shell": False}
        if idem:
            prior = receipts.load(idem, directory=receipt_dir)
            if prior:
                if prior.get("ACTOR_BOUND") != actor.actor_id:
                    raise GatewayError("CAPABILITY_DENIED", "idempotency key belongs to another actor", 403)
                return {"operation": intent, "receipt": prior, "invoked": False, "idempotent_replay": True, "shell": False}
        scope = self._execution_scope(actor, capability or "cancel")
        presented_scope = str(arguments.get("scope") or "").strip()
        if presented_scope and presented_scope != scope:
            raise GatewayError("IDENTITY_MISMATCH", "scope does not match actor and capability", 403)
        leases = lease_cls(self.root / ".ai-os" / "state" / "command-fabric" / "leases")
        lease_id = str(arguments.get("lease_id") or "").strip()
        if intent == "CANCEL":
            if not lease_id:
                raise GatewayError("MISSING_IDENTITY", "lease_id is required to cancel", 400)
            current = leases.validate(lease_id, owner="RAIOS_SYSTEM")
            if not current.get("ok"):
                raise GatewayError("ESCALATION_DENIED", str(current.get("code") or "LEASE_REJECTED"), 403)
            holder = str((current.get("lease") or {}).get("lease_holder") or "")
            if holder != actor.actor_id:
                raise GatewayError("CAPABILITY_DENIED", "lease holder does not match token", 403)
            released = leases.release(lease_id, owner="RAIOS_SYSTEM")
            if not released.get("ok"):
                raise GatewayError("ESCALATION_DENIED", str(released.get("code") or "LEASE_RELEASE_DENIED"), 403)
            return {"operation": "CANCEL", "lease_id": lease_id, "released": True, "invoked": False, "shell": False}
        expires = self._grant_deadline(arguments)
        fence_raw = str(arguments.get("fence_token") or "").strip()
        if require_fence and (not lease_id or not fence_raw):
            raise GatewayError("MISSING_IDENTITY", "lease_id and fence_token are required", 400)
        acquired = False
        if lease_id or fence_raw:
            if not lease_id or not fence_raw:
                raise GatewayError("MISSING_IDENTITY", "lease_id and fence_token are both required", 400)
            try:
                fence_token = int(fence_raw)
            except ValueError as exc:
                raise GatewayError("ESCALATION_DENIED", "fence_token is not an integer", 403) from exc
            fence = leases.validate_fence(lease_id, scope=scope, fence_token=fence_token)
            if not fence.get("ok"):
                raise GatewayError("ESCALATION_DENIED", str(fence.get("code") or "FENCE_REJECTED"), 403)
            holder = str((fence.get("lease") or {}).get("lease_holder") or "")
            if holder != actor.actor_id:
                raise GatewayError("CAPABILITY_DENIED", "lease holder does not match token", 403)
            self._consume_nonce(actor, arguments, task_id)
        else:
            self._consume_nonce(actor, arguments, task_id)
            now = datetime.now(timezone.utc)
            lease = leases.acquire(
                owner="RAIOS_SYSTEM",
                lease_holder=actor.actor_id,
                scope=scope,
                task_id=task_id,
                correlation_id=str(arguments.get("correlation_id") or ""),
                capability=capability,
                resource_or_target="native",
                idempotency_key=idem,
                provenance_ref=f"NATIVE_DELEGATED::{actor.actor_id}",
                ttl_seconds=max(1, min(120, int((expires - now).total_seconds()))),
                head=str(arguments.get("requested_head") or ""),
            )
            if not lease.get("ok"):
                raise GatewayError("ESCALATION_DENIED", str(lease.get("code") or "LEASE_REJECTED"), 403)
            if str(lease.get("lease_holder") or "") != actor.actor_id:
                raise GatewayError("CAPABILITY_DENIED", "lease holder does not match token", 403)
            acquired = not bool(lease.get("IDEMPOTENT_REACQUIRE"))
            lease_id = str(lease.get("lease_id") or "")
        executor = self._select_executor(capability)
        try:
            invoked = capabilities.invoke(capability, arguments.get("payload") or arguments.get("task_payload") or arguments)
        finally:
            if acquired and lease_id:
                leases.release(lease_id, owner="RAIOS_SYSTEM")
        auth = {"PRINCIPAL": actor.actor_id, "AUTHORITY_SOURCE": "NATIVE_DELEGATED_GRANT"}
        receipt = receipts.build(
            env={
                "task_id": task_id,
                "correlation_id": arguments.get("correlation_id"),
                "idempotency_key": idem,
                "target": "native",
                "requested_capability": capability,
                "message_id": arguments.get("packet_id"),
            },
            auth=auth,
            policy={"POLICY_RESULT": "ALLOW", "RISK_CLASS": "LOW"},
            ucp={"STATUS": "ADMITTED", "NO_OP": False},
            capability=invoked,
            status="COMPLETED" if invoked and invoked.get("INVOKED") else "RECORDED",
        )
        receipt["CANONICAL_HEAD"] = arguments.get("requested_head")
        receipt["SHELL"] = False
        receipt["ACTOR_IS_STATIC_C1"] = False
        receipts.persist(receipt, directory=receipt_dir)
        return {
            "operation": intent,
            "receipt": receipt,
            "invoked": bool(invoked and invoked.get("INVOKED")),
            "lease_id": lease_id,
            "shell": False,
            "principal": actor.actor_id,
            "executor": executor,
        }

    def tool_execute_scoped_task(self, actor: Actor, arguments: dict) -> dict:
        intent = str(arguments.get("execution_intent") or "DELEGATED").upper()
        if intent not in DELEGATED_EXECUTION:
            raise GatewayError("ESCALATION_DENIED", "execute_scoped_task admits governed execution only", 403)
        execution = self._delegated_execution(
            actor,
            arguments,
            intent,
            require_fence=(intent == "DELEGATED" and actor.actor_role != "EXTERNAL_DELEGATED_CLIENT"),
        )
        return self._receipt(
            {
                "tool": "execute_scoped_task",
                "execution": execution,
                "shell": False,
                "compatibility_path": False,
            }
        )

    def tool_send_packet(self, actor: Actor, arguments: dict) -> dict:
        intent = str(arguments.get("execution_intent") or "NONE").upper()
        if intent in DELEGATED_EXECUTION:
            self._record_execution_deprecation(actor, arguments)
            execution = self._delegated_execution(actor, arguments, intent, require_fence=False)
            return self._receipt(
                {
                    "tool": "send_packet",
                    "execution": execution,
                    "shell": False,
                    "execution_compatibility": "TEMPORARY",
                    "replacement_tool": "execute_scoped_task",
                }
            )
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
