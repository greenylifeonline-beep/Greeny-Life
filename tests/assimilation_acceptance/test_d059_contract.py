"""D-059 Qwen/Granite canonical assimilation acceptance contract.

This is intentionally implementation-agnostic.
It encodes what counts as proof and what does not.
"""

from __future__ import annotations


REQUIRED_FAMILIES = {"qwen", "granite"}

FORBIDDEN_PROOF_ONLY_KINDS = {
    "config",
    "model_name",
    "provider_config",
    "vault_record",
    "report_only",
    "archive_presence",
    "weight_presence",
    "branch_presence",
}

FORBIDDEN_RUNTIME_DEPENDENCIES = {
    "_raios-a17-native-cortex",
    "_raios-a17-integration-wave",
    "_raios-a17-cursor-parallel",
    "_raios-assimilation-runtime",
}


def validate_assimilation_record(record: dict) -> list[str]:
    errors: list[str] = []

    family = str(record.get("family") or "").lower()

    if family not in REQUIRED_FAMILIES:
        errors.append("UNKNOWN_OR_MISSING_FAMILY")

    capability_ids = record.get("capability_ids") or []
    if not capability_ids:
        errors.append("NO_CAPABILITY_IDS")

    if not record.get("source_provenance"):
        errors.append("NO_SOURCE_PROVENANCE")

    if record.get("proof_kind") in FORBIDDEN_PROOF_ONLY_KINDS:
        errors.append("NON_ASSIMILATION_PROOF_KIND")

    if record.get("source_independent") is not True:
        errors.append("SOURCE_INDEPENDENCE_NOT_PROVEN")

    if record.get("brain_wiring_proven") is not True:
        errors.append("BRAIN_WIRING_NOT_PROVEN")

    if record.get("runtime_proven") is not True:
        errors.append("RUNTIME_NOT_PROVEN")

    if record.get("vault_only") is True:
        errors.append("VAULT_ONLY")

    if record.get("local_model_weights_required") is True:
        errors.append("LOCAL_MODEL_WEIGHT_DEPENDENCY")

    dependencies = {
        str(x)
        for x in (record.get("runtime_dependencies") or [])
    }

    historical = dependencies.intersection(
        FORBIDDEN_RUNTIME_DEPENDENCIES
    )

    if historical:
        errors.append(
            "HISTORICAL_RUNTIME_DEPENDENCY:"
            + ",".join(sorted(historical))
        )

    return errors


def validate_pair(records: list[dict]) -> list[str]:
    errors: list[str] = []

    by_family = {
        str(r.get("family") or "").lower(): r
        for r in records
    }

    for family in sorted(REQUIRED_FAMILIES):
        if family not in by_family:
            errors.append(f"MISSING_FAMILY:{family}")
            continue

        for error in validate_assimilation_record(
            by_family[family]
        ):
            errors.append(f"{family}:{error}")

    return errors


def test_rejects_config_as_assimilation() -> None:
    record = {
        "family": "qwen",
        "capability_ids": ["x"],
        "source_provenance": "historical",
        "proof_kind": "config",
        "source_independent": True,
        "brain_wiring_proven": True,
        "runtime_proven": True,
    }

    assert "NON_ASSIMILATION_PROOF_KIND" in validate_assimilation_record(record)


def test_rejects_vault_only() -> None:
    record = {
        "family": "granite",
        "capability_ids": ["x"],
        "source_provenance": "historical",
        "proof_kind": "capability",
        "source_independent": True,
        "brain_wiring_proven": True,
        "runtime_proven": True,
        "vault_only": True,
    }

    assert "VAULT_ONLY" in validate_assimilation_record(record)


def test_rejects_old_runtime_dependency() -> None:
    record = {
        "family": "qwen",
        "capability_ids": ["x"],
        "source_provenance": "historical",
        "proof_kind": "capability",
        "source_independent": True,
        "brain_wiring_proven": True,
        "runtime_proven": True,
        "runtime_dependencies": [
            "_raios-a17-native-cortex"
        ],
    }

    errors = validate_assimilation_record(record)

    assert any(
        e.startswith("HISTORICAL_RUNTIME_DEPENDENCY:")
        for e in errors
    )


def test_requires_both_qwen_and_granite() -> None:
    errors = validate_pair(
        [
            {
                "family": "qwen",
                "capability_ids": ["q1"],
                "source_provenance": "source-q",
                "proof_kind": "capability",
                "source_independent": True,
                "brain_wiring_proven": True,
                "runtime_proven": True,
            }
        ]
    )

    assert "MISSING_FAMILY:granite" in errors


def test_accepts_real_dual_family_assimilation_contract() -> None:
    records = [
        {
            "family": "qwen",
            "capability_ids": ["q1"],
            "source_provenance": "source-q",
            "proof_kind": "capability",
            "source_independent": True,
            "brain_wiring_proven": True,
            "runtime_proven": True,
            "runtime_dependencies": [],
        },
        {
            "family": "granite",
            "capability_ids": ["g1"],
            "source_provenance": "source-g",
            "proof_kind": "capability",
            "source_independent": True,
            "brain_wiring_proven": True,
            "runtime_proven": True,
            "runtime_dependencies": [],
        },
    ]

    assert validate_pair(records) == []
