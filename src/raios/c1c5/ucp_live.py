"""Harmless live UCP send/ack against the existing control plane. No acquire. No WAL."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
CONTROL_PLANE = ROOT / ".ai-os" / "control" / "RAIOS-CONTROL-PLANE-V1.py"
EXISTING_CONTROL_PLANE = ".ai-os/control/RAIOS-CONTROL-PLANE-V1.py"


def load_control_plane():
    spec = importlib.util.spec_from_file_location("raios_control_plane_v1", CONTROL_PLANE)
    if spec is None or spec.loader is None:
        raise RuntimeError("CONTROL_PLANE_UNAVAILABLE")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def correlated_send_ack(
    *,
    correlation_id: str,
    text: str,
    sender: str = "C1@AG",
    target: str = "C2-OBS",
    kind: str = "TASK_DRY_RUN",
) -> dict[str, Any]:
    """Write a live inbox message and ack. Does not acquire leases or mutate WAL."""
    plane = load_control_plane()
    payload = {
        "correlation_id": correlation_id,
        "text": text,
        "mode": "READ_ONLY",
        "writes_allowed": False,
        "intent": "SELF_INSPECT",
        "risk_class": "LOW",
    }
    msg = plane.send(sender, target, kind, payload, False)
    ack = plane.ack(msg["message_id"], target)
    send_receipt = plane.RECEIPTS / f"{msg['message_id']}.send.json"
    ack_receipt = plane.RECEIPTS / f"{msg['message_id']}.{target}.ack.receipt.json"
    inbox = plane.INBOX / f"{msg['message_id']}.json"
    return {
        "KIND": "LIVE_UCP_SEND_ACK",
        "MESSAGE_ID": msg["message_id"],
        "CORRELATION_ID": msg.get("correlation_id") or correlation_id,
        "SENDER": sender,
        "TARGET": target,
        "UCP_KIND": kind,
        "INBOX_PATH": str(inbox),
        "SEND_RECEIPT_PATH": str(send_receipt),
        "ACK_RECEIPT_PATH": str(ack_receipt),
        "SEND_RECEIPT_EXISTS": send_receipt.is_file(),
        "ACK_RECEIPT_EXISTS": ack_receipt.is_file(),
        "INBOX_EXISTS": inbox.is_file(),
        "ACK_STATUS": ack.get("status"),
        "LEASE_ACQUIRED": False,
        "WAL_WRITTEN": False,
        "CANONICAL_MUTATION": False,
        "COMMAND_FABRIC_E2E_PROVEN": False,
        "HTTP_PRIMARY": True,
        "NATS_PRIMARY": False,
        "UCP_IMPLEMENTATION": EXISTING_CONTROL_PLANE,
        "UCP_REBUILT": False,
    }
