"""A17.9 Native Main Cortex integration contract.

The cortex is a replaceable Qwen-class provider. It never owns identity,
canonical memory, knowledge, tool authority, governance, or durability.
Cortex output is always a proposal.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from ..identity import (
    CORTEX_FAMILY,
    CORTEX_IS_IDENTITY,
    CORTEX_MASTER_CANDIDATE,
    ORGANISM_ID,
    FailClosed,
    deterministic_id,
    utc_now,
)
from ..models import CortexProposal, CortexProviderKind, EventType


class MainCortex(Protocol):
    kind: CortexProviderKind

    def discover(self) -> dict[str, Any]: ...
    def load(self) -> dict[str, Any]: ...
    def unload(self) -> dict[str, Any]: ...
    def health(self) -> dict[str, Any]: ...
    def capabilities(self) -> dict[str, Any]: ...
    def infer(self, prompt: str, **kwargs: Any) -> CortexProposal: ...
    def structured_infer(self, prompt: str, schema: dict[str, Any], **kwargs: Any) -> CortexProposal: ...
    def tool_plan(self, task: dict[str, Any]) -> CortexProposal: ...
    def context_limits(self) -> dict[str, Any]: ...
    def resource_requirements(self) -> dict[str, Any]: ...
    def adapter_attach(self, adapter_id: str) -> dict[str, Any]: ...
    def adapter_detach(self, adapter_id: str) -> dict[str, Any]: ...


def _proposal(kind: CortexProviderKind, model: str, text: str, structured: dict[str, Any] | None = None, tools: list | None = None) -> CortexProposal:
    return CortexProposal(
        proposal_id=deterministic_id("prop", kind.value, model, text[:64]),
        provider_kind=kind.value,
        model_name=model,
        text=text,
        structured=structured or {},
        tool_plan=tuple(tools or ()),
        execution_authority=False,
        mutates_canonical=False,
    )


@dataclass
class StubCortex:
    kind: CortexProviderKind = CortexProviderKind.STUB
    model_name: str = "stub-cortex"
    loaded: bool = False
    adapters: list[str] = field(default_factory=list)
    available: bool = True

    def discover(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "available": self.available,
            "model_name": self.model_name,
            "family": CORTEX_FAMILY,
            "selected_master_candidate": CORTEX_MASTER_CANDIDATE,
            "installed": False,
            "identity_owner": ORGANISM_ID,
            "cortex_is_identity": CORTEX_IS_IDENTITY,
        }

    def load(self) -> dict[str, Any]:
        self.loaded = True
        return {"loaded": True, "model_name": self.model_name}

    def unload(self) -> dict[str, Any]:
        self.loaded = False
        return {"loaded": False}

    def health(self) -> dict[str, Any]:
        return {"ok": self.available, "loaded": self.loaded, "status": "STUB"}

    def capabilities(self) -> dict[str, Any]:
        return {"infer": True, "structured_infer": True, "tool_plan": True, "adapters": True}

    def infer(self, prompt: str, **kwargs: Any) -> CortexProposal:
        return _proposal(self.kind, self.model_name, f"PROPOSAL:{prompt[:200]}")

    def structured_infer(self, prompt: str, schema: dict[str, Any], **kwargs: Any) -> CortexProposal:
        return _proposal(self.kind, self.model_name, prompt[:200], {"schema": schema, "proposal": True})

    def tool_plan(self, task: dict[str, Any]) -> CortexProposal:
        return _proposal(self.kind, self.model_name, "tool-plan", {"task": task}, [{"tool": "none", "reason": "proposal_only"}])

    def context_limits(self) -> dict[str, Any]:
        return {"tokens": 8192, "characters": 32000}

    def resource_requirements(self) -> dict[str, Any]:
        return {"gpu": False, "ram_gb": 1, "disk_gb": 1}

    def adapter_attach(self, adapter_id: str) -> dict[str, Any]:
        self.adapters.append(adapter_id)
        return {"attached": adapter_id}

    def adapter_detach(self, adapter_id: str) -> dict[str, Any]:
        self.adapters = [item for item in self.adapters if item != adapter_id]
        return {"detached": adapter_id}


class LocalOllamaCortex(StubCortex):
    kind: CortexProviderKind = CortexProviderKind.LOCAL_OLLAMA
    model_name: str = CORTEX_MASTER_CANDIDATE

    def discover(self) -> dict[str, Any]:
        data = super().discover()
        data["available"] = False
        data["reason"] = "HEAVYWEIGHT_INSTALL_NOT_PERFORMED"
        data["safe_to_install"] = False
        return data

    def load(self) -> dict[str, Any]:
        raise FailClosed("QWEN36_INSTALL_NOT_AUTHORIZED")


class RemoteOpenAICompatibleCortex(StubCortex):
    kind = CortexProviderKind.REMOTE_OPENAI_COMPATIBLE
    model_name = "openai-compatible-remote"

    def discover(self) -> dict[str, Any]:
        data = super().discover()
        data["available"] = False
        data["reason"] = "REMOTE_ENDPOINT_UNCONFIGURED"
        return data


class KaggleRemoteCortex(StubCortex):
    kind = CortexProviderKind.KAGGLE_REMOTE
    model_name = "kaggle-remote"

    def discover(self) -> dict[str, Any]:
        data = super().discover()
        data["available"] = False
        data["reason"] = "KAGGLE_REMOTE_UNCONFIGURED"
        return data


class FutureLocalRuntimeCortex(StubCortex):
    kind = CortexProviderKind.FUTURE_LOCAL_RUNTIME
    model_name = "future-local-runtime"


PROVIDERS = {
    CortexProviderKind.STUB: StubCortex,
    CortexProviderKind.LOCAL_OLLAMA: LocalOllamaCortex,
    CortexProviderKind.REMOTE_OPENAI_COMPATIBLE: RemoteOpenAICompatibleCortex,
    CortexProviderKind.KAGGLE_REMOTE: KaggleRemoteCortex,
    CortexProviderKind.FUTURE_LOCAL_RUNTIME: FutureLocalRuntimeCortex,
}


class CortexRegistry:
    def __init__(self, store: Any) -> None:
        self.store = store
        self.active: MainCortex = StubCortex()

    def replace(self, kind: CortexProviderKind | str) -> dict[str, Any]:
        kind = CortexProviderKind(kind)
        identity_before = self.store.identity()
        self.active = PROVIDERS[kind]()
        identity_after = self.store.identity()
        if identity_before["organism_id"] != identity_after["organism_id"]:
            raise FailClosed("IDENTITY_MUTATED_ON_CORTEX_REPLACE")
        if identity_after.get("cortex_is_identity"):
            raise FailClosed("CORTEX_MUST_NOT_OWN_IDENTITY")
        payload = {
            "provider": kind.value,
            "organism_id": identity_after["organism_id"],
            "identity_preserved": True,
            "memory_authority": "RAIOS",
            "cortex_is_identity": False,
        }
        self.store.append_event(EventType.CORTEX_REPLACED, kind.value, payload)
        return payload

    def apply_proposal_as_canonical(self, proposal: CortexProposal) -> None:
        raise FailClosed("DIRECT_CANONICAL_MUTATION_REJECTED")
