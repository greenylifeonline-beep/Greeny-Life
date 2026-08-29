from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from safetensors.numpy import load_file, save_file

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "RAIOS" / "V9"))

from evolution.model_lab.merge_executor import execute
from evolution.model_lab.merge_strategy import declarations


def _model(path: Path, values: list[float]) -> Path:
    path.mkdir()
    save_file({"weight": np.asarray(values, dtype=np.float32)}, str(path / "model.safetensors"))
    return path


def test_existing_default_refusal_is_preserved():
    result = execute({"id": "blocked", "strategy": "TIES"})
    assert result["executed"] is False
    assert result["weights_touched"] is False
    assert result["reason"] == "MERGE_FORBIDDEN_HERE"


def test_linear_dry_run_hashes_inputs_without_writing_output(tmp_path):
    first = _model(tmp_path / "first", [1.0, 3.0])
    second = _model(tmp_path / "second", [3.0, 5.0])
    output = tmp_path / "output"
    result = execute({
        "id": "dry",
        "strategy": "LINEAR",
        "inputs": [{"path": str(first), "weight": 1}, {"path": str(second), "weight": 1}],
        "output_path": str(output),
        "dry_run": True,
    })
    assert result["ok"] is True
    assert result["executed"] is False
    assert result["weights_touched"] is False
    assert len(result["receipt"]["inputs"]) == 2
    assert not output.exists()
def test_linear_execution_requires_explicit_authority(tmp_path):
    first = _model(tmp_path / "first", [1.0])
    second = _model(tmp_path / "second", [3.0])
    result = execute({
        "strategy": "LINEAR",
        "inputs": [{"path": str(first), "weight": 1}, {"path": str(second), "weight": 1}],
        "output_path": str(tmp_path / "output"),
        "dry_run": False,
    })
    assert result["executed"] is False
    assert result["reason"] == "NO_BLIND_WEIGHT_MERGE"


def test_explicit_cpu_linear_merge_is_receipted_and_local(tmp_path):
    first = _model(tmp_path / "first", [1.0, 3.0])
    second = _model(tmp_path / "second", [3.0, 5.0])
    output = tmp_path / "output"
    result = execute({
        "id": "approved-test",
        "strategy": "LINEAR",
        "inputs": [{"path": str(first), "weight": 1}, {"path": str(second), "weight": 3}],
        "output_path": str(output),
        "dry_run": False,
        "allow_execute": True,
    })
    assert result["ok"] is True
    assert result["executed"] is True
    merged = load_file(str(output / "model.safetensors"))["weight"]
    np.testing.assert_allclose(merged, np.asarray([2.5, 4.5], dtype=np.float32))
    receipt = json.loads((output / "RAIOS-WEIGHT-MERGE-RECEIPT.json").read_text())
    assert receipt["backend"] == "CPU_LINEAR"
    assert receipt["gpu_session_started"] is False
    assert receipt["paid_resource_created"] is False
    assert receipt["model_downloaded"] is False
    assert receipt["automatic_canonical_promotion"] is False


def test_backend_discovery_never_installs_or_downloads():
    state = declarations()
    assert state["cpu_linear_available"] is True
    assert state["installed_blindly"] is False
    assert state["mergekit"]["installed_by_raios"] is False
    assert state["mergekit"]["network_acquisition"] is False


def test_canonical_cli_exposes_capabilities_without_side_effects():
    proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "ai-os" / "raios_weight_merge.py"), "capabilities"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=30,
    )
    assert proc.returncode == 0, proc.stderr
    payload = json.loads(proc.stdout)
    assert payload["cpu_linear_available"] is True
    assert payload["automatic_canonical_promotion"] is False
