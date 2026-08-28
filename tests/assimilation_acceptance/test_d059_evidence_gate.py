from __future__ import annotations

import json
from pathlib import Path

from .d059_evidence_gate import (
    load_evidence,
    validate_evidence_file,
)


def _valid_record(family: str) -> dict:
    return {
        "family": family,
        "capability_ids": [
            f"{family}.capability.1",
        ],
        "source_provenance": f"{family}-source",
        "proof_kind": "capability",
        "source_independent": True,
        "brain_wiring_proven": True,
        "runtime_proven": True,
        "vault_only": False,
        "local_model_weights_required": False,
        "runtime_dependencies": [],
    }


def test_load_records_schema(tmp_path: Path) -> None:
    path = tmp_path / "evidence.json"

    path.write_text(
        json.dumps(
            {
                "records": [
                    _valid_record("qwen"),
                    _valid_record("granite"),
                ]
            }
        ),
        encoding="utf-8",
    )

    records = load_evidence(path)

    assert len(records) == 2


def test_load_family_key_schema(tmp_path: Path) -> None:
    path = tmp_path / "evidence.json"

    path.write_text(
        json.dumps(
            {
                "qwen": _valid_record("qwen"),
                "granite": _valid_record("granite"),
            }
        ),
        encoding="utf-8",
    )

    records = load_evidence(path)

    assert {
        r["family"]
        for r in records
    } == {
        "qwen",
        "granite",
    }


def test_valid_dual_family_evidence_passes(
    tmp_path: Path,
) -> None:
    path = tmp_path / "evidence.json"

    path.write_text(
        json.dumps(
            {
                "records": [
                    _valid_record("qwen"),
                    _valid_record("granite"),
                ]
            }
        ),
        encoding="utf-8",
    )

    result = validate_evidence_file(path)

    assert result["accepted"] is True
    assert result["errors"] == []


def test_missing_granite_fails(
    tmp_path: Path,
) -> None:
    path = tmp_path / "evidence.json"

    path.write_text(
        json.dumps(
            {
                "records": [
                    _valid_record("qwen"),
                ]
            }
        ),
        encoding="utf-8",
    )

    result = validate_evidence_file(path)

    assert result["accepted"] is False
    assert "MISSING_FAMILY:granite" in result["errors"]


def test_runtime_dependency_on_old_tree_fails(
    tmp_path: Path,
) -> None:
    record = _valid_record("qwen")

    record["runtime_dependencies"] = [
        "_raios-a17-native-cortex",
    ]

    path = tmp_path / "evidence.json"

    path.write_text(
        json.dumps(
            {
                "records": [
                    record,
                    _valid_record("granite"),
                ]
            }
        ),
        encoding="utf-8",
    )

    result = validate_evidence_file(path)

    assert result["accepted"] is False

    assert any(
        "HISTORICAL_RUNTIME_DEPENDENCY:"
        in error
        for error in result["errors"]
    )

