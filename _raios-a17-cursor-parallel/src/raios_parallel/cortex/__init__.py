"""Model provider SPI. Output is proposal only. Cortex is not identity."""
from __future__ import annotations

from typing import Any

from ..identity import CORTEX_FAMILY, CORTEX_IS_IDENTITY, CORTEX_TARGET, ORGANISM_ID, FailClosed, deterministic_id, utc_now
from ..models import DegradedMode


class CortexProposal:
    def __init__(self, text: str, provider: str, model: str) -> None:
        self.proposal_id = deterministic_id("prop", provider, text[:40])
        self.text = text
        self.provider = provider
        self.model = model
        self.execution_authority = False
        self.created_at = utc_now()


class ModelProvider:
    kind = "STUB"
    model_name = "stub"

    def discover(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "model": self.model_name,
            "family": CORTEX_FAMILY,
            "target": CORTEX_TARGET,
            "available": False,
            "cortex_is_identity": CORTEX_IS_IDENTITY,
            "identity_owner": ORGANISM_ID,
        }

    def health(self) -> dict[str, Any]:
        return {"ok": False, "status": "UNCONFIGURED"}

    def load(self) -> dict[str, Any]:
        if "qwen3.6" in self.model_name.lower() or "35b" in self.model_name.lower():
            raise FailClosed("QWEN36_INSTALL_NOT_AUTHORIZED")
        return {"loaded": False}

    def unload(self) -> dict[str, Any]:
        return {"loaded": False}

    def infer(self, prompt: str, **kwargs: Any) -> CortexProposal:
        return CortexProposal(f"PROPOSAL:{prompt[:180]}", self.kind, self.model_name)

    def structured_infer(self, prompt: str, schema: dict[str, Any], **kwargs: Any) -> CortexProposal:
        return self.infer(prompt)

    def tool_plan(self, task: dict[str, Any]) -> CortexProposal:
        return CortexProposal("tool-plan-proposal", self.kind, self.model_name)

    def context_limits(self) -> dict[str, Any]:
        return {"tokens": 8192}

    def resource_requirements(self) -> dict[str, Any]:
        return {"gpu": False}

    def adapter_attach(self, adapter_id: str) -> dict[str, Any]:
        return {"attached": adapter_id}

    def adapter_detach(self, adapter_id: str) -> dict[str, Any]:
        return {"detached": adapter_id}


class OllamaLocalProvider(ModelProvider):
    kind = "OLLAMA_LOCAL"
    model_name = CORTEX_TARGET


class KaggleRemoteProvider(ModelProvider):
    kind = "KAGGLE_REMOTE"
    model_name = "kaggle-remote"


class OpenAICompatibleProvider(ModelProvider):
    kind = "OPENAI_COMPATIBLE"
    model_name = "openai-compatible"


class FutureNativeRuntimeProvider(ModelProvider):
    kind = "FUTURE_NATIVE_RUNTIME"
    model_name = "future-native"


class CortexRegistry:
    def __init__(self, store: Any, governance: Any) -> None:
        self.store = store
        self.governance = governance
        self.active: ModelProvider = ModelProvider()
        self.providers = {
            "OLLAMA_LOCAL": OllamaLocalProvider,
            "KAGGLE_REMOTE": KaggleRemoteProvider,
            "OPENAI_COMPATIBLE": OpenAICompatibleProvider,
            "FUTURE_NATIVE_RUNTIME": FutureNativeRuntimeProvider,
            "STUB": ModelProvider,
        }

    def replace(self, kind: str) -> dict[str, Any]:
        before = self.store.identity()
        self.active = self.providers[kind]()
        after = self.store.identity()
        if before["organism_id"] != after["organism_id"]:
            raise FailClosed("IDENTITY_MUTATED_ON_CORTEX_REPLACE")
        self.store.append_event("CORTEX_REPLACED", kind, {"identity_preserved": True})
        return {"provider": kind, "organism_id": after["organism_id"], "identity_preserved": True, "cortex_is_identity": False}

    def apply_as_execution(self, proposal: CortexProposal) -> None:
        self.governance.reject("EXECUTE_FROM_MODEL", {"proposal_id": proposal.proposal_id})

    def fail_provider(self) -> dict[str, Any]:
        from ..maintenance import Maintenance

        # degraded mode entered by caller typically
        return self.store.set_mode(DegradedMode.SAFE_MINIMUM)
