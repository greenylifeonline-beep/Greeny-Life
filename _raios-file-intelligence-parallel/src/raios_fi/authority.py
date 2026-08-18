"""Independent information-authority dimensions. Never collapse into file_class."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

AUTHORITY_CLASSES = (
    "LIVE_OPERATIONAL_STATE",
    "CERTIFIED_STATE",
    "ARCHITECTURAL_DECISION",
    "EXECUTION_EVIDENCE",
    "HISTORICAL_EVIDENCE",
    "LEARNING_STATE",
    "PROPOSAL",
    "GENERATED_OUTPUT",
    "EXTERNAL_REFERENCE",
    "UNKNOWN",
)

TEMPORAL_SCOPES = ("CURRENT", "HISTORICAL", "TIMELESS", "UNKNOWN")
VERIFICATION_STATES = ("VERIFIED", "PARTIALLY_VERIFIED", "UNVERIFIED", "CONTRADICTED", "STALE")
KNOWLEDGE_STATES = ("DISCOVERED", "VALIDATED", "CANONICAL", "SUPERSEDED", "DEPRECATED", "QUARANTINED")


@dataclass(frozen=True)
class AuthorityRecord:
    authority_class: str
    temporal_scope: str
    verification_state: str
    knowledge_state: str
    evidence: tuple[str, ...]
    model_used: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_authority(path: Path, *, deterministic_ok: bool = False, contradicted: bool = False) -> AuthorityRecord:
    rel = str(path).replace("\\", "/").lower()
    parts = set(Path(rel).parts)
    evidence: list[str] = []
    authority = "UNKNOWN"
    temporal = "UNKNOWN"

    if "node_modules" in parts or "/.git/" in rel:
        authority, temporal = "EXTERNAL_REFERENCE", "CURRENT"
        evidence.append("vendor_or_git")
    elif "teacher-harvest" in rel or "/experience/raw/" in rel:
        authority, temporal = "LEARNING_STATE", "CURRENT"
        evidence.append("teacher_harvest_path")
    elif "/canonical/" in rel or rel.endswith("system_manifest.json"):
        authority, temporal = "CERTIFIED_STATE", "CURRENT"
        evidence.append("canonical_path")
    elif "/archive/" in rel or "old_folders" in rel:
        authority, temporal = "HISTORICAL_EVIDENCE", "HISTORICAL"
        evidence.append("archive_path")
    elif "/raios/v9/" in rel:
        authority, temporal = "LIVE_OPERATIONAL_STATE", "CURRENT"
        evidence.append("v9_path")
    elif rel.endswith((".md",)) and any(k in rel for k in ("adr", "decision", "architecture")):
        authority, temporal = "ARCHITECTURAL_DECISION", "TIMELESS"
        evidence.append("adr_path")
    elif "/reports/" in rel or "doctor" in Path(rel).name.lower() or rel.endswith("-report.json"):
        authority, temporal = "EXECUTION_EVIDENCE", "CURRENT"
        evidence.append("report_path")
    elif any(p in rel for p in ("/generated/", "__pycache__", ".next/")):
        authority, temporal = "GENERATED_OUTPUT", "CURRENT"
        evidence.append("generated_path")
    elif "proposal" in rel or "patch" in rel:
        authority, temporal = "PROPOSAL", "CURRENT"
        evidence.append("proposal_path")

    if contradicted:
        verification = "CONTRADICTED"
        evidence.append("provider_disagreement")
    elif deterministic_ok and authority != "UNKNOWN":
        verification = "PARTIALLY_VERIFIED"
        evidence.append("deterministic_path_rule")
    else:
        verification = "UNVERIFIED"

    # This parallel package never promotes to CANONICAL.
    knowledge = "DISCOVERED"
    if authority == "HISTORICAL_EVIDENCE":
        knowledge = "SUPERSEDED"
        evidence.append("historical_not_canonical")
    elif authority == "UNKNOWN":
        knowledge = "DISCOVERED"

    if authority not in AUTHORITY_CLASSES:
        authority = "UNKNOWN"
    return AuthorityRecord(
        authority_class=authority,
        temporal_scope=temporal if temporal in TEMPORAL_SCOPES else "UNKNOWN",
        verification_state=verification,
        knowledge_state=knowledge,
        evidence=tuple(evidence),
        model_used=False,
    )
