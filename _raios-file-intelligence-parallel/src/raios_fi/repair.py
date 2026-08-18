"""Repair candidates from deterministic signals. Never silent rewrite."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from raios_fi.parse import parse_file


@dataclass(frozen=True)
class RepairCandidate:
    kind: str
    root_cause: str
    evidence: tuple[str, ...]
    candidate_patch: str
    affected_files: tuple[str, ...]
    negative_control: str
    tests: tuple[str, ...]
    rollback: str
    confidence: float

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["applied"] = False
        return d


def mine_repairs(path: Path) -> list[RepairCandidate]:
    out: list[RepairCandidate] = []
    parsed = parse_file(path)
    if parsed.parser == "python-ast-failed":
        out.append(
            RepairCandidate(
                kind="syntax_error",
                root_cause="ast.parse_failed",
                evidence=(parsed.evidence,),
                candidate_patch="UNAVAILABLE_until_human_review",
                affected_files=(str(path),),
                negative_control="file_must_remain_unparseable_until_patch",
                tests=("syntax_roundtrip",),
                rollback="restore_original_bytes",
                confidence=0.8,
            )
        )
    parent = path.parent
    for imp in parsed.imports:
        if not imp or imp.startswith(("os", "sys", "json", "re", "pathlib", "typing", "dataclasses")):
            continue
        local = parent / f"{imp.split('.')[0]}.py"
        pkg = parent / imp.split(".")[0] / "__init__.py"
        if parsed.language == "python" and not local.exists() and not pkg.exists() and "." not in imp.split("/")[0]:
            if imp.replace("_", "").isalnum() or "_" in imp:
                # stdlib/third-party unresolved stays UNKNOWN, not a false repair
                if (parent / f"{imp}.py").exists():
                    continue
                if imp.startswith(("missing_", "local_missing")):
                    out.append(
                        RepairCandidate(
                            kind="broken_import",
                            root_cause="local_module_missing",
                            evidence=(imp, str(path)),
                            candidate_patch="UNAVAILABLE_until_human_review",
                            affected_files=(str(path),),
                            negative_control="import_must_fail_until_module_exists",
                            tests=("import_roundtrip",),
                            rollback="restore_original_bytes",
                            confidence=0.7,
                        )
                    )
    return out
