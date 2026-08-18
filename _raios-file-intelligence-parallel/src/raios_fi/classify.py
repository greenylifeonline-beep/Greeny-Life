"""Smart classification: rules first, model second (model never required)."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from raios_fi.types import CLASS_GENERATED, FileTypeResult, classify_file


@dataclass(frozen=True)
class Classification:
    domain: str
    subsystem: str
    role: str
    criticality: str
    change_risk: str
    generated_or_manual: str
    lifecycle: str
    activity: str
    version_relevance: str
    duplicate_probability: float
    confidence: float
    rule_ids: tuple[str, ...]
    model_used: bool

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
    activity = "unknown"
    version_relevance = "unknown"
    dup = 0.0
    conf = typed.confidence

    if typed.file_class == CLASS_GENERATED:
        rules.append("generated_class")
        generated = "generated"
        activity = "generated"
        change_risk = "low"
    if "/tests/" in rel or rel.endswith((".test.ts", ".spec.ts", "_test.py")):
        lifecycle = "test"
        role = "test"
        rules.append("test_path")
        conf = max(conf, 0.8)
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
        conf = max(conf, 0.7)
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

    if "greeny" in rel or "/app/" in rel:
        domain = "greeny_life"
        rules.append("greeny_path")
    if "raios" in rel:
        domain = "raios"
        rules.append("raios_path")
    if "/archive/" in rel:
        activity = "superseded_candidate"
        version_relevance = "reference"
        rules.append("archive_path")
    if "/node_modules/" in rel:
        activity = "dead"
        generated = "generated"
        rules.append("vendor")
    if typed.file_class == "UNKNOWN":
        domain = domain if domain != "unknown" else "unknown"
        role = "unknown"
        activity = "unknown"
        conf = min(conf, 0.4)
        rules.append("unknown_unclaimed")

    return Classification(
        domain=domain,
        subsystem=subsystem,
        role=role,
        criticality=criticality,
        change_risk=change_risk,
        generated_or_manual=generated,
        lifecycle=lifecycle,
        activity=activity,
        version_relevance=version_relevance,
        duplicate_probability=dup,
        confidence=round(conf, 3),
        rule_ids=tuple(rules),
        model_used=False,
    )
