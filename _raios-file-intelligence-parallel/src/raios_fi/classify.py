"""Multi-dimensional classification. Rules first. Dimensions never collapse."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .authority import classify_authority
from .confidence import build_confidence, verification_from_confidence
from .liveness import classify_liveness
from .types import CLASS_GENERATED, FileTypeResult, classify_file


@dataclass(frozen=True)
class Classification:
    physical_type: str
    logical_type: str
    domain: str
    subsystem: str
    role: str
    authority_class: str
    temporal_scope: str
    verification_state: str
    knowledge_state: str
    lifecycle: str
    version_role: str
    criticality: str
    change_risk: str
    active_state: str
    generated_state: str
    provenance: str
    confidence: float
    evidence_confidence: dict[str, Any]
    rule_ids: tuple[str, ...]
    model_used: bool
    # compat aliases used by older tests
    generated_or_manual: str = "manual"
    activity: str = "unknown"
    version_relevance: str = "unknown"
    duplicate_probability: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_path(path: Path, typed: FileTypeResult | None = None) -> Classification:
    typed = typed or classify_file(path)
    rel = str(path).replace("\\", "/").lower()
    rules: list[str] = []
    domain = "unknown"
    subsystem = "unknown"
    role = "unknown"
    criticality = "low"
    change_risk = "low"
    generated = "generated" if typed.file_class == CLASS_GENERATED else "manual"
    lifecycle = "docs"
    version_role = "unknown"

    supporting = [typed.detector]
    contradicting: list[str] = []
    deterministic = []
    if typed.detector.startswith("signature") or typed.detector.startswith("parser-probe"):
        deterministic.append(typed.detector)
    if typed.detector == "probe+ext-hint":
        supporting.append("extension_hint_not_authority")
        rules.append("extension_never_sole")

    ext = path.suffix.lower()
    if ext == ".json" and typed.language == "python":
        contradicting.append("ext=json vs parser=python")
        rules.append("misleading_extension")
    if ext == ".txt" and typed.physical_type == "ZIP":
        contradicting.append("ext=txt vs signature=zip")
        rules.append("misleading_extension")

    if typed.file_class == CLASS_GENERATED:
        rules.append("generated_class")
        generated = "generated"
        change_risk = "low"
    if "/tests/" in rel or rel.endswith((".test.ts", ".spec.ts", "_test.py")):
        lifecycle = "test"
        role = "test"
        subsystem = "tests"
        rules.append("test_path")
    elif rel.endswith((".md", ".txt")) and typed.file_class != CLASS_GENERATED:
        lifecycle = "docs"
        role = "document"
        rules.append("docs_ext")
    elif typed.file_class == "CODE":
        lifecycle = "runtime"
        role = "source"
        change_risk = "high"
        criticality = "high"
        rules.append("code_class")
    elif typed.file_class == "CONFIG":
        lifecycle = "build"
        role = "config"
        change_risk = "high"
        criticality = "high"
        rules.append("config_class")
    elif typed.file_class == "DATABASE":
        lifecycle = "runtime"
        role = "schema"
        criticality = "high"
        rules.append("db_class")
    elif typed.logical_type == "OOXML_DOCUMENT":
        role = "report" if "report" in rel else "document"
        rules.append("ooxml_logical")

    if "greeny" in rel or "/app/" in rel:
        domain = "greeny_life"
        rules.append("greeny_path")
    if "raios" in rel:
        domain = "raios"
        rules.append("raios_path")
    if "/archive/" in rel:
        version_role = "reference"
        rules.append("archive_path")
    if "/node_modules/" in rel:
        generated = "generated"
        rules.append("vendor")

    live = classify_liveness(path)
    authority = classify_authority(path, deterministic_ok=bool(deterministic), contradicted=bool(contradicting))
    conf = build_confidence(
        supporting=supporting,
        contradicting=contradicting,
        deterministic=deterministic,
        base=typed.confidence * 0.5,
    )
    verification = verification_from_confidence(conf, contradicted=bool(contradicting))
    # Authority verification is independent of type verification; do not overwrite authority fields.
    if typed.file_class == "UNKNOWN":
        rules.append("unknown_unclaimed")
        conf = build_confidence(
            supporting=supporting,
            contradicting=contradicting + ["unclaimed_type"],
            deterministic=deterministic,
            base=min(typed.confidence, 0.2),
        )

    return Classification(
        physical_type=typed.physical_type,
        logical_type=typed.logical_type,
        domain=domain,
        subsystem=subsystem,
        role=role,
        authority_class=authority.authority_class,
        temporal_scope=authority.temporal_scope,
        verification_state=verification,
        knowledge_state=authority.knowledge_state,
        lifecycle=lifecycle,
        version_role=version_role,
        criticality=criticality,
        change_risk=change_risk,
        active_state=live.active_state,
        generated_state=generated,
        provenance="path+signature+parser-probe" if deterministic else "path+hint",
        confidence=conf.score,
        evidence_confidence=conf.to_dict(),
        rule_ids=tuple(rules),
        model_used=False,
        generated_or_manual=generated,
        activity=live.active_state,
        version_relevance=version_role,
        duplicate_probability=0.0,
    )
