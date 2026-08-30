import pytest

from raios.resource_fabric.executable_adapters import (
    PROVIDERS, ProviderGateError, ProviderRequest, build_executable_adapter,
)


def proof(provider, **overrides):
    value = {
        "identity": f"{provider}-identity",
        "auth_proven": True,
        "storage_proven": True,
        "storage_free_bytes": 10_000,
        "capacity_proven": True,
        "capacity_units": 8,
        "gpu_sku": "PROVEN-GPU",
        "gpu_vram_bytes": 16_000,
        "active_session_proven": False,
        "provenance": ("receipt:current",),
    }
    value.update(overrides)
    return value


@pytest.mark.parametrize("provider", PROVIDERS)
def test_stage_is_non_mutating_for_every_provider(provider):
    adapter = build_executable_adapter(provider, proof(provider))
    staged = adapter.stage(ProviderRequest(operation="store", bytes_required=100))
    assert staged["status"] == "STAGED_READ_ONLY"
    assert staged["mutation"] is False
@pytest.mark.parametrize("provider", PROVIDERS)
def test_complete_current_proof_can_reach_injected_canonical_adapter(provider):
    adapter = build_executable_adapter(provider, proof(provider))
    request = ProviderRequest(operation="compute", capacity_required=2)
    result = adapter.execute(
        adapter.stage(request),
        {"seat": "C1", "verified": True},
        mutation_adapter=lambda req: {"accepted": req.operation},
    )
    assert result["status"] == "EXECUTED"
    assert result["result"] == {"accepted": "compute"}


@pytest.mark.parametrize("missing,expected", [
    ({"auth_proven": False}, "AUTH_OR_PROVENANCE_NOT_PROVEN"),
    ({"storage_proven": False}, "STORAGE_CAPACITY_NOT_PROVEN"),
    ({"capacity_proven": False}, "CURRENT_CAPACITY_NOT_PROVEN"),
    ({"gpu_sku": None}, "GPU_SKU_VRAM_NOT_PROVEN"),
])
def test_missing_proof_fails_closed(missing, expected):
    adapter = build_executable_adapter("KAGGLE", proof("KAGGLE", **missing))
    request = ProviderRequest(operation="run", bytes_required=1,
                              capacity_required=1, gpu_required=True)
    with pytest.raises(ProviderGateError, match=expected):
        adapter.execute(adapter.stage(request), {"seat": "C1", "verified": True}, lambda req: None)
def test_account_quota_does_not_equal_current_gpu_capacity():
    adapter = build_executable_adapter(
        "KAGGLE",
        proof("KAGGLE", capacity_proven=False, capacity_units=None,
              gpu_sku=None, gpu_vram_bytes=None),
    )
    request = ProviderRequest(operation="gpu", gpu_required=True)
    with pytest.raises(ProviderGateError, match="CURRENT_CAPACITY_NOT_PROVEN"):
        adapter.execute(adapter.stage(request), {"seat": "C1", "verified": True}, lambda req: None)


def test_paid_and_mutation_adapter_are_separate_gates():
    adapter = build_executable_adapter("MODAL", proof("MODAL"))
    staged = adapter.stage(ProviderRequest(operation="paid", paid=True))
    with pytest.raises(ProviderGateError, match="C1_PAID_AUTH_REQUIRED"):
        adapter.execute(staged, {"seat": "C1", "verified": True}, lambda req: None)
    with pytest.raises(ProviderGateError, match="CANONICAL_MUTATION_ADAPTER_REQUIRED"):
        adapter.execute(staged, {"seat": "C1", "verified": True, "paid_allowed": True})


def test_unknown_provider_rejected():
    with pytest.raises(ValueError, match="UNKNOWN_PROVIDER"):
        build_executable_adapter("OTHER", {})
