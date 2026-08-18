"""Comparison engine: text, symbols, schema, config, behavior. Never assume newer is better."""

from __future__ import annotations

import difflib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .adapters import jq_available, yq_available
from .config import run, sha256_bytes
from .parse import parse_file
from .store import IndexStore, Store


@dataclass(frozen=True)
class ComparisonResult:
    what_changed: str
    why_likely_changed: str
    impact: str
    dependencies: tuple[str, ...]
    tests_affected: tuple[str, ...]
    merge_risk: str
    confidence: float
    evidence: tuple[str, ...]
    source_hash_a: str
    source_hash_b: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ComparisonEngine:
    def __init__(self, store: IndexStore | Store | None = None) -> None:
        self.store = store

    def text_diff(self, a: Path, b: Path) -> ComparisonResult:
        ba = a.read_bytes()
        bb = b.read_bytes()
        ha, hb = sha256_bytes(ba), sha256_bytes(bb)
        if ha == hb:
            return ComparisonResult(
                "none",
                "identical_hash",
                "none",
                (),
                (),
                "none",
                1.0,
                ("same_sha256",),
                ha,
                hb,
            )
        ta = ba.decode("utf-8", errors="replace").splitlines()
        tb = bb.decode("utf-8", errors="replace").splitlines()
        delta = list(difflib.unified_diff(ta, tb, lineterm="", n=1))
        n = max(1, len([x for x in delta if x.startswith(("+", "-"))]))
        risk = "high" if n > 40 else "medium" if n > 8 else "low"
        return ComparisonResult(
            "text_modified",
            "content_hash_diff",
            "file_content",
            (),
            (),
            risk,
            0.9,
            (f"unified_hunks={len(delta)}",),
            ha,
            hb,
        )

    def symbol_diff(self, a: Path, b: Path) -> ComparisonResult:
        pa, pb = parse_file(a), parse_file(b)
        sa = {s.qualified_name for s in pa.symbols}
        sb = {s.qualified_name for s in pb.symbols}
        added, removed = sorted(sb - sa), sorted(sa - sb)
        what = "symbol_modified" if added or removed else "symbols_unchanged"
        risk = "high" if removed else "medium" if added else "low"
        return ComparisonResult(
            what,
            "parser_symbol_set_diff",
            "api_surface" if added or removed else "none",
            tuple(sorted(set(pa.imports) | set(pb.imports)))[:40],
            (),
            risk,
            0.75 if pa.parser != "unavailable" else 0.3,
            (f"added={added[:20]}", f"removed={removed[:20]}"),
            sha256_bytes(a.read_bytes()),
            sha256_bytes(b.read_bytes()),
        )

    def schema_diff(self, a: Path, b: Path) -> ComparisonResult:
        # SQL CREATE TABLE names only — no execution.
        import re

        def tables(p: Path) -> set[str]:
            text = p.read_text(encoding="utf-8", errors="replace")
            return set(re.findall(r"CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?([A-Za-z0-9_]+)", text, re.I))

        ta, tb = tables(a), tables(b)
        return ComparisonResult(
            "schema_drift" if ta != tb else "schema_same",
            "sql_create_table_names",
            "database",
            (),
            (),
            "high" if ta != tb else "none",
            0.8,
            (f"only_a={sorted(ta-tb)}", f"only_b={sorted(tb-ta)}"),
            sha256_bytes(a.read_bytes()),
            sha256_bytes(b.read_bytes()),
        )

    def config_diff(self, a: Path, b: Path) -> ComparisonResult:
        """Structural JSON/YAML diff. jq/yq preferred when present; newer is not assumed better."""
        ba, bb = a.read_bytes(), b.read_bytes()
        ha, hb = sha256_bytes(ba), sha256_bytes(bb)
        if ha == hb:
            return ComparisonResult(
                "none",
                "identical_hash",
                "none",
                (),
                (),
                "none",
                1.0,
                ("same_sha256",),
                ha,
                hb,
            )
        sa, sb = a.suffix.lower(), b.suffix.lower()
        provider = "text"
        canon_a: str | None = None
        canon_b: str | None = None
        if sa == ".json" and sb == ".json":
            canon_a, pa = _canonical_json(a)
            canon_b, pb = _canonical_json(b)
            if canon_a is not None and canon_b is not None:
                provider = pa if pa == pb else f"{pa}+{pb}"
        elif sa in {".yaml", ".yml"} and sb in {".yaml", ".yml"}:
            canon_a, pa = _canonical_yaml(a)
            canon_b, pb = _canonical_yaml(b)
            if canon_a is not None and canon_b is not None:
                provider = pa if pa == pb else f"{pa}+{pb}"
        if canon_a is not None and canon_b is not None:
            same = canon_a == canon_b
            return ComparisonResult(
                "config_equivalent" if same else "config_modified",
                f"{provider}_canonical",
                "config",
                (),
                (),
                "none" if same else "medium",
                0.9 if provider in {"jq", "yq"} else 0.75,
                (f"provider={provider}", f"equivalent={same}"),
                ha,
                hb,
            )
        text = self.text_diff(a, b)
        return ComparisonResult(
            "config_text_modified" if text.what_changed != "none" else "none",
            "config_text_fallback",
            "config",
            text.dependencies,
            text.tests_affected,
            text.merge_risk,
            min(text.confidence, 0.7),
            text.evidence + ("jq_or_yq_structural_unavailable",),
            ha,
            hb,
        )


def _canonical_json(path: Path) -> tuple[str | None, str]:
    if jq_available():
        proc = run(["jq", "-S", ".", str(path)])
        if proc.returncode == 0 and proc.stdout is not None:
            return proc.stdout, "jq"
    try:
        payload = json.dumps(
            json.loads(path.read_text(encoding="utf-8")),
            sort_keys=True,
            separators=(",", ":"),
        )
        return payload, "python-json"
    except (OSError, json.JSONDecodeError, UnicodeError):
        return None, "none"


def _canonical_yaml(path: Path) -> tuple[str | None, str]:
    if not yq_available():
        return None, "none"
    cmds: list[list[str]] = []
    ver = run(["yq", "--version"])
    blob = ((ver.stdout or "") + (ver.stderr or "")).lower()
    if "mikefarah" in blob:
        cmds.append(["yq", "-o=json", str(path)])
    cmds.extend(
        [
            ["yq", "-o=json", str(path)],
            ["yq", ".", str(path)],
        ]
    )
    seen: set[str] = set()
    for cmd in cmds:
        key = " ".join(cmd)
        if key in seen:
            continue
        seen.add(key)
        proc = run(cmd)
        if proc.returncode == 0 and (proc.stdout or "").strip():
            return proc.stdout, "yq"
    return None, "none"
