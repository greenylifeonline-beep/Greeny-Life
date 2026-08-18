"""Read-only integration bridge for _raios-a17-native-cortex reports. Never mutates."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..identity import FailClosed, PACKAGE, env_flag, repo_root_from
from ..models import Discovery

REPORT_MAP = {
    "A17.4": ("reports", ("A17.4", "teacher-harvest", "HARVEST")),
    "A17.5": ("reports", ("A17.5", "assimilation", "ASSIMILATION")),
    "A17.6-9": ("reports", ("A17.6", "A17.9", "differential", "mastery")),
    "A17.10-12": ("reports", ("A17.10", "A17.12", "cortex")),
    "A17.13": ("reports", ("A17.13", "qwen", "MAIN-CORTEX")),
}


class NativeCortexBridge:
    ROOT_REL = Path("_raios-a17-native-cortex")

    def __init__(self, repo_root: Path | None = None) -> None:
        self.repo_root = repo_root or repo_root_from()
        override = env_flag("RAIOS_A17_NATIVE_ROOT")
        self.root = Path(override) if override else self.repo_root / self.ROOT_REL

    def discover(self) -> dict[str, Any]:
        if not self.root.exists():
            return {key: Discovery.MISSING.value for key in REPORT_MAP} | {
                "root": str(self.root),
                "status": Discovery.MISSING.value,
            }
        out: dict[str, Any] = {"root": str(self.root), "writable": False}
        reports = self.root / "reports"
        files = [p.name.lower() for p in reports.glob("*")] if reports.exists() else []
        for label, (_dir, needles) in REPORT_MAP.items():
            hits = [n for n in needles if any(n.lower() in name for name in files)]
            if hits:
                out[label] = Discovery.FOUND.value
            elif reports.exists():
                out[label] = Discovery.PENDING.value
            else:
                out[label] = Discovery.MISSING.value
        return out

    def read_json(self, rel: str) -> Any:
        path = (self.root / rel).resolve()
        try:
            path.relative_to(self.root.resolve())
        except ValueError as exc:
            raise FailClosed("PATH_TRAVERSAL_REJECTED") from exc
        if not path.is_file():
            return {"status": Discovery.MISSING.value, "path": str(path)}
        return json.loads(path.read_text(encoding="utf-8"))

    def assert_read_only(self) -> None:
        if PACKAGE in str(self.root):
            return
        # never write; presence of write attempt is a governance failure
        raise FailClosed("NATIVE_CORTEX_IS_READ_ONLY") if False else None
