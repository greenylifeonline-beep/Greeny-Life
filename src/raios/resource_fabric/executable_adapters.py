"""Governed cloud execution adapters: proof-first and fail-closed."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

PROVIDERS = ("KAGGLE", "HUGGING_FACE", "ORACLE", "COLAB", "MODAL")


class ProviderGateError(RuntimeError):
    """A provider operation lacks a required current proof."""


@dataclass(frozen=True)
class ProviderProof:
    provider: str
    identity: str | None = None
    auth_proven: bool = False
    storage_proven: bool = False
    storage_free_bytes: int | None = None
    capacity_proven: bool = False
    capacity_units: float | None = None
    gpu_sku: str | None = None
    gpu_vram_bytes: int | None = None
    active_session_proven: bool = False
    provenance: tuple[str, ...] = ()

    @classmethod
    def from_mapping(cls, provider: str, value: Mapping[str, Any]) -> "ProviderProof":
        allowed = cls.__dataclass_fields__.keys()
        return cls(provider=provider, **{k: value[k] for k in allowed if k != "provider" and k in value})
@dataclass(frozen=True)
class ProviderRequest:
    operation: str
    bytes_required: int = 0
    capacity_required: float = 0
    gpu_required: bool = False
    paid: bool = False
    payload_ref: str | None = None


class GovernedExecutableAdapter:
    provider = ""

    def __init__(self, proof: ProviderProof | Mapping[str, Any]):
        self.proof = proof if isinstance(proof, ProviderProof) else ProviderProof.from_mapping(self.provider, proof)

    def probe_identity(self) -> dict[str, Any]:
        return {"provider": self.provider, "identity": self.proof.identity,
                "auth_proven": self.proof.auth_proven, "provenance": list(self.proof.provenance)}

    def probe_storage(self) -> dict[str, Any]:
        return {"provider": self.provider, "storage_proven": self.proof.storage_proven,
                "storage_free_bytes": self.proof.storage_free_bytes}

    def probe_capacity(self) -> dict[str, Any]:
        return {"provider": self.provider, "capacity_proven": self.proof.capacity_proven,
                "capacity_units": self.proof.capacity_units, "gpu_sku": self.proof.gpu_sku,
                "gpu_vram_bytes": self.proof.gpu_vram_bytes,
                "active_session_proven": self.proof.active_session_proven}

    def stage(self, request: ProviderRequest) -> dict[str, Any]:
        return {"status": "STAGED_READ_ONLY", "provider": self.provider,
                "request": request, "mutation": False}
    def _validate(self, request: ProviderRequest, authority: Mapping[str, Any]) -> None:
        if not self.proof.auth_proven or not self.proof.identity or not self.proof.provenance:
            raise ProviderGateError("AUTH_OR_PROVENANCE_NOT_PROVEN")
        if authority.get("seat") != "C1" or not authority.get("verified"):
            raise ProviderGateError("C1_AUTH_REQUIRED")
        if request.bytes_required:
            if not self.proof.storage_proven or self.proof.storage_free_bytes is None:
                raise ProviderGateError("STORAGE_CAPACITY_NOT_PROVEN")
            if self.proof.storage_free_bytes < request.bytes_required:
                raise ProviderGateError("INSUFFICIENT_PROVEN_STORAGE")
        if request.capacity_required or request.gpu_required:
            if not self.proof.capacity_proven or self.proof.capacity_units is None:
                raise ProviderGateError("CURRENT_CAPACITY_NOT_PROVEN")
            if self.proof.capacity_units < request.capacity_required:
                raise ProviderGateError("INSUFFICIENT_PROVEN_CAPACITY")
        if request.gpu_required and (not self.proof.gpu_sku or not self.proof.gpu_vram_bytes):
            raise ProviderGateError("GPU_SKU_VRAM_NOT_PROVEN")
        if request.paid and not authority.get("paid_allowed"):
            raise ProviderGateError("C1_PAID_AUTH_REQUIRED")

    def execute(self, staged: Mapping[str, Any], authority: Mapping[str, Any],
                mutation_adapter: Callable[[ProviderRequest], Any] | None = None) -> dict[str, Any]:
        request = staged.get("request")
        if staged.get("status") != "STAGED_READ_ONLY" or not isinstance(request, ProviderRequest):
            raise ProviderGateError("INVALID_STAGE")
        self._validate(request, authority)
        if mutation_adapter is None:
            raise ProviderGateError("CANONICAL_MUTATION_ADAPTER_REQUIRED")
        result = mutation_adapter(request)
        return {"status": "EXECUTED", "provider": self.provider, "result": result,
                "proof_provenance": list(self.proof.provenance)}
class KaggleExecutableAdapter(GovernedExecutableAdapter):
    provider = "KAGGLE"


class HuggingFaceExecutableAdapter(GovernedExecutableAdapter):
    provider = "HUGGING_FACE"


class OracleExecutableAdapter(GovernedExecutableAdapter):
    provider = "ORACLE"


class ColabExecutableAdapter(GovernedExecutableAdapter):
    provider = "COLAB"


class ModalExecutableAdapter(GovernedExecutableAdapter):
    provider = "MODAL"


ADAPTERS = {
    cls.provider: cls for cls in (
        KaggleExecutableAdapter, HuggingFaceExecutableAdapter,
        OracleExecutableAdapter, ColabExecutableAdapter, ModalExecutableAdapter,
    )
}


def build_executable_adapter(provider: str, proof: ProviderProof | Mapping[str, Any]) -> GovernedExecutableAdapter:
    try:
        adapter = ADAPTERS[provider.upper()]
    except KeyError as exc:
        raise ValueError(f"UNKNOWN_PROVIDER:{provider}") from exc
    return adapter(proof)
