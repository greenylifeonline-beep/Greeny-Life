from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .governor import CognitiveResourceGovernor
from .provider_contracts import CapabilityRequirement, LanguageProvider, ProviderCapability


CAPABILITIES = (
    "LANGUAGE_ID",
    "DIALECT_CLASSIFICATION",
    "CODE_SWITCH_CLASSIFICATION",
    "SEMANTIC_INTERPRETATION",
    "SEMANTIC_REALIZATION",
    "SEMANTIC_VERIFICATION",
    "TERMINOLOGY_ADJUDICATION",
    "PRAGMATIC_INTERPRETATION",
)


class DeterministicProvider:
    provider_id = "deterministic-neuro-lingua"

    @property
    def capabilities(self) -> ProviderCapability:
        return ProviderCapability(
            provider_id=self.provider_id,
            capabilities=CAPABILITIES,
            languages=("ar-EG", "ar-GULF", "en", "nb-NO", "sv-SE", "da-DK"),
            local=True,
            quality_score=0.7,
            estimated_latency_ms=5,
        )

    async def execute(self, capability: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "DEFERRED_TO_KERNEL", "capability": capability, "payload_keys": sorted(payload)}


@dataclass
class ProviderRouter:
    governor: CognitiveResourceGovernor = field(default_factory=CognitiveResourceGovernor)
    providers: list[LanguageProvider] = field(default_factory=list)
    llm_calls: int = 0
    provider_calls: int = 0
    deterministic_resolutions: int = 0

    def __post_init__(self) -> None:
        if not self.providers:
            from .cortex import CortexProvider

            self.providers = [DeterministicProvider(), CortexProvider()]

    def route(self, requirement: CapabilityRequirement) -> dict[str, Any]:
        from .cortex import CORTEX_IDENTITY
        from .qwen_runtime import probe

        self.provider_calls += 1
        admission = self.governor.admit(requirement.capability)
        cortex_needed = requirement.capability in {
            "SEMANTIC_INTERPRETATION",
            "SEMANTIC_REALIZATION",
            "SEMANTIC_VERIFICATION",
        }
        if requirement.offline_required or not cortex_needed:
            self.deterministic_resolutions += 1
            return {
                "provider": "deterministic-neuro-lingua",
                "fallback_used": False,
                "reason": "TIER0_OR_TIER1" if not cortex_needed else (admission.reason or "TIER0_OR_TIER1"),
                "llm": False,
                "model_name_bound": False,
                "admission": admission.reason,
            }
        status = probe()
        if not status.get("cortex_live"):
            return {
                "provider": "main-cortex-capability",
                "fallback_used": False,
                "reason": "MODEL_MISSING",
                "error": "MODEL_MISSING",
                "llm": False,
                "model_name_bound": False,
                "model": CORTEX_IDENTITY,
                "student_substituted": False,
                "admission": admission.reason,
            }
        return {
            "provider": "main-cortex-capability",
            "fallback_used": False,
            "reason": "TIER3_SEMANTIC",
            "llm": True,
            "model_name_bound": True,
            "model": CORTEX_IDENTITY,
            "student_substituted": False,
            "admission": admission.reason,
        }

    def execute(self, decision: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        from .cortex import CORTEX_IDENTITY

        if decision.get("error") == "MODEL_MISSING" or not decision.get("model_name_bound"):
            return {
                "ok": False,
                "error": "MODEL_MISSING",
                "response": "",
                "model": CORTEX_IDENTITY,
                "model_name_bound": False,
                "llm_executed": False,
                "student_substituted": False,
                "gl005_proven": False,
            }
        if decision.get("model") != CORTEX_IDENTITY or decision.get("provider") != "main-cortex-capability":
            return {
                "ok": False,
                "error": "STUDENT_NE_CORTEX",
                "response": "",
                "model": decision.get("model"),
                "model_name_bound": False,
                "llm_executed": False,
                "student_substituted": False,
                "gl005_proven": False,
            }
        provider = next(
            (row for row in self.providers if getattr(row, "provider_id", None) == "main-cortex-capability"),
            None,
        )
        if provider is not None and hasattr(provider, "run"):
            rec = provider.run(payload)
        else:
            from .qwen_runtime import generate

            rec = generate(str(payload.get("text") or payload.get("prompt") or ""), model=CORTEX_IDENTITY)
        executed = bool(rec.get("ok"))
        if executed:
            self.llm_calls += 1
        rec["llm_executed"] = executed
        rec["model_name_bound"] = True
        rec["student_substituted"] = False
        rec["model"] = CORTEX_IDENTITY
        rec["provider"] = "main-cortex-capability"
        return rec

    def metrics(self) -> dict[str, Any]:
        total = max(self.provider_calls, 1)
        return {
            "provider_calls": self.provider_calls,
            "llm_calls": self.llm_calls,
            "deterministic_resolution_ratio": round(self.deterministic_resolutions / total, 4),
            "local_execution_ratio": round((total - self.llm_calls) / total, 4),
        }
