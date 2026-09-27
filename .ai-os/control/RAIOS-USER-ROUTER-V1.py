"""Existing C1/C5 HTTP user router. Not a second control plane or message bus.

Recovers the missing canonical wrapper around RAIOS-ROUTE-REGISTRY-V1.json
and RAIOS-CONTROL-PLANE-V1.py. C5-PUBLIC is HTTP to 127.0.0.1:8766.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CTRL = Path(__file__).resolve().parent
REGISTRY_PATH = CTRL / "RAIOS-ROUTE-REGISTRY-V1.json"
CONTROL_PLANE_PATH = CTRL / "RAIOS-CONTROL-PLANE-V1.py"
DEFAULT_C5 = "http://127.0.0.1:8766/api/chat"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return default


def load_registry() -> dict[str, Any]:
    doc = _load_json(REGISTRY_PATH, {})
    return doc if isinstance(doc, dict) else {}


def c5_public_url() -> str:
    routes = (load_registry().get("routes") or {})
    target = ((routes.get("C5-PUBLIC") or {}).get("target") or DEFAULT_C5)
    return str(target)


def _control_plane():
    spec = importlib.util.spec_from_file_location("raios_control_plane_v1", CONTROL_PLANE_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError("CONTROL_PLANE_UNAVAILABLE")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def cp(*args: Any) -> Any:
    plane = _control_plane()
    if not args:
        raise ValueError("CP_COMMAND_REQUIRED")
    cmd = str(args[0])
    if cmd == "ack":
        actor = str(args[2]) if len(args) > 2 else "C2@AG"
        return plane.ack(str(args[1]), actor)
    if cmd == "send":
        payload = args[4] if len(args) > 4 else {}
        if not isinstance(payload, dict):
            payload = {"text": str(payload)}
        external = bool(args[5]) if len(args) > 5 else False
        return plane.send(str(args[1]), str(args[2]), str(args[3]), payload, external)
    if cmd == "health":
        return plane.health()
    raise ValueError(f"UNKNOWN_CP::{cmd}")


def local_worker_present(worker_id: str) -> bool:
    try:
        rows = _control_plane().health()
    except Exception:
        return False
    wanted = str(worker_id or "")
    for row in rows or []:
        if str(row.get("worker_id") or "") == wanted and str(row.get("state") or "").upper() == "LIVE":
            return True
    return False


def _language(text: str) -> str:
    return "ar" if any("\u0600" <= ch <= "\u06FF" for ch in (text or "")) else "en"


def _c5_text(payload: Any) -> str:
    if isinstance(payload, str):
        return payload
    if not isinstance(payload, dict):
        return str(payload or "")
    for key in ("response", "content", "reply", "text", "answer"):
        val = payload.get(key)
        if isinstance(val, str) and val.strip():
            return val
    err = payload.get("error") or payload.get("detail")
    if err:
        return f"ERROR::{err}"
    return json.dumps(payload, ensure_ascii=False)


def _http_c5(text: str, *, correlation: str, sender: str, target: str) -> dict[str, Any]:
    url = c5_public_url()
    body = json.dumps(
        {
            "text": text,
            "language": _language(text),
            "training_mode": False,
            "task_id": correlation or "RAIOS-C1-C5-CHANNEL",
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            raw = response.read()
            status_code = int(response.status)
            payload = json.loads(raw.decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        try:
            payload = json.loads(exc.read().decode("utf-8", errors="replace"))
        except Exception:
            payload = {"error": str(exc)}
        status_code = int(exc.code)
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    except Exception as exc:
        payload = {"error": f"{type(exc).__name__}:{exc}"}
        status_code = 0
        raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    visible = _c5_text(payload)
    ok = status_code == 200 and bool(visible) and not str(payload.get("error") or "").strip()
    message_id = f"MSG-C1C5-{digest[:12]}"
    return {
        "status": "PROVEN_E2E" if ok else "FAILED",
        "message_id": message_id,
        "correlation_id": correlation,
        "sender": sender,
        "target": target,
        "http_status": status_code,
        "route": "C5-PUBLIC",
        "transport": "HTTP",
        "wal_written": False,
        "response": payload if isinstance(payload, dict) else {"text": visible},
        "receipt": {"sha256": digest, "at": utc(), "url": url},
    }


def route_one(sender: str, target: str, text: str, correlation: str | None = None) -> dict[str, Any]:
    corr = str(correlation or f"COR-USER-ROUTER-{utc().replace(':', '')}")
    lane = str(target or "")
    if lane in {"C5-PUBLIC", "C5", "C5@AG"}:
        return _http_c5(text, correlation=corr, sender=sender, target=lane)
    if lane in {"C5-FOUNDER"}:
        return {
            "status": "FAIL_CLOSED",
            "message_id": None,
            "correlation_id": corr,
            "sender": sender,
            "target": lane,
            "wal_written": False,
            "response": {"error": "C5_FOUNDER_FAIL_CLOSED"},
            "receipt": {},
        }
    plane = _control_plane()
    msg = plane.send(
        sender,
        target,
        "ROUTE",
        {"text": text, "correlation_id": corr},
        False,
    )
    mid = msg.get("message_id")
    receipt_path = plane.RECEIPTS / f"{mid}.send.json"
    digest = ""
    if receipt_path.is_file():
        digest = hashlib.sha256(receipt_path.read_bytes()).hexdigest()
    return {
        "status": "QUEUED_INTERNAL_BUS",
        "message_id": mid,
        "correlation_id": msg.get("correlation_id") or corr,
        "sender": sender,
        "target": target,
        "wal_written": False,
        "response": {"text": "", "queued": True},
        "receipt": {"sha256": digest, "at": utc()},
    }
