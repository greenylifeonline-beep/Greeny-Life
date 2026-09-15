"""UCF cert remaining-gates probe. Does not print tokens. Does not start MCP/CC."""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\Ghanam\Documents\Codex\Greeny-Life")
sys.path.insert(0, str(ROOT / "scripts" / "ai-os"))
from raios_mcp.gateway import payload_hash_of  # noqa: E402

REPO = "greenylifeonline-beep/Greeny-Life"
WORKING_BRANCH = "ai-evolution-202608051809"
PROMPT_HEAD = "2efd08184614749dee999be7a2456c6bf1387c2e"


def live_head() -> str:
    try:
        import subprocess
        h = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, timeout=20).strip()
        return h or PROMPT_HEAD
    except Exception:
        return PROMPT_HEAD


def utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def http_get(url: str, timeout: int = 25) -> dict:
    ts = utc()
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
            parsed = None
            try:
                parsed = json.loads(body)
            except Exception:
                parsed = None
            return {"ts": ts, "status": "OK", "http": resp.status, "url": url, "json": parsed, "body_prefix": body[:400]}
    except Exception as e:
        return {"ts": ts, "status": "FAIL", "error": type(e).__name__, "detail": str(e)[:300], "url": url}


def rpc(url: str, method: str, params=None, token: str | None = None, timeout: int = 20) -> dict:
    ts = utc()
    payload = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        payload["params"] = params
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    data = json.dumps(payload).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", "replace")
            parsed = json.loads(body) if body else {}
            return {"ts": ts, "status": "OK", "http": resp.status, "method": method, "json": parsed}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", "replace")[:500]
        return {"ts": ts, "status": "FAIL", "error": "HTTPError", "http": e.code, "method": method, "detail": err_body}
    except Exception as e:
        return {"ts": ts, "status": "FAIL", "error": type(e).__name__, "detail": str(e)[:300], "method": method}


def load_token_row() -> tuple[str | None, str | None, list]:
    path = ROOT / ".ai-os" / "mcp" / "tokens.local.json"
    if not path.exists():
        return None, None, []
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = list(data.get("actors") or [])
    preferred = ("C2", "C2-CURSOR", "C2@AG")
    for want in preferred:
        for row in rows:
            if str(row.get("actor_id") or "").upper() == want and str(row.get("token") or ""):
                return str(row.get("token") or "") or None, str(row.get("actor_id")), list(row.get("scopes") or [])
    for row in rows:
        tok = str(row.get("token") or "")
        if tok:
            return tok, str(row.get("actor_id") or "") or None, list(row.get("scopes") or [])
    return None, None, []


def seat_identity(actor_id: str) -> dict:
    seat_map = json.loads((ROOT / ".ai-os" / "mcp" / "SEAT-MAP.json").read_text(encoding="utf-8-sig"))
    spec = ((seat_map.get("seats") or {}).get(actor_id) or {})
    return {
        "knowledge_state": seat_map.get("knowledge_state"),
        "actor_role": spec.get("actor_role") or "",
        "instance_role": spec.get("instance_role") or "",
        "tools": list(spec.get("tools") or []),
    }


def write_identity_args(*, actor_id: str, actor_role: str, instance_role: str, authority_scope: str, extra: dict) -> dict:
    created = utc_iso()
    expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    args = {
        "actor_id": actor_id,
        "actor_role": actor_role,
        "instance_role": instance_role,
        "session_id": "sess_" + uuid.uuid4().hex[:8],
        "packet_id": str(uuid.uuid4()),
        "correlation_id": "evt_" + uuid.uuid4().hex[:8],
        "repository": REPO,
        "branch": WORKING_BRANCH,
        "requested_head": git("rev-parse", "HEAD"),
        "authority_scope": authority_scope,
        "write_intent": "OPINION_ONLY",
        "execution_intent": "NONE",
        "promotion_intent": "NONE",
        "created_at": created,
        "expires_at": expires,
    }
    args.update(extra)
    args["payload_hash"] = payload_hash_of(args)
    return args


def inner_from_rpc(send: dict) -> dict:
    content = (((send.get("json") or {}).get("result") or {}).get("content") or [{}])[0].get("text") or ""
    if content:
        try:
            return json.loads(content)
        except Exception:
            pass
    err = ((send.get("json") or {}).get("error") or {})
    if err:
        return {"ok": False, "error": err.get("message") or err, "rpc_error": err}
    return {}


def main() -> int:
    token, token_actor, grant_scopes = load_token_row()
    mcp = "http://127.0.0.1:8788/mcp"
    observed_head = live_head()
    live_branch = git("branch", "--show-current") or WORKING_BRANCH
    seat = seat_identity(token_actor or "C2")
    actor_id = token_actor or "C2"
    actor_role = str(seat.get("actor_role") or "")
    instance_role = str(seat.get("instance_role") or "")
    if grant_scopes:
        authority_scope = ",".join(str(s) for s in grant_scopes if s)
    else:
        authority_scope = ",".join(str(s) for s in (seat.get("tools") or []) if s)
    text = "UCF-CERTIFICATION e2e notice-only authenticated-actor->C6. WORK_AUTHORITY=false. EXECUTION=NONE."
    report = {
        "schema": "raios.ucf.cert-e2e-probe.v1",
        "generated_at_utc": utc(),
        "token_present": bool(token),
        "token_actor_id": token_actor,
        "c2_token_present": token_actor in {"C2", "C2-CURSOR", "C2@AG"} if token_actor else False,
        "identity_source": "SEAT-MAP" if seat.get("knowledge_state") == "CANONICAL" else "POLICY",
        "live_head": observed_head,
        "live_branch": live_branch,
        "working_branch_sent": WORKING_BRANCH,
        "repository_sent": REPO,
        "health": {
            "c5": http_get("http://127.0.0.1:8766/health", 12),
            "mcp": http_get("http://127.0.0.1:8788/health", 10),
            "cc": http_get("http://127.0.0.1:8770/health", 12),
        },
        "rpc": {
            "initialize": rpc(mcp, "initialize", {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "c2-ucf-cert-e2e", "version": "1.1"},
            }),
            "tools_list": rpc(mcp, "tools/list", {}),
        },
    }
    send_args = write_identity_args(
        actor_id=actor_id,
        actor_role=actor_role,
        instance_role=instance_role,
        authority_scope=authority_scope,
        extra={"to": ["C6"], "text": text},
    )
    send = rpc(mcp, "tools/call", {"name": "send_packet", "arguments": send_args}, token=token)
    packet_id = None
    try:
        inner = inner_from_rpc(send)
        packet_id = inner.get("packet_id")
        report["send_packet"] = {
            "status": send.get("status"),
            "http": send.get("http"),
            "ok": inner.get("ok"),
            "error": inner.get("error"),
            "message": inner.get("message"),
            "packet_id": packet_id,
            "to": inner.get("to"),
            "authenticated_actor_id": actor_id,
            "actor_role": actor_role,
            "instance_role": instance_role,
            "branch": send_args.get("branch"),
            "requested_head": send_args.get("requested_head"),
        }
    except Exception:
        report["send_packet"] = {"status": send.get("status"), "http": send.get("http"), "error": send.get("error"), "detail": send.get("detail")}
    if packet_id and token:
        ack_args = write_identity_args(
            actor_id=actor_id,
            actor_role=actor_role,
            instance_role=instance_role,
            authority_scope=authority_scope,
            extra={"target_packet_id": packet_id, "status": "READ"},
        )
        ack = rpc(mcp, "tools/call", {"name": "ack_packet", "arguments": ack_args}, token=token)
        try:
            ack_inner = inner_from_rpc(ack)
            report["ack_packet"] = {
                "status": ack.get("status"),
                "http": ack.get("http"),
                "ok": ack_inner.get("ok"),
                "error": ack_inner.get("error"),
                "message": ack_inner.get("message"),
                "ack_status_sent": "READ",
                "causation_id": ack_inner.get("causation_id"),
                "packet_id": ack_inner.get("packet_id"),
            }
        except Exception:
            report["ack_packet"] = {"status": ack.get("status"), "http": ack.get("http"), "error": ack.get("error"), "detail": ack.get("detail")}
    else:
        report["ack_packet"] = {"status": "SKIP", "reason": "no packet_id or no token"}
    out = ROOT / ".ai-os" / "receipts" / "c2-executive" / "UCF-CERT-E2E.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "written": str(out),
        "c5": report["health"]["c5"].get("status"),
        "mcp": report["health"]["mcp"].get("status"),
        "cc": report["health"]["cc"].get("status"),
        "token_present": bool(token),
        "token_actor_id": token_actor,
        "c2_token_present": report["c2_token_present"],
        "send": report["send_packet"].get("status"),
        "send_ok": report["send_packet"].get("ok"),
        "send_error": report["send_packet"].get("error"),
        "packet_id_present": bool(packet_id),
        "ack": report["ack_packet"].get("status"),
        "ack_ok": report["ack_packet"].get("ok"),
        "live_head": observed_head,
        "live_branch": live_branch,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
