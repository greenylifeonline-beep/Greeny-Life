from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from brain import inspect_canonical_runtime_health
from raios.neuro_lingua.schema import KnowledgeState
from raios.neuro_lingua.wal import ExistingCognitiveWALWriter

ROOT = Path(__file__).resolve().parents[1]


def test_c5_health_composes_canonical_runtime_without_wal_write() -> None:
    wal = ExistingCognitiveWALWriter()
    assert wal.wal_path
    before = Path(wal.wal_path).stat().st_size
    result = inspect_canonical_runtime_health(str(ROOT))
    after = Path(wal.wal_path).stat().st_size
    assert result["status"] == "PASS"
    assert result["capabilities_checked"] == 7
    assert result["knowledge_state"] == "DISCOVERED"
    assert result["wal_unchanged"] is True
    assert before == after


def test_c5_health_detects_no_broken_binding() -> None:
    result = inspect_canonical_runtime_health(str(ROOT))
    assert set(result["module_health"].values()) == {"REACHABLE"}
    assert all(result["component_health"].values())
    assert result["repair_action"] == "NONE_REQUIRED"


def test_c5_health_detects_missing_canonical_paths_without_repair(tmp_path: Path) -> None:
    result = inspect_canonical_runtime_health(str(tmp_path))
    assert result["status"] == "DEGRADED"
    assert result["repair_action"] == "GOVERNED_REPAIR_REQUIRED"
    assert result["high_risk_self_promotion"] is False


def test_direct_canonical_learning_promotion_is_denied() -> None:
    writer = ExistingCognitiveWALWriter()
    with pytest.raises(ValueError, match="DIRECT_CANONICAL_PROMOTION_FORBIDDEN"):
        writer.append_learning(
            "unsafe-promotion",
            {"confidence": 1.0},
            knowledge_state=KnowledgeState.CANONICAL,
        )


def test_c5_canonical_health_cli() -> None:
    completed = subprocess.run(
        [sys.executable, "brain.py", "--repo", str(ROOT), "--canonical-health"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert '"status": "PASS"' in completed.stdout
