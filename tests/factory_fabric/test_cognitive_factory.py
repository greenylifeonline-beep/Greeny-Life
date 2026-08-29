from __future__ import annotations

import hashlib
import json
from pathlib import Path

from raios.factory_fabric.cognitive import analyze_cognitive_estate


def _object(root: Path, name: str, payload: bytes) -> tuple[Path, str]:
    digest = hashlib.sha256(payload).hexdigest()
    path = root / "estate" / "objects" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path, digest


def _manifest(root: Path, entries: list[dict]) -> None:
    path = root / "estate" / "manifests" / "FACTORY-ESTATE.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"entries": entries}), encoding="utf-8")


def _entry(path: Path, digest: str, relative: str) -> dict:
    return {
        "donor": "historical-cognitive-factory",
        "status": "IMPORTED",
        "source_relative": relative,
        "source_sha256": digest,
        "object_path": str(path),
    }


def test_missing_estate_is_safe_active_empty(tmp_path):
    result = analyze_cognitive_estate(tmp_path)
    assert result["status"] == "PASS_EMPTY"
    assert result["active_cognitive_factory"] is True
    assert result["canonical_promotion_authority"] is False


def test_cognitive_material_is_classified_and_deduplicated(tmp_path):
    bench, bench_hash = _object(tmp_path, "bench.json", b'{"score": 1}')
    skill, skill_hash = _object(tmp_path, "skill.json", b'{"skill": "repair"}')
    route, route_hash = _object(tmp_path, "route.json", b'{"route": "safe"}')
    _manifest(tmp_path, [
        _entry(bench, bench_hash, "benchmarks/a.json"),
        _entry(bench, bench_hash, "benchmarks/copy.json"),
        _entry(skill, skill_hash, "skills/b.json"),
        _entry(route, route_hash, "routing-policies/ACTIVE.json"),
    ])

    first = analyze_cognitive_estate(tmp_path)
    second = analyze_cognitive_estate(tmp_path)
    assert first == second
    assert first["status"] == "PASS"
    assert first["imported_cognitive_items"] == 3
    assert first["duplicates_suppressed"] == 1

    by_capability = {item["capability"]: item for item in first["review_queue"]}
    assert by_capability["BENCHMARK_CANDIDATE"]["disposition"] == "REVIEW_REQUIRED"
    assert by_capability["SKILL_VALIDATION_CANDIDATE"]["disposition"] == "REVIEW_REQUIRED"
    assert by_capability["GOVERNANCE_REFERENCE"]["disposition"] == "REFERENCE_ONLY"
    assert all(item["promotion_authority"] is False for item in first["review_queue"])
    assert first["automatic_training"] is False
    assert first["automatic_canonical_promotion"] is False
    assert first["second_wal_created"] is False
    assert first["second_event_bus_created"] is False


def test_object_integrity_is_fail_closed(tmp_path):
    obj, digest = _object(tmp_path, "bad.json", b"original")
    _manifest(tmp_path, [_entry(obj, digest, "experiences/x.json")])
    obj.write_bytes(b"tampered")

    result = analyze_cognitive_estate(tmp_path)
    assert result["status"] == "FAIL_INTEGRITY"
    assert result["imported_cognitive_items"] == 0
    assert result["invalid_items"][0]["reason"] == "OBJECT_INTEGRITY_FAILED"


def test_runtime_artifact_write_is_explicit(tmp_path):
    obj, digest = _object(tmp_path, "failure.json", b'{"status": "FAILED"}')
    _manifest(tmp_path, [_entry(obj, digest, "failures/x.json")])

    analyze_cognitive_estate(tmp_path, write_runtime_artifacts=False)
    target = tmp_path / "cognitive" / "COGNITIVE-REVIEW-QUEUE.json"
    assert not target.exists()

    analyze_cognitive_estate(tmp_path, write_runtime_artifacts=True)
    assert target.is_file()
