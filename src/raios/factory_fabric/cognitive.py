"""Governed cognitive capability over imported Factory Fabric estate.

This module never owns promotion, training, WAL, or event delivery.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROLE_BY_CATEGORY = {
    "benchmarks": ("BENCHMARK_CANDIDATE", "REVIEW_REQUIRED"),
    "skills": ("SKILL_VALIDATION_CANDIDATE", "REVIEW_REQUIRED"),
    "training-candidates": ("TRAINING_REVIEW_CANDIDATE", "REVIEW_REQUIRED"),
    "experiences": ("ASSIMILATION_FEEDBACK", "VALIDATION_REQUIRED"),
    "failures": ("ASSIMILATION_FEEDBACK", "VALIDATION_REQUIRED"),
    "semantic-atoms": ("KNOWLEDGE_MATERIAL", "VALIDATION_REQUIRED"),
    "semantic-corpus": ("KNOWLEDGE_MATERIAL", "VALIDATION_REQUIRED"),
    "semantic-taxonomy": ("KNOWLEDGE_MATERIAL", "VALIDATION_REQUIRED"),
    "routing-policies": ("GOVERNANCE_REFERENCE", "REFERENCE_ONLY"),
    "doctrine": ("GOVERNANCE_REFERENCE", "REFERENCE_ONLY"),
    "durability-policy": ("GOVERNANCE_REFERENCE", "REFERENCE_ONLY"),
    "durability-transactions": ("GOVERNANCE_REFERENCE", "REFERENCE_ONLY"),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _category(relative: str) -> str:
    parts = [part for part in relative.replace("\\", "/").split("/") if part]
    if parts and parts[0].lower() == "state":
        parts = parts[1:]
    return parts[0].lower() if parts else "unknown"


def _role(category: str) -> tuple[str, str]:
    if category in ROLE_BY_CATEGORY:
        return ROLE_BY_CATEGORY[category]
    if category in {"decisions", "evidence", "performance", "model-profiles"}:
        return "EVIDENCE_REFERENCE", "REFERENCE_ONLY"
    return "COGNITIVE_REFERENCE", "REFERENCE_ONLY"


def analyze_cognitive_estate(
    runtime_root: str | Path,
    *,
    write_runtime_artifacts: bool = False,
) -> dict[str, Any]:
    """Create deterministic governed queues from the imported cognitive donor."""
    root = Path(runtime_root).expanduser().resolve()
    manifest_path = root / "estate" / "manifests" / "FACTORY-ESTATE.json"
    if not manifest_path.is_file():
        return _empty_report("SOURCE_MANIFEST_MISSING")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    queue: list[dict[str, Any]] = []
    invalid: list[dict[str, str]] = []
    categories: Counter[str] = Counter()
    seen: set[tuple[str, str]] = set()
    duplicates_suppressed = 0

    for entry in manifest.get("entries", []):
        if entry.get("donor") != "historical-cognitive-factory":
            continue
        if entry.get("status") != "IMPORTED":
            continue
        relative = str(entry.get("source_relative") or "")
        expected = str(entry.get("source_sha256") or "")
        obj = Path(str(entry.get("object_path") or ""))
        if not obj.is_file() or not expected or _sha256(obj) != expected:
            invalid.append({"source_relative": relative, "reason": "OBJECT_INTEGRITY_FAILED"})
            continue
        category = _category(relative)
        capability, disposition = _role(category)
        identity = (expected, capability)
        if identity in seen:
            duplicates_suppressed += 1
            continue
        seen.add(identity)
        item_id = hashlib.sha256(
            f"{expected}|{category}|{capability}".encode("utf-8")
        ).hexdigest()
        categories[category] += 1
        queue.append({
            "cognitive_item_id": f"COG:{item_id[:24]}",
            "source_sha256": expected,
            "source_relative": relative,
            "category": category,
            "capability": capability,
            "disposition": disposition,
            "promotion_authority": False,
        })

    queue.sort(key=lambda item: (item["capability"], item["source_sha256"]))
    report = {
        "schema": "raios.factory-fabric.cognitive-capability.v1",
        "status": "FAIL_INTEGRITY" if invalid else ("PASS" if queue else "PASS_EMPTY"),
        "imported_cognitive_items": len(queue),
        "invalid_items": invalid,
        "duplicates_suppressed": duplicates_suppressed,
        "categories": dict(sorted(categories.items())),
        "review_queue": queue,

        "active_cognitive_factory": True,
        "runtime_role": "CANONICAL_COGNITIVE_CAPABILITY",
        "automatic_training": False,
        "automatic_canonical_promotion": False,
        "canonical_promotion_authority": False,
        "second_wal_created": False,
        "second_event_bus_created": False,
        "source_mutation": False,
    }
    if write_runtime_artifacts:
        out = root / "cognitive"
        out.mkdir(parents=True, exist_ok=True)
        (out / "COGNITIVE-REVIEW-QUEUE.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    return report


def _empty_report(reason: str) -> dict[str, Any]:
    return {
        "schema": "raios.factory-fabric.cognitive-capability.v1",
        "status": "PASS_EMPTY",
        "reason": reason,
        "imported_cognitive_items": 0,
        "invalid_items": [],
        "categories": {},
        "review_queue": [],
        "active_cognitive_factory": True,
        "runtime_role": "CANONICAL_COGNITIVE_CAPABILITY",
        "automatic_training": False,
        "automatic_canonical_promotion": False,
        "canonical_promotion_authority": False,
        "second_wal_created": False,
        "second_event_bus_created": False,
        "source_mutation": False,
    }
