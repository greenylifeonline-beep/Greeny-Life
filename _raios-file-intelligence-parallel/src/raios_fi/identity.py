"""Cross-version identity. Basename is never sufficient."""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .parse import parse_file

RELATIONS = (
    "SAME",
    "RENAMED",
    "MOVED",
    "MODIFIED",
    "SPLIT",
    "MERGED",
    "SEMANTIC_EQUIVALENT",
    "SEMANTIC_DIVERGENCE",
    "UNRELATED",
    "UNKNOWN",
)


@dataclass(frozen=True)
class IdentityMatch:
    relation: str
    score: float
    signals: dict[str, bool]
    evidence: tuple[str, ...]
    basename_only: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalized_hash(data: bytes) -> str:
    text = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n").strip()
    return hashlib.sha256(text).hexdigest()


def symbol_fingerprint(path: Path) -> str | None:
    parsed = parse_file(path)
    if parsed.parser in {"unavailable", "python-ast-failed"} and not parsed.symbols:
        return None
    names = sorted({s.qualified_name for s in parsed.symbols})
    imports = sorted(parsed.imports)
    blob = "|".join(names + ["#"] + imports)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def match_records(a: dict[str, Any], b: dict[str, Any]) -> IdentityMatch:
    """Match two FileObjects. Basename agreement alone yields UNKNOWN, not SAME."""
    path_a = str(a.get("root_relative") or a.get("relative_path") or "")
    path_b = str(b.get("root_relative") or b.get("relative_path") or "")
    name_a, name_b = Path(path_a).name, Path(path_b).name
    parent_a = str(Path(path_a).parent)
    parent_b = str(Path(path_b).parent)
    hash_a, hash_b = a.get("sha256"), b.get("sha256")
    norm_a, norm_b = a.get("normalized_sha256"), b.get("normalized_sha256")
    sym_a, sym_b = a.get("symbol_fingerprint"), b.get("symbol_fingerprint")
    dep_a = tuple(sorted(a.get("imports") or []))
    dep_b = tuple(sorted(b.get("imports") or []))

    signals = {
        "exact_path": path_a == path_b and bool(path_a),
        "exact_hash": bool(hash_a) and hash_a == hash_b,
        "normalized_hash": bool(norm_a) and norm_a == norm_b,
        "git_lineage": bool(a.get("git_state") and a.get("git_state") == b.get("git_state") and path_a == path_b),
        "symbol_fingerprint": bool(sym_a) and sym_a == sym_b,
        "ast_fingerprint": bool(a.get("ast_fingerprint")) and a.get("ast_fingerprint") == b.get("ast_fingerprint"),
        "dependency_neighborhood": bool(dep_a) and dep_a == dep_b,
        "basename": name_a == name_b and bool(name_a),
    }
    evidence = [k for k, v in signals.items() if v]

    if signals["exact_hash"] and signals["exact_path"]:
        relation = "SAME"
        score = 1.0
    elif signals["exact_hash"] and name_a == name_b and parent_a != parent_b:
        relation = "MOVED"
        score = 0.95
    elif signals["exact_hash"] and name_a != name_b:
        relation = "RENAMED"
        score = 0.95
    elif signals["exact_path"] and hash_a != hash_b:
        if signals["symbol_fingerprint"]:
            relation = "MODIFIED"
            score = 0.8
        elif sym_a and sym_b and sym_a != sym_b:
            relation = "SEMANTIC_DIVERGENCE"
            score = 0.7
        else:
            relation = "MODIFIED"
            score = 0.75
    elif signals["symbol_fingerprint"] and signals["dependency_neighborhood"] and not signals["exact_hash"]:
        relation = "SEMANTIC_EQUIVALENT"
        score = 0.65
    elif signals["basename"] and not signals["exact_hash"] and not signals["exact_path"]:
        relation = "UNKNOWN"
        score = 0.2
        evidence.append("basename_insufficient")
    else:
        relation = "UNRELATED" if evidence else "UNKNOWN"
        score = 0.1 if relation == "UNRELATED" else 0.0

    if relation not in RELATIONS:
        relation = "UNKNOWN"
    return IdentityMatch(
        relation=relation,
        score=score,
        signals=signals,
        evidence=tuple(evidence),
        basename_only=signals["basename"] and not any(
            signals[k] for k in ("exact_path", "exact_hash", "normalized_hash", "symbol_fingerprint")
        ),
    )
