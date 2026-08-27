"""In-process transport double. Not a second event bus. Used only in deterministic tests."""

from __future__ import annotations

from typing import Any


class FakeFabricTransport:
    EXISTING_PROVIDER = "scripts/ai-os/raios_transport/nats_provider.py"
    STREAM = "RAIOS_FABRIC"
    SUBJECT_ROOT = "raios.fabric"
    EXACTLY_ONCE_CLAIMED = False
    NATS_AT_LEAST_ONCE = True

    def __init__(self) -> None:
        self.published: list[dict[str, Any]] = []
        self.acked: list[str] = []
        self._seq = 0
        self.duplicate_next = False

    def command_subject(self, target: str) -> str:
        key = str(target).replace("@", "").replace("/", "")
        return f"{self.SUBJECT_ROOT}.commands.{key}"

    def result_subject(self, correlation_id: str) -> str:
        return f"{self.SUBJECT_ROOT}.results.{correlation_id}"

    def publish(self, envelope: dict[str, Any]) -> dict[str, Any]:
        self._seq += 1
        rec = {
            "STORED": True,
            "SEQUENCE": str(self._seq),
            "SUBJECT": envelope.get("subject") or self.command_subject(str(envelope.get("target") or "C5")),
            "STREAM": self.STREAM,
            "DUPLICATE_FLAG": bool(self.duplicate_next),
            "MSG_ID": envelope.get("nats_msg_id") or envelope.get("idempotency_key"),
            "NATS_AT_LEAST_ONCE": True,
            "EXACTLY_ONCE_CLAIMED": False,
        }
        self.duplicate_next = False
        stored = dict(envelope)
        stored["_delivery"] = rec
        self.published.append(stored)
        return rec

    def deliver_all(self, *, duplicate: bool = False) -> list[dict[str, Any]]:
        out = []
        for item in self.published:
            env = dict(item)
            env["delivery_count"] = 2 if duplicate else 1
            out.append(env)
        if duplicate:
            extra = []
            for item in list(out):
                again = dict(item)
                again["delivery_count"] = 2
                extra.append(again)
            out.extend(extra)
        return out

    def ack(self, receipt_id: str) -> None:
        self.acked.append(receipt_id)
