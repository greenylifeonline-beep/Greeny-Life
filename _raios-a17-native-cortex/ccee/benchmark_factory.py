"""Self-generated benchmarks with leakage prevention."""
from __future__ import annotations

from typing import Any

from .config import deterministic_id
from .event_bus import EventBus
from .transfer import TransferEngine

VARIANTS = (
    "near",
    "unseen",
    "adversarial",
    "partial_information",
    "contradictory",
    "tool_disabled",
    "cross_domain",
    "failure",
)


class BenchmarkFactory:
    def __init__(self, bus: EventBus, transfer: TransferEngine) -> None:
        self.bus = bus
        self.transfer = transfer

    def generate(self, capability: str, seed: dict[str, Any]) -> dict[str, Any]:
        train = []
        unseen = []
        for i, kind in enumerate(VARIANTS):
            case = {
                "id": deterministic_id("bench", capability, kind, str(i)),
                "capability": capability,
                "variant": kind,
                "seed": seed.get("id"),
                "expected": seed.get("expected") if kind != "unseen" else seed.get("unseen_expected", seed.get("expected")),
            }
            if kind in {"near", "failure"}:
                self.transfer.register_train(case["id"])
                train.append(case)
            else:
                self.transfer.register_unseen(case["id"])
                unseen.append(case)
            self.bus.emit("BENCHMARK", "benchmark_factory", case)
        leaked = set(c["id"] for c in train) & set(c["id"] for c in unseen)
        return {"train": train, "unseen": unseen, "leakage": bool(leaked)}
