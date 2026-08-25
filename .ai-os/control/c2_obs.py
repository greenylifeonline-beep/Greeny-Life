#!/usr/bin/env python3
"""C2-OBS bind onto existing keepers. Not a second control plane. Not Repair."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "ai-os"))
sys.path.insert(0, str(ROOT / "RAIOS" / "V9"))

from cloud.nomadic.idempotency import IdempotencyStore, key as idem_key  # noqa: E402
from cloud.nomadic.lease_manager import LeaseManager  # noqa: E402
from raios_c5_watchdog import classify as watchdog_classify  # noqa: E402
from raios_mcp.gateway import Gateway, GatewayError, write_envelope  # noqa: E402

MSG_ID = "MSG-1787675796720281-e5058327"
WORKER = "C2-OBS"
JOB = "COMMAND_FABRIC_JOIN_REPAIR"
BCID = "bc-dd60b5cf-95bd-4f24-9237-cc1b2225f013"
D17335A = "d17335a8a1428acdd0b98849550e4c930c1d9e97"

CONTROL = ROOT / ".ai-os" / "control"
STATE = ROOT / ".ai-os" / "state" / "command-fabric"
RECEIPTS = ROOT / ".ai-os" / "receipts" / "command-fabric"
REPORTS = ROOT / ".ai-os" / "reports" / "command-fabric"
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
LEASE_PATH = STATE / "LEASE.json"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def dump(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def port_open(port: int) -> bool:
    sock = socket.socket()
    sock.settimeout(0.4)
    try:
        return sock.connect_ex(("127.0.0.1", port)) == 0
    finally:
        sock.close()


def http_json(url: str) -> tuple[int, dict[str, Any] | None]:
    try:
        with urllib.request.urlopen(url, timeout=2) as resp:
            raw = resp.read().decode("utf-8")
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, None
    except Exception:
        return 0, None


def git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True)
    return (r.stdout or "").strip()


def diagnose() -> dict[str, Any]:
    head = git("rev-parse", "HEAD")
    ancestor = (
        subprocess.run(["git", "merge-base", "--is-ancestor", D17335A, "HEAD"], cwd=ROOT).returncode == 0
    )
    repair_obj = subprocess.run(["git", "cat-file", "-t", "12603d0"], cwd=ROOT, capture_output=True, text=True)
    mcp_code, mcp_body = http_json("http://127.0.0.1:8787/health")
    screen = http_json("http://127.0.0.1:8765/")[0]
    c1 = http_json("http://127.0.0.1:8876/")[0]
    rec = {
        "schema": "raios.command-fabric.diagnosis.v1",
        "ts": utc(),
        "message_id": MSG_ID,
        "identity": {
            "seat": WORKER,
            "executor": "cursor-cloud",
            "hostname": socket.gethostname(),
            "bc_id": BCID,
            "url": f"https://cursor.com/agents/{BCID}",
            "not_chatgpt_c2": True,
            "not_repair_executor": True,
            "not_c5": True,
        },
        "d17335a_context": {
            "commit": D17335A,
            "local_head": head,
            "head_is_d17335a": head.startswith("d17335a"),
            "d17335a_is_ancestor": ancestor,
            "workspace": str(ROOT),
            "branch": git("branch", "--show-current"),
            "repair_windows_root": "C:\\Users\\Ghanam\\Documents\\Codex\\Greeny-Life-Repair",
            "repair_root_reachable": False,
            "repair_commit_12603d0": repair_obj.stdout.strip() if repair_obj.returncode == 0 else "ABSENT",
        },
        "ci_d17335a": {
            "govern": "success",
            "c5_week": "success",
            "ci_pass_ne_assimilation": True,
            "gl005_proven": False,
        },
        "keepers": json.loads((CONTROL / "KEEPERS.json").read_text(encoding="utf-8")),
        "live": {
            "mcp_health_http": mcp_code,
            "mcp": mcp_body,
            "screen_8765": screen,
            "c1_console_8876": c1,
            "cursor_agent": shutil.which("cursor-agent"),
            "multimodal_gateway": str(next(ROOT.rglob("raios_multimodal_gateway.py"), "")) or None,
            "control_dir_was_missing": True,
            "mail_inbox_exists": (ROOT / ".ai-os" / "mail" / "INBOX.jsonl").exists(),
            "wal_mtime": datetime.fromtimestamp(WAL.stat().st_mtime, timezone.utc).isoformat() if WAL.exists() else None,
        },
        "watchdog": watchdog_classify(),
        "fail_closed": True,
        "gl005_proven": False,
        "c2_join_proven": False,
        "command_fabric_e2e_proven": False,
        "c5_health_proven": mcp_code == 200 and screen == 200,
        "remote_c2_ready": bool((mcp_body or {}).get("remote_c2_ready")),
        "new_engine_created": False,
        "new_bus_created": False,
        "wal_written": False,
        "ninth_mcp_tool": False,
    }
    return rec


class Fabric:
    """File lease + idempotency over existing keepers. Not a second bus."""

    def __init__(self, root: Path | None = None) -> None:
        self.root = root or ROOT
        self.state = self.root / ".ai-os" / "state" / "command-fabric"
        self.leases = LeaseManager(ttl_s=3600.0)
        self.idem = IdempotencyStore()
        self._load_lease()

    def _load_lease(self) -> None:
        path = self.state / "LEASE.json"
        if not path.exists():
            return
        rec = json.loads(path.read_text(encoding="utf-8"))
        lease = rec.get("lease") or {}
        if rec.get("ok") and lease.get("job_id"):
            self.leases.claim(lease["job_id"], lease["worker_id"], now=lease.get("claimed_at_epoch") or None)

    def claim(self, worker_id: str = WORKER) -> dict[str, Any]:
        rec = self.leases.claim(JOB, worker_id)
        rec["ts"] = utc()
        rec["worker_id"] = worker_id
        rec["job_id"] = JOB
        rec["fencing"] = "nomadic.LeaseManager"
        rec["gl005_proven"] = False
        if rec.get("ok") and rec.get("lease"):
            rec["lease"]["claimed_at_epoch"] = rec["lease"]["expires_at"] - self.leases.ttl_s
        self.state.mkdir(parents=True, exist_ok=True)
        dump(self.state / "LEASE.json", rec)
        return rec

    def require_holder(self, worker_id: str = WORKER) -> dict[str, Any]:
        holder = self.leases.holder(JOB)
        if holder != worker_id:
            return {"ok": False, "reason": "LEASE_REQUIRED", "holder": holder, "gl005_proven": False}
        return {"ok": True, "holder": holder}

    def remember(self, message_id: str, payload: str) -> dict[str, Any]:
        return self.idem.remember(idem_key(JOB, sha(payload), message_id), {"output_hash": sha(payload)})


def isolated_channel() -> dict[str, Any]:
    """C1 → inbox → C2 ACK → C2 response → outbox → receipt on existing Gateway."""
    tmp = Path(tempfile.mkdtemp(prefix="c2-obs-fabric-"))
    subprocess.check_call(["git", "init", "-b", "v9-neurolingua-semantic-kernel"], cwd=tmp, stdout=subprocess.DEVNULL)
    subprocess.check_call(["git", "config", "user.email", "c2obs@local"], cwd=tmp)
    subprocess.check_call(["git", "config", "user.name", "c2obs"], cwd=tmp)
    shutil.copytree(ROOT / ".ai-os" / "mcp", tmp / ".ai-os" / "mcp", dirs_exist_ok=True)
    for extra in ("packets.jsonl", "AUDIT.jsonl"):
        (tmp / ".ai-os" / "mcp" / extra).write_text("", encoding="utf-8")
    (tmp / ".ai-os" / "board").mkdir(parents=True, exist_ok=True)
    (tmp / ".ai-os" / "board" / "NOW.md").write_text("# board\n", encoding="utf-8")
    (tmp / ".ai-os" / "board" / "NOW.json").write_text("{}\n", encoding="utf-8")
    (tmp / ".ai-os" / "mail").mkdir(parents=True, exist_ok=True)
    (tmp / ".ai-os" / "receipts").mkdir(parents=True, exist_ok=True)
    sample = {"schema": "raios.c2-obs.read.v1", "gl005_proven": False}
    (tmp / ".ai-os" / "receipts" / "C2-OBS-READ.json").write_text(json.dumps(sample) + "\n", encoding="utf-8")
    subprocess.check_call(["git", "add", "."], cwd=tmp, stdout=subprocess.DEVNULL)
    subprocess.check_call(["git", "commit", "-m", "c2-obs-isolated"], cwd=tmp, stdout=subprocess.DEVNULL)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=tmp, text=True).strip()
    future = "2099-01-01T00:00:00+00:00"
    gw = Gateway.from_root(
        tmp,
        grants=[
            {"actor_id": "C1", "token": "tok-c1", "expires_at": future},
            {"actor_id": "C2", "token": "tok-c2", "expires_at": future},
        ],
    )
    c1 = gw.authenticate("tok-c1")
    c2 = gw.authenticate("tok-c2")
    read = gw.call(c2, "get_head", {})
    env = write_envelope(c1, head, {"to": ["C2"], "text": f"COMMAND_FABRIC_JOIN_REPAIR {MSG_ID}"})
    sent = gw.call(c1, "send_packet", env)
    inbox = gw.call(c2, "read_inbox", {})
    seen = any(sent["packet_id"] == p.get("packet_id") for p in inbox.get("packets") or [])
    ack_env = write_envelope(c2, head, {"target_packet_id": sent["packet_id"], "status": "READ"})
    ack = gw.call(c2, "ack_packet", ack_env)
    resp_env = write_envelope(
        c2,
        head,
        {"to": ["C1"], "text": "C2-OBS ACK JOIN_REPAIR fail_closed=true GL005_PROVEN=false"},
    )
    resp = gw.call(c2, "send_packet", resp_env)
    outbox = [json.loads(x) for x in (tmp / ".ai-os" / "mail" / "OUTBOX.jsonl").read_text().splitlines() if x.strip()]
    receipt = gw.call(c2, "read_receipt", {"name": "C2-OBS-READ.json"})
    replay_err = None
    try:
        gw.call(c1, "send_packet", env)
    except GatewayError as err:
        replay_err = err.code
    dup_err = None
    bad = write_envelope(c1, head, {"packet_id": "same", "correlation_id": "same", "to": ["C2"], "text": "x"})
    try:
        gw.call(c1, "send_packet", bad)
    except GatewayError as err:
        dup_err = err.code
    unauth = None
    try:
        gw.authenticate(None)
    except GatewayError as err:
        unauth = err.code
    return {
        "ok": bool(seen and ack.get("ok") and resp.get("ok") and receipt.get("ok")),
        "read_head": read.get("head"),
        "c1_packet_id": sent.get("packet_id"),
        "c2_ack_packet_id": ack.get("packet_id"),
        "c2_response_packet_id": resp.get("packet_id"),
        "inbox_saw_c1": seen,
        "c1_outbox_count": len(outbox),
        "receipt_name": "C2-OBS-READ.json",
        "receipt_sha256": receipt.get("receipt_sha256"),
        "fail_replay": replay_err,
        "fail_packet_eq_correlation": dup_err,
        "fail_unauthenticated": unauth,
        "ack_moved": False,
        "wal_written": False,
        "gl005_proven": False,
        "tmp": str(tmp),
    }


def join() -> dict[str, Any]:
    STATE.mkdir(parents=True, exist_ok=True)
    RECEIPTS.mkdir(parents=True, exist_ok=True)
    REPORTS.mkdir(parents=True, exist_ok=True)
    diag = diagnose()
    dump(REPORTS / "DIAGNOSIS.json", diag)
    fabric = Fabric()
    lease = fabric.claim(WORKER)
    dump(RECEIPTS / "LEASE.json", lease)
    if not lease.get("ok"):
        flags = _flags(diag, lease, None, None, joined=False)
        dump(STATE / "FLAGS.json", flags)
        return flags
    hold = fabric.require_holder(WORKER)
    if not hold.get("ok"):
        raise SystemExit("LEASE_REQUIRED")
    first = fabric.remember(MSG_ID, MSG_ID)
    second = fabric.remember(MSG_ID, MSG_ID)
    hb = {
        "schema": "raios.command-fabric.heartbeat.v1",
        "ts": utc(),
        "worker_id": WORKER,
        "status": "ALIVE",
        "head": git("rev-parse", "HEAD"),
        "d17335a": D17335A,
        "bc_id": BCID,
        "lease_token": (lease.get("lease") or {}).get("token"),
        "fail_closed": True,
        "stale": False,
        "gl005_proven": False,
        "c2_join_proven": False,
    }
    dump(RECEIPTS / "HEARTBEAT.json", hb)
    dump(STATE / "HEARTBEAT.json", hb)
    ack = {
        "schema": "raios.command-fabric.ack.v1",
        "ts": utc(),
        "message_id": MSG_ID,
        "type": "COMMAND_FABRIC_JOIN_REPAIR",
        "from": WORKER,
        "to": "C1",
        "status": "READ",
        "moved": False,
        "idempotent": first,
        "duplicate_retry": second,
        "correlation_id": "corr-" + sha(MSG_ID)[:12],
        "causation_id": MSG_ID,
        "law": "ACK_IS_A_NEW_PACKET_NEVER_A_MOVE",
        "gl005_proven": False,
    }
    dump(RECEIPTS / f"ACK-{MSG_ID}.json", ack)
    channel = isolated_channel()
    dump(RECEIPTS / "CHANNEL.json", channel)
    delivery = {
        "schema": "raios.command-fabric.delivery.v1",
        "ts": utc(),
        "message_id": MSG_ID,
        "path": "C1 → Inbox → C2 ACK → C2 Response → Outbox → Receipt",
        "channel_ok": channel.get("ok"),
        "isolated_not_live_mcp_token": True,
        "live_remote_c2_ready": diag["remote_c2_ready"],
        "receipt_sha256": channel.get("receipt_sha256"),
        "gl005_proven": False,
        "command_fabric_e2e_proven": False,
        "c2_join_proven": False,
    }
    dump(RECEIPTS / "DELIVERY.json", delivery)
    registry = {
        "schema": "raios.command-fabric.registry.v1",
        "ts": utc(),
        "workers": {
            WORKER: {"status": "ALIVE", "host": socket.gethostname(), "kind": "cursor-cloud-observer"},
            "C5": {"status": "LIVE_SCREEN", "ports": [8765, 8876]},
            "MCP": {"status": "LIVE", "port": 8787, "authenticated_remote_c2": False},
            "REPAIR_WORKERS": {"status": "UNREACHABLE", "note": "12603d0 absent; reported STALE on Repair host"},
        },
        "gl005_proven": False,
    }
    dump(STATE / "REGISTRY.json", registry)
    flags = _flags(diag, lease, channel, delivery, joined=False)
    dump(STATE / "FLAGS.json", flags)
    dump(RECEIPTS / "LAST.json", flags)
    dump(REPORTS / "LAST.json", flags)
    return flags


def _flags(diag: dict, lease: dict, channel: dict | None, delivery: dict | None, joined: bool) -> dict[str, Any]:
    c5_health = bool(diag.get("c5_health_proven"))
    return {
        "schema": "raios.command-fabric.flags.v1",
        "ts": utc(),
        "from": WORKER,
        "message_id": MSG_ID,
        "lease_ok": bool(lease.get("ok")),
        "channel_isolated_ok": bool((channel or {}).get("ok")),
        "delivery_ok": bool((delivery or {}).get("channel_ok")),
        "c5_health_live": c5_health,
        "GL005_PROVEN": False,
        "C2_JOIN_PROVEN": False,
        "COMMAND_FABRIC_E2E_PROVEN": False,
        "C5_HEALTH_PROVEN": c5_health,
        "C2_OBS_CONTEXT_PROVEN": bool(diag["d17335a_context"]["d17335a_is_ancestor"]),
        "CI_PASS_NE_ASSIMILATION": True,
        "fail_closed": True,
        "new_engine_created": False,
        "new_bus_created": False,
        "wal_written": False,
        "cursor_agent_found": shutil.which("cursor-agent") is not None,
        "multimodal_gateway_found": bool(diag["live"]["multimodal_gateway"]),
        "repair_reachable": False,
        "why_join_unproven": "Repair Command Fabric at 12603d0 is unreachable. This host bound C2-OBS onto existing MCP/mail keepers only. Live MCP remote_c2_ready=false (no token).",
    }


if __name__ == "__main__":
    rec = join()
    print(json.dumps({k: rec[k] for k in rec if k.isupper() or k in {"lease_ok", "channel_isolated_ok", "c5_health_live", "why_join_unproven"}}, ensure_ascii=False, indent=2))
    raise SystemExit(0 if rec.get("channel_isolated_ok") and rec.get("lease_ok") else 2)
