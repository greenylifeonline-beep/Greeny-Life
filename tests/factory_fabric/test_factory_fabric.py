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
from raios.factory_fabric.state_import import DonorRoot, import_factory_estate, load_imported_jsonl_events


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


def test_estate_import_replaces_superseded_append_only_snapshot(tmp_path):
    donor = tmp_path / "donor"
    donor.mkdir()
    source = donor / "training-events.jsonl"
    source.write_text(json.dumps({"training_turn_id": "T1"}) + "\n", encoding="utf-8")
    (donor / "zzz-after-training.txt").write_text("unrelated", encoding="utf-8")
    runtime = tmp_path / "runtime"
    first = import_factory_estate(runtime, [DonorRoot("c5-live-runtime", donor)])
    first_entry = next(x for x in first["entries"] if x.get("source_relative") == "training-events.jsonl")
    first_object = Path(first_entry["object_path"])

    with source.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"training_turn_id": "T2"}) + "\n")

    second = import_factory_estate(runtime, [DonorRoot("c5-live-runtime", donor)])
    current = [x for x in second["entries"] if x.get("source_relative") == "training-events.jsonl"]
    assert len(current) == 1
    assert current[0]["source_sha256"] != first_entry["source_sha256"]
    assert Path(current[0]["object_path"]).is_file()
    assert not first_object.exists()
    rows = load_imported_jsonl_events(runtime)
    assert [row["event"]["training_turn_id"] for row in rows] == ["T1", "T2"]


def test_estate_import_can_select_reference_files(tmp_path):
    donor = tmp_path / "donor"
    donor.mkdir()
    (donor / "keep.md").write_text("valuable reference", encoding="utf-8")
    (donor / "skip.bin").write_bytes(b"generated payload")

    result = import_factory_estate(
        tmp_path / "runtime",
        [DonorRoot("REFERENCE", donor, frozenset({"keep.md"}))],
    )

    imported = [x for x in result["entries"] if x.get("status") == "IMPORTED"]
    assert result["source_file_count"] == 1
    assert imported[0]["source_relative"] == "keep.md"


def test_imported_estate_survives_source_retirement(tmp_path):
    donor = tmp_path / "donor"
    donor.mkdir()
    source = donor / "events.jsonl"
    source.write_text(
        json.dumps({"task_id": "T1", "capability": "continuity", "state": "VALIDATED"}) + "\n",
        encoding="utf-8",
    )
    runtime = tmp_path / "runtime"
    first = import_factory_estate(runtime, [DonorRoot("TEST", donor)])
    source.unlink()
    donor.rmdir()

    second = import_factory_estate(runtime, [])
    report = build_curriculum(runtime)

    assert first["objects_copied"] == 1
    assert second["retained_entries"] == 1
    assert second["source_file_count"] == 1
    assert report["raw_events"] == 1
    assert "Greeny-Life-Repair" not in (
        ROOT / "src" / "raios" / "factory_fabric" / "state_import.py"
    ).read_text(encoding="utf-8")


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
    assert heavy["source_removable"] is False
    assert heavy["benchmark_required"] is True
    assert heavy["canonical_role"] == "REMOTE_MIGRATION_CANDIDATE"


def test_model_ecology_parses_ollama_sizes_before_classification():
    from raios.factory_fabric.model_ecology import parse_size_text

    assert parse_size_text("23 GB") == 23 * 1024**3
    assert parse_size_text("639 MB") == 639 * 1024**2
    assert parse_size_text("unknown") == 0


def test_main_cortex_is_never_selected_as_student(monkeypatch):
    from raios.factory_fabric import model_ecology

    monkeypatch.setenv("RAIOS_STUDENT_MODEL", "qwen3.6:35b-a3b")

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"status":"ONLINE","live_engines":["qwen3:0.6b"]}'

    monkeypatch.setattr(model_ecology.urllib.request, "urlopen", lambda *a, **k: _Resp())
    assert model_ecology.runtime_model() == "qwen3:0.6b"
    rows = model_ecology.classify_records(
        [{"name": "qwen3.6:35b-a3b", "size_bytes": 23 * 1024**3}],
        runtime_model="qwen3:0.6b",
    )
    assert rows[0]["canonical_role"] == "MAIN_CORTEX_C1_OWNED"
    assert rows[0]["currently_bound"] is False


def test_runtime_model_reads_live_engines(monkeypatch):
    from raios.factory_fabric import model_ecology

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"status":"ONLINE","live_engines":["qwen3:0.6b"],"model_fabric_ready":true}'

    monkeypatch.delenv("RAIOS_C5_MODEL", raising=False)
    monkeypatch.delenv("RAIOS_STUDENT_MODEL", raising=False)
    monkeypatch.setattr(model_ecology.urllib.request, "urlopen", lambda *a, **k: _Resp())
    assert model_ecology.runtime_model() == "qwen3:0.6b"


def test_orchestrator_model_ecology_module_is_present():
    from raios.factory_fabric import model_ecology

    assert callable(model_ecology.classify_local_models)


def test_official_source_extraction_and_units_are_evidence_gated():
    from raios.factory_fabric.official_source import clean_lines, make_units

    html = "<html><script>import forbidden</script><body><p>Official import customs evidence must be verified before operational use.</p></body></html>"
    lines = clean_lines(html)
    assert lines == ["Official import customs evidence must be verified before operational use."]
    units = make_units([{
        "source_id": "TEST-OFFICIAL",
        "jurisdiction": "TEST",
        "authority": "TEST AUTHORITY",
        "domain": "customs",
        "requested_url": "https://example.invalid/official",
        "raw_sha256": "0" * 64,
        "retrieved_at": "2026-08-29T00:00:00Z",
        "semantic_lines": lines,
    }])
    assert len(units) == 1
    assert units[0]["state"] == "DISCOVERED"
    assert units[0]["verification_status"] == "UNVERIFIED_CURRENTNESS"
    assert units[0]["execution_authority"] is False


def test_trade_corridor_primitives_are_deterministic_and_conservative():
    from raios.factory_fabric.trade_corridor import calculate_transport, evidence_risk_score, scenario_documents

    assert calculate_transport("SEA_LCL", 500.0, 2.0, 1.0) == 230.0
    assert scenario_documents({}, "MISSING_DOCUMENT")["ORIGIN_EVIDENCE"] is False
    assert evidence_risk_score([]) == 1.0
    assert evidence_risk_score([{"currentness_analysis": {"triage": "CURRENTNESS_UNKNOWN"}}]) == 1.0


def test_package_import_is_lazy_and_public_api_is_compatible():
    code = (
        "import sys; import raios.factory_fabric as f; "
        "assert 'raios.factory_fabric.orchestrator' not in sys.modules; "
        "assert callable(f.run_all); assert callable(f.import_factory_estate)"
    )
    env = os.environ.copy()
    source_root = str(ROOT / "src")
    env["PYTHONPATH"] = os.pathsep.join(
        part for part in (source_root, env.get("PYTHONPATH")) if part
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
    )
    assert proc.returncode == 0, proc.stderr


def test_resource_factory_probe_defaults_to_non_live_overlay():
    from raios.factory_fabric.orchestrator import resource_factory_probe

    report = resource_factory_probe()
    assert report["status"] == "PASS"
    assert report["live_probe"] is False
    assert report["control"]["provider_mutation"] is False
    assert report["model_factory"]["gpu_session_started"] is False
    assert report["model_factory"]["paid_resource_created"] is False


def test_estate_import_compacts_historical_append_only_debt_when_latest_known(tmp_path):
    donor = tmp_path / "donor"
    donor.mkdir()
    source = donor / "training-events.jsonl"
    runtime = tmp_path / "runtime"
    source.write_text('{"training_turn_id":"T1"}\n', encoding="utf-8")
    historical_bytes = source.read_bytes()
    import_factory_estate(runtime, [DonorRoot("c5-live-runtime", donor)])
    source.write_text('{"training_turn_id":"T1"}\n{"training_turn_id":"T2"}\n', encoding="utf-8")
    second = import_factory_estate(runtime, [DonorRoot("c5-live-runtime", donor)])
    latest_hash = next(x["source_sha256"] for x in second["entries"] if x.get("source_relative") == "training-events.jsonl")
    # Reintroduce historical debt while the latest object remains known.
    manifest = runtime / "estate" / "manifests" / "FACTORY-ESTATE.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    old_objects = list((runtime / "estate" / "objects").glob("*.jsonl"))
    assert len(old_objects) == 1  # normal path already compacted
    import hashlib
    old_bytes = historical_bytes
    old_hash = hashlib.sha256(old_bytes).hexdigest()
    old_copy = runtime / "estate" / "objects" / (old_hash + ".jsonl")
    old_copy.write_bytes(old_bytes)
    data["entries"].append({"donor":"c5-live-runtime","source_root":str(donor),"source_relative":"training-events.jsonl","source_sha256":old_hash,"size_bytes":old_copy.stat().st_size,"object_path":str(old_copy),"status":"IMPORTED"})
    manifest.write_text(json.dumps(data), encoding="utf-8")
    third = import_factory_estate(runtime, [DonorRoot("c5-live-runtime", donor)])
    current = [x for x in third["entries"] if x.get("source_relative") == "training-events.jsonl"]
    assert [x["source_sha256"] for x in current] == [latest_hash]
    assert not old_copy.exists()


def test_compaction_defers_locked_object_delete_without_failing_import(tmp_path, monkeypatch):
    donor = tmp_path / "donor"
    donor.mkdir()
    source = donor / "training-events.jsonl"
    runtime = tmp_path / "runtime"
    source.write_text('{"training_turn_id":"T1"}\n', encoding="utf-8")
    first = import_factory_estate(runtime, [DonorRoot("c5-live-runtime", donor)])
    old = Path(first["entries"][0]["object_path"])
    source.write_text('{"training_turn_id":"T1"}\n{"training_turn_id":"T2"}\n', encoding="utf-8")
    real_unlink = Path.unlink
    def locked_unlink(path, *args, **kwargs):
        if path == old:
            raise PermissionError(32, "sharing violation", str(path))
        return real_unlink(path, *args, **kwargs)
    monkeypatch.setattr(Path, "unlink", locked_unlink)
    result = import_factory_estate(runtime, [DonorRoot("c5-live-runtime", donor)])
    assert result["pending_delete_count"] == 1
    assert str(old) in result["pending_delete"]
    assert old.exists()
    current = [x for x in result["entries"] if x.get("source_relative") == "training-events.jsonl"]
    assert len(current) == 1
