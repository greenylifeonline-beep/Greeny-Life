from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Callable


@dataclass
class StageResult:
    stage: str
    status: str
    confidence: float | None
    evidence: list[str]
    provider: str
    latency_ms: float
    fallback_used: bool
    warnings: list[str] = field(default_factory=list)
    payload: dict[str, Any] = field(default_factory=dict)

    def as_trace(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "status": self.status,
            "confidence": self.confidence,
            "evidence": list(self.evidence),
            "provider": self.provider,
            "latency_ms": round(self.latency_ms, 3),
            "fallback_used": self.fallback_used,
            "warnings": list(self.warnings),
        }


def run_stage(stage: str, provider: str, fn: Callable[[], dict[str, Any]]) -> StageResult:
    started = perf_counter()
    warnings: list[str] = []
    fallback_used = False
    try:
        payload = fn()
        status = str(payload.get("status") or "OK")
        fallback_used = bool(payload.get("fallback_used", False))
        warnings = list(payload.get("warnings") or [])
        confidence = payload.get("confidence")
        if confidence is not None:
            confidence = float(confidence)
        evidence = list(payload.get("evidence") or [])
    except Exception as exc:
        status = "FAILED"
        payload = {"error": type(exc).__name__, "message": str(exc)}
        confidence = None
        evidence = [f"{type(exc).__name__}:{exc}"]
        warnings = ["STAGE_EXCEPTION"]
    latency_ms = (perf_counter() - started) * 1000.0
    return StageResult(
        stage=stage,
        status=status,
        confidence=confidence,
        evidence=evidence,
        provider=provider,
        latency_ms=latency_ms,
        fallback_used=fallback_used,
        warnings=warnings,
        payload=payload,
    )
