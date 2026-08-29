from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("NO_LLM_CALLS", "true")
os.environ.setdefault("RAIOS_RESOURCE_LIVE", "0")

from raios.factory_fabric.assimilation import build_curriculum
from raios.factory_fabric.state_import import DonorRoot, import_factory_estate


def test_estate_import_is_content_addressed_and_source_read_only(tmp_path):
    donor = tmp_path / "donor"
    donor.mkdir()
    a = donor / "events.jsonl"
    b = donor / "copy.jsonl"
    content = '{"task_id":"T1","failure_class":"repair","status":"FAILED"}\n'
    a.write_text(content, encoding="utf-8")
    b.write_text(content, encoding="utf-8")
    before = {p.name: p.read_bytes() for p in donor.iterdir()}

    runtime = tmp_path / "runtime"
    result = import_factory_estate(runtime, [DonorRoot("TEST", donor)])

    assert result["source_file_count"] == 2
    assert result["unique_object_count"] == 1
    assert result["objects_copied"] == 1
    assert result["objects_reused"] == 1
    assert result["source_mutation"] is False
    assert before == {p.name: p.read_bytes() for p in donor.iterdir()}


def test_assimilation_consumes_imported_event_stream(tmp_path):
    donor = tmp_path / "donor"
    donor.mkdir()
    (donor / "events.jsonl").write_text(
        "\n".join([
            json.dumps({"task_id": "T1", "failure_class": "repair", "status": "FAILED"}),
            json.dumps({"task_id": "T2", "capability": "learning", "state": "DISCOVERED"}),
        ]) + "\n",
        encoding="utf-8",
    )
    runtime = tmp_path / "runtime"
    import_factory_estate(runtime, [DonorRoot("TEST", donor)])
    report = build_curriculum(runtime)
    assert report["status"] == "PASS"
    assert report["raw_events"] == 2
    assert report["unique_materials"] == 2
    assert report["assimilation_units"] >= 1
    assert report["source_dependency"] == "EXTERNALIZED_FACTORY_ESTATE"


def test_foundry_is_externalized_and_donor_independent():
    text = (ROOT / "src" / "raios" / "factory_fabric" / "foundry_engine.py").read_text(encoding="utf-8")
    assert "RAIOS_FOUNDRY_RUNTIME_ROOT" in text
    assert "foundry_config" in text
    assert "CANONICAL_RUNTIME_EXTERNALIZED" in text
    assert "DONOR_SOURCE_RUNTIME_REQUIRED" in text
    assert "_raios-learning-observatory" not in text


def test_training_factory_native_node_runner():
    proc = subprocess.run(
        ["node", str(ROOT / "scripts" / "runtime" / "verify-training-factory.mjs")],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=60,
    )
    assert proc.returncode == 0, proc.stderr
    assert '"status":"PASS"' in proc.stdout
    assert '"external_dependency":false' in proc.stdout


def test_foundry_small_run_uses_external_runtime(tmp_path):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "src")
    env["RAIOS_FOUNDRY_REPO_ROOT"] = str(ROOT)
    env["RAIOS_FOUNDRY_RUNTIME_ROOT"] = str(tmp_path / "foundry")
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "raios.factory_fabric.foundry_engine",
            "run",
            "--max-files",
            "40",
            "--case-limit",
            "40",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        timeout=180,
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout[-2000:]
    report = json.loads(proc.stdout)
    assert report["train"]["execution_authorizations"] == 0
    assert report["blind"]["execution_authorizations"] == 0
    assert report["promotion"]["automatic_canonical_promotion"] is False
    assert report["receipt"].startswith("runtime:")


def test_model_ecology_preserves_active_runtime_model():
    from raios.factory_fabric.model_ecology import classify_records

    rows = classify_records(
        [
            {"name": "qwen3:0.6b", "size_bytes": 522653767},
            {"name": "large:35b", "size_bytes": 12 * 1024**3},
        ],
        runtime_model="qwen3:0.6b",
    )
    active, heavy = rows
    assert active["runtime_required"] is True
    assert active["source_removable"] is False
    assert active["canonical_role"] == "ACTIVE_RUNTIME_MODEL"
    assert heavy["heavy_local"] is True
    assert heavy["remote_migration_required"] is True
    assert heavy["source_removable"] is True


def test_orchestrator_model_ecology_module_is_present():
    from raios.factory_fabric import model_ecology

    assert callable(model_ecology.classify_local_models)
