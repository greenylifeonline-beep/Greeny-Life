"""Vendor-neutral TransportProvider contract and logical routes."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

LOGICAL_KINDS = (
    "commands",
    "results",
    "receipts",
    "events",
    "health",
    "failures",
    "acks",
)

TREE_ROOT = Path(r"C:\Users\Ghanam\Documents\Codex\Greeny-Life-Repair")
EXPECTED_HEAD = "12603d02253547c7727bc84ce68c318e8e9258bc"


@dataclass(frozen=True)
class LogicalRoute:
    kind: str
    key: str

    @property
    def path(self) -> str:
        return f"{self.kind}/{self.key}"


def parse_logical_route(route: str) -> LogicalRoute:
    kind, sep, key = str(route).partition("/")
    if not sep or kind not in LOGICAL_KINDS or not key.strip():
        raise ValueError("INVALID_LOGICAL_ROUTE")
    return LogicalRoute(kind, key.strip())


def runtime_key(runtime: str) -> str:
    return str(runtime).replace("@", "").replace("/", "")


def derive_logical_route(envelope: dict[str, Any]) -> LogicalRoute:
    if envelope.get("logical_route"):
        return parse_logical_route(str(envelope["logical_route"]))
    schema = str(envelope.get("schema") or "")
    runtime = str(envelope.get("receiver_runtime") or envelope.get("target") or "")
    corr = str(envelope.get("correlation_id") or "")
    if schema == "raios.cross-host-packet.v1" and runtime:
        return LogicalRoute("commands", runtime)
    if schema == "raios.message-ack.v1" and runtime:
        return LogicalRoute("acks", runtime)
    if schema in ("raios.c5-routed-response.v1", "raios.message.v1") and corr:
        return LogicalRoute("results", corr)
    if schema == "raios.user-route-receipt.v1" and runtime:
        return LogicalRoute("receipts", runtime)
    raise ValueError("INVALID_LOGICAL_ROUTE")


def wire_envelope(envelope: dict[str, Any]) -> dict[str, Any]:
    return {k: v for k, v in envelope.items() if k != "logical_route"}


@dataclass
class FabricConfig:
    nats_url: str = "nats://127.0.0.1:4222"
    stream: str = "RAIOS_FABRIC"
    subject_root: str = "raios.fabric"
    tree_root: Path = TREE_ROOT
    evidence_root: Path = TREE_ROOT / ".ai-os" / "receipts" / "command-fabric" / "fabric"
    health_path: Path = Path(r"C:\ProgramData\RAIOS\transport\logs\RAIOS-FABRIC-BRIDGE-HEALTH.json")
    token_path: Path = Path(r"C:\ProgramData\RAIOS\transport\runtime\fabric.token")
    c5_chat: str = "http://127.0.0.1:8766/api/chat"
    c5_health: str = "http://127.0.0.1:8766/health"
    allowed_actors: frozenset[str] = field(default_factory=lambda: frozenset({"C1", "C2", "C5"}))
    ack_wait_seconds: float = 120.0
    js_puback_timeout: float = 10.0
    http_timeout_seconds: float = 60.0
    expected_head: str = EXPECTED_HEAD
    hmac_token: str = ""


@dataclass
class IncomingMessage:
    envelope: dict[str, Any]
    receipt_id: str
    delivery_count: int
    stream_seq: str | None
    logical_route: str


class TransportProvider(ABC):
    transport_id: str
    runtime_id: str = ""
    role_id: str = ""

    @abstractmethod
    async def connect(self) -> None: ...

    @abstractmethod
    async def health(self) -> dict[str, Any]: ...

    @abstractmethod
    async def publish(self, envelope: dict[str, Any]) -> str: ...

    @abstractmethod
    async def subscribe(self, logical_route: str, durable: str | None = None): ...

    @abstractmethod
    async def request(self, envelope: dict[str, Any], timeout: float = 5.0) -> dict[str, Any]: ...

    @abstractmethod
    async def reply(self, request_id: str, envelope: dict[str, Any]) -> None: ...

    @abstractmethod
    async def ack(self, receipt_id: str) -> None: ...

    @abstractmethod
    async def nack(self, receipt_id: str, reason: str | None = None) -> None: ...

    @abstractmethod
    async def close(self) -> None: ...
