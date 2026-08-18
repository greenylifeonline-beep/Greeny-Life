"""Safe counterfactual failures from real incidents. Sandbox only."""
from __future__ import annotations

from typing import Any

from .config import FailClosed, deterministic_id, utc_now
from .event_bus import EventBus

HTTP_500_FAMILY = (
    "timeout",
    "connection_refused",
    "model_unloaded",
    "oom",
    "malformed_response",
    "empty_response",
    "http_200_invalid_semantic",
    "context_overflow",
    "wrong_model",
    "race",
    "partial_write",
    "stale_evidence",
    "missing_response_hash",
    "missing_final",
    "false_pass",
    "child_exit_1",
    "interactive_else_parse",
)


class FailureImagination:
    def __init__(self, bus: EventBus) -> None:
        self.bus = bus

    def imagine(self, seed: dict[str, Any], *, sandbox: bool = True) -> list[dict[str, Any]]:
        if not sandbox:
            raise FailClosed("PRODUCTION_SABOTAGE_FORBIDDEN")
        family = list(HTTP_500_FAMILY)
        if seed.get("kind") not in {"http_500", "atomic_certification", "ollama"}:
            family = family[:6]
        out = []
        for name in family:
            rec = {
                "imagined_id": deterministic_id("img", name, str(seed.get("id") or "seed")),
                "seed": seed.get("kind"),
                "failure": name,
                "hypothesis": f"variant '{name}' shares recovery surface with {seed.get('kind')}",
                "reproduction_strategy": {"sandbox": True, "inject": name},
                "expected_signal": {"typed_error": name.upper(), "success_token": False},
                "recovery_strategy": {"fail_closed": True, "persist_failure_receipt": True, "no_false_pass": True},
                "test": f"test_imagined_{name}",
                "result": "PENDING",
                "generalization_candidate": True,
                "production_runtime_sabotaged": False,
                "created_at": utc_now(),
            }
            self.bus.emit("EXPERIMENT", "failure_imagination", rec, risk_class="LOW")
            out.append(rec)
        return out
