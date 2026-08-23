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
        from .cortex import named_cortex_model, resolve_endpoint, resolve_role

        self.provider_calls += 1
        admission = self.governor.admit(requirement.capability)
        role = resolve_role("CORTEX_MODEL")
        endpoint = resolve_endpoint("CORTEX_MODEL")
        named = str(endpoint.get("model") or role.get("model") or named_cortex_model())
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
                "role": None,
                "local_winner": False,
                "laptop_is_model_host": False,
                "admission": admission.reason,
            }
        configured = bool(endpoint.get("configured"))
        base = {
            "provider": "main-cortex-capability",
            "fallback_used": False,
            "model": named,
            "role": "CORTEX_MODEL",
            "local_winner": False,
            "winner_final": False,
            "student_substituted": False,
            "laptop_is_model_host": False,
            "local_ollama_ne_cortex_criterion": True,
            "local_ram_ne_cortex_criterion": True,
            "endpoint_kind": endpoint.get("kind"),
            "endpoint_configured": configured,
            "transport": "openai-compatible",
            "source_patch_required": False,
            "admission": admission.reason,
        }
        if not configured:
            return {
                **base,
                "reason": endpoint.get("reason") or "ENDPOINT_UNBOUND",
                "error": "MODEL_MISSING",
                "llm": False,
                "model_name_bound": False,
            }
        return {
            **base,
            "reason": "TIER3_SEMANTIC",
            "llm": True,
            "model_name_bound": True,
        }

    def execute(self, decision: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        from .cortex import model_in_role, named_cortex_model, resolve_endpoint, resolve_role

        role = resolve_role("CORTEX_MODEL")
        endpoint = resolve_endpoint("CORTEX_MODEL")
        named = str(endpoint.get("model") or role.get("model") or named_cortex_model())
        chosen = str(decision.get("model") or named)
        if decision.get("error") == "MODEL_MISSING" or not decision.get("model_name_bound"):
            return {
                "ok": False,
                "error": "MODEL_MISSING",
                "reason": decision.get("reason") or endpoint.get("reason") or "ENDPOINT_UNBOUND",
                "response": "",
                "model": named,
                "role": "CORTEX_MODEL",
                "local_winner": False,
                "winner_final": False,
                "model_name_bound": False,
                "llm_executed": False,
                "student_substituted": False,
                "provider_execute_called": True,
                "endpoint_kind": endpoint.get("kind"),
                "endpoint_configured": bool(endpoint.get("configured")),
                "laptop_is_model_host": False,
                "transport": "openai-compatible",
                "gl005_proven": False,
            }
        if decision.get("provider") != "main-cortex-capability" or not model_in_role(chosen, "CORTEX_MODEL"):
            return {
                "ok": False,
                "error": "STUDENT_NE_CORTEX",
                "response": "",
                "model": decision.get("model"),
                "role": "CORTEX_MODEL",
                "local_winner": False,
                "model_name_bound": False,
                "llm_executed": False,
                "student_substituted": False,
                "provider_execute_called": True,
                "gl005_proven": False,
            }
        provider = next(
            (row for row in self.providers if getattr(row, "provider_id", None) == "main-cortex-capability"),
            None,
        )
        if provider is not None and hasattr(provider, "run"):
            rec = provider.run({**payload, "model": chosen})
        else:
            from .qwen_runtime import generate

            rec = generate(str(payload.get("text") or payload.get("prompt") or ""), model=chosen)
        executed = bool(rec.get("ok"))
        if executed:
            self.llm_calls += 1
        rec["llm_executed"] = executed
        rec["model_name_bound"] = True
        rec["student_substituted"] = False
        rec["provider_execute_called"] = True
        rec["model"] = chosen
        rec["role"] = "CORTEX_MODEL"
        rec["local_winner"] = False
        rec["winner_final"] = False
        rec["provider"] = "main-cortex-capability"
        rec["endpoint_kind"] = endpoint.get("kind")
        rec["endpoint_configured"] = bool(endpoint.get("configured"))
        rec["laptop_is_model_host"] = False
        rec["transport"] = "openai-compatible"
        rec["source_patch_required"] = False
        return rec

    def metrics(self) -> dict[str, Any]:
        total = max(self.provider_calls, 1)
        return {
            "provider_calls": self.provider_calls,
            "llm_calls": self.llm_calls,
            "deterministic_resolution_ratio": round(self.deterministic_resolutions / total, 4),
            "local_execution_ratio": round((total - self.llm_calls) / total, 4),
        }
