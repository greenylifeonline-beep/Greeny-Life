"""A22 elastic compute contracts + GPU_VALUE_PER_MINUTE. No paid setup."""
from __future__ import annotations

from typing import Any, Protocol

from ..identity import FailClosed, canonical_json, deterministic_id, utc_now
from ..models import ComputeProviderKind


class ComputeProvider(Protocol):
    kind: ComputeProviderKind

    def discover(self) -> dict[str, Any]: ...
    def health(self) -> dict[str, Any]: ...
    def capabilities(self) -> dict[str, Any]: ...
    def memory(self) -> dict[str, Any]: ...
    def compute(self) -> dict[str, Any]: ...
    def context_limit(self) -> dict[str, Any]: ...
    def cost(self) -> dict[str, Any]: ...
    def quota(self) -> dict[str, Any]: ...
    def privacy_class(self) -> str: ...
    def risk_class(self) -> str: ...
    def load_model(self, name: str) -> dict[str, Any]: ...
    def unload_model(self, name: str) -> dict[str, Any]: ...
    def execute(self, job: dict[str, Any]) -> dict[str, Any]: ...
    def cancel(self, job_id: str) -> dict[str, Any]: ...


class BaseProvider:
    kind = ComputeProviderKind.LOCAL_CPU
    available = True

    def discover(self) -> dict[str, Any]:
        return {"kind": self.kind.value, "available": self.available, "paid_setup": False}

    def health(self) -> dict[str, Any]:
        return {"ok": self.available}

    def capabilities(self) -> dict[str, Any]:
        return {"infer": True, "train": False}

    def memory(self) -> dict[str, Any]:
        return {"ram_gb": 8}

    def compute(self) -> dict[str, Any]:
        return {"gpu": self.kind in {ComputeProviderKind.KAGGLE_GPU, ComputeProviderKind.TEMPORARY_GPU}}

    def context_limit(self) -> dict[str, Any]:
        return {"tokens": 8192}

    def cost(self) -> dict[str, Any]:
        return {"unit": "none", "amount": 0}

    def quota(self) -> dict[str, Any]:
        return {"remaining": "UNKNOWN"}

    def privacy_class(self) -> str:
        return "LOCAL" if "LOCAL" in self.kind.value else "REMOTE_UNCONFIGURED"

    def risk_class(self) -> str:
        return "LOW" if self.kind is ComputeProviderKind.LOCAL_CPU else "UNKNOWN"

    def load_model(self, name: str) -> dict[str, Any]:
        if name.lower().startswith("qwen3.6") or "35b" in name.lower():
            raise FailClosed("QWEN36_INSTALL_NOT_AUTHORIZED")
        return {"loaded": False, "reason": "STUB"}

    def unload_model(self, name: str) -> dict[str, Any]:
        return {"unloaded": True}

    def execute(self, job: dict[str, Any]) -> dict[str, Any]:
        return {"executed": False, "reason": "STUB_NO_PAID_PROVIDER"}

    def cancel(self, job_id: str) -> dict[str, Any]:
        return {"cancelled": True, "job_id": job_id}


class LocalOllamaProvider(BaseProvider):
    kind = ComputeProviderKind.LOCAL_OLLAMA
    available = False


class KaggleGpuProvider(BaseProvider):
    kind = ComputeProviderKind.KAGGLE_GPU
    available = False


class RemoteOpenAIProvider(BaseProvider):
    kind = ComputeProviderKind.REMOTE_OPENAI_COMPATIBLE
    available = False


class FutureCloudProvider(BaseProvider):
    kind = ComputeProviderKind.FUTURE_CLOUD
    available = False


class TemporaryGpuProvider(BaseProvider):
    kind = ComputeProviderKind.TEMPORARY_GPU
    available = False


PROVIDERS = {
    ComputeProviderKind.LOCAL_CPU: BaseProvider,
    ComputeProviderKind.LOCAL_OLLAMA: LocalOllamaProvider,
    ComputeProviderKind.KAGGLE_GPU: KaggleGpuProvider,
    ComputeProviderKind.REMOTE_OPENAI_COMPATIBLE: RemoteOpenAIProvider,
    ComputeProviderKind.FUTURE_CLOUD: FutureCloudProvider,
    ComputeProviderKind.TEMPORARY_GPU: TemporaryGpuProvider,
}


def gpu_value_per_minute(gain: dict[str, float], minutes: float) -> float:
    if minutes <= 0:
        raise FailClosed("GPU_MINUTES_INVALID")
    score = (
        0.25 * float(gain.get("capability_gain") or 0)
        + 0.20 * float(gain.get("validated_training_data") or 0)
        + 0.15 * float(gain.get("adapter_improvement") or 0)
        + 0.15 * float(gain.get("benchmark_evidence") or 0)
        + 0.15 * float(gain.get("teacher_correction") or 0)
        + 0.10 * float(gain.get("reusable_skill") or 0)
    )
    return score / minutes


class ComputeScheduler:
    def __init__(self, store: Any) -> None:
        self.store = store
        self.providers = {kind: cls() for kind, cls in PROVIDERS.items()}

    def schedule(self, job: dict[str, Any]) -> dict[str, Any]:
        gain = job.get("gain") or {}
        minutes = float(job.get("minutes") or 1)
        value = gpu_value_per_minute(gain, minutes)
        uses_gpu = bool(job.get("gpu"))
        if uses_gpu and value <= 0:
            raise FailClosed("GPU_JOB_WITHOUT_MEASURABLE_GAIN")
        job_id = deterministic_id("job", canonical_json(job))
        payload = {
            "job_id": job_id,
            "gpu_value_per_minute": value,
            "scheduled": not uses_gpu or value > 0,
            "goals": ["privacy", "latency", "cost", "GPU_VALUE_PER_MINUTE", "quota", "warm_affinity", "failure_recovery"],
            "paid_setup": False,
        }
        self.store.conn.execute(
            "INSERT INTO compute_jobs(job_id, provider, gpu_value_per_minute, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (job_id, str(job.get("provider") or "LOCAL_CPU"), value, canonical_json(payload), utc_now()),
        )
        return payload
