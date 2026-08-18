"""Read-only adapters around existing RAIOS systems. Never duplicate authority."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..identity import FailClosed, PROTECTED_LIVE_WRITERS, env_flag, repo_root_from


class A174HarvestAdapter:
    """Consume completed A17.4 artifacts later. Never writes into live harvest paths."""

    EXPECTED_RELATIVE = Path("_raios-a17-native-cortex") / "experience" / "raw" / "teacher-harvest"

    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = repo_root or repo_root_from()

    def harvest_root(self) -> Path | None:
        override = env_flag("RAIOS_A17_4_HARVEST_ROOT")
        if override:
            return Path(override)
        candidate = self.repo_root / self.EXPECTED_RELATIVE
        if candidate.exists():
            return candidate
        return None

    def status(self) -> dict[str, Any]:
        root = self.harvest_root()
        if root is None:
            return {
                "A17_4_REAL_DATA_CONSUMPTION": "PENDING",
                "reason": "HARVEST_ROOT_ABSENT",
                "expected": str(self.repo_root / self.EXPECTED_RELATIVE),
            }
        files = [p for p in root.rglob("*") if p.is_file()]
        if not files:
            return {
                "A17_4_REAL_DATA_CONSUMPTION": "PENDING",
                "reason": "HARVEST_EMPTY_OR_INCOMPLETE",
                "root": str(root),
            }
        return {
            "A17_4_REAL_DATA_CONSUMPTION": "PENDING",
            "reason": "LIVE_OR_UNVERIFIED_HARVEST_NOT_CERTIFIED_HERE",
            "root": str(root),
            "file_count_observed": len(files),
            "writable": False,
        }

    def iter_artifacts(self) -> list[Path]:
        root = self.harvest_root()
        if root is None:
            return []
        return [p for p in root.iterdir() if p.is_dir() or p.suffix in {".json", ".txt", ".jsonl"}]

    def assert_read_only(self, path: Path) -> None:
        resolved = path.resolve()
        for rel in PROTECTED_LIVE_WRITERS:
            protected = (self.repo_root / rel).resolve()
            try:
                resolved.relative_to(protected)
            except ValueError:
                continue
            raise FailClosed("A17_4_LIVE_PATH_IS_READ_ONLY")


class LearningFabricAdapter:
    """Reuse Cognitive Learning Fabric V2 if present. Do not fork authority."""

    REL = Path("RAIOS-COGNITIVE-LEARNING-FABRIC-REFERENCE-V2")

    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = repo_root or repo_root_from()
        self.path = self.repo_root / self.REL

    def available(self) -> bool:
        return self.path.is_dir()

    def status(self) -> dict[str, Any]:
        return {
            "available": self.available(),
            "role": "REFERENCE_NOT_AUTHORITY",
            "path": str(self.path),
            "reused": True,
        }


class CognitiveExchangeAdapter:
    REL = Path("RAIOS-SHARED-COGNITIVE-EXCHANGE-REFERENCE-V2")

    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = repo_root or repo_root_from()
        self.path = self.repo_root / self.REL

    def status(self) -> dict[str, Any]:
        return {"available": self.path.is_dir(), "role": "CAS_PATTERN_REUSED", "path": str(self.path)}


class V9ContinuityAdapter:
    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = repo_root or repo_root_from()
        self.identity_path = self.repo_root / "RAIOS" / "V9" / "continuity" / "RAIOS-IDENTITY.json"

    def read_identity(self) -> dict[str, Any]:
        if not self.identity_path.is_file():
            return {"status": "UNKNOWN", "path": str(self.identity_path)}
        return json.loads(self.identity_path.read_text(encoding="utf-8"))

    def write_identity(self, *_args: Any, **_kwargs: Any) -> None:
        raise FailClosed("RAIOS_V9_MUTATION_REJECTED")


class ModelEscalationAdapter:
    """Reuse _raios-model-escalation when present. Do not duplicate routing."""

    REL = Path("_raios-model-escalation")
    HIERARCHY = ("L0_DETERMINISTIC_TOOLS", "L1_NATIVE_MAIN_CORTEX", "L2_SELF_CRITIQUE", "L3_TEMPORARY_TEACHER", "L4_EXTERNAL_FRONTIER")

    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = repo_root or repo_root_from()
        self.path = self.repo_root / self.REL

    def status(self) -> dict[str, Any]:
        return {
            "available": self.path.exists(),
            "reused": self.path.exists(),
            "duplicated": False,
            "preferred_hierarchy": list(self.HIERARCHY),
            "small_teachers_permanent_routing_targets": False,
            "path": str(self.path),
        }
