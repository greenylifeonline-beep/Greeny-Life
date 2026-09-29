"""Read-only file intelligence capability.

Extracted from historical Cursor donor work and folded into canonical RAIOS.
No second runtime, registry, WAL, or automatic dependency installation.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
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

MAGIKA_CLASS: dict[str, tuple[str, str | None]] = {
    "python": ("CODE", "python"),
    "javascript": ("CODE", "javascript"),
    "typescript": ("CODE", "typescript"),
    "tsx": ("CODE", "tsx"),
    "powershell": ("CODE", "powershell"),
    "shell": ("CODE", "shell"),
    "sql": ("CODE", "sql"),
    "json": ("DATA", "json"),
    "yaml": ("CONFIG", "yaml"),
    "toml": ("CONFIG", "toml"),
    "xml": ("DOCUMENT", "xml"),
    "html": ("DOCUMENT", "html"),
    "markdown": ("DOCUMENT", "markdown"),
    "pdf": ("DOCUMENT", "pdf"),
    "zip": ("ARCHIVE", "zip"),
    "png": ("MEDIA", "png"),
    "jpeg": ("MEDIA", "jpeg"),
    "jpg": ("MEDIA", "jpeg"),
    "sqlite": ("DATABASE", "sqlite"),
    "elf": ("BINARY", None),
    "unknown": ("UNKNOWN", None),
}

_SIGNATURES: tuple[tuple[bytes, str, str | None], ...] = (
    (b"%PDF-", "DOCUMENT", "pdf"),
    (b"PK\x03\x04", "ARCHIVE", "zip"),
    (b"\x89PNG\r\n\x1a\n", "MEDIA", "png"),
    (b"\xff\xd8\xff", "MEDIA", "jpeg"),
    (b"SQLite format 3\x00", "DATABASE", "sqlite"),
)

_TEXT_HINTS = {
    ".py": "python",
    ".js": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".ts": "typescript",
    ".tsx": "tsx",
    ".ps1": "powershell",
    ".sh": "shell",
    ".sql": "sql",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".xml": "xml",
    ".html": "html",
    ".htm": "html",
    ".md": "markdown",
    ".txt": "text",
}


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


def classify_authority(
    path: str | Path,
    *,
    deterministic_ok: bool = False,
    contradicted: bool = False,
) -> AuthorityRecord:
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
    elif rel.endswith(".md") and any(k in rel for k in ("adr", "decision", "architecture")):
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

    knowledge = "SUPERSEDED" if authority == "HISTORICAL_EVIDENCE" else "DISCOVERED"
    return AuthorityRecord(
        authority_class=authority if authority in AUTHORITY_CLASSES else "UNKNOWN",
        temporal_scope=temporal if temporal in TEMPORAL_SCOPES else "UNKNOWN",
        verification_state=verification if verification in VERIFICATION_STATES else "UNVERIFIED",
        knowledge_state=knowledge if knowledge in KNOWLEDGE_STATES else "DISCOVERED",
        evidence=tuple(evidence),
        model_used=False,
    )


def _run(cmd: list[str], *, timeout: float = 60.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, check=False, shell=False)


def _magika_hit(label: str, score: float, detector: str) -> dict[str, Any]:
    mapped = MAGIKA_CLASS.get(label.lower())
    if mapped is None:
        return {
            "file_class": "UNKNOWN",
            "language": None,
            "label": label,
            "confidence": min(float(score), 0.4),
            "detector": detector,
            "reason": "UNMAPPED_MAGIKA_LABEL",
        }
    file_class, language = mapped
    return {
        "file_class": file_class,
        "language": language,
        "label": label,
        "confidence": float(score) if score else 0.9,
        "detector": detector,
        "reason": None if file_class != "UNKNOWN" else "UNCLAIMED",
    }


def magika_classify(path: str | Path) -> dict[str, Any] | None:
    target = Path(path)
    try:
        from magika import Magika  # type: ignore
    except ImportError:
        Magika = None  # type: ignore[assignment]

    if Magika is not None:
        try:
            result = Magika().identify_path(target)
            output = getattr(result, "output", result)
            label = getattr(output, "ct_label", None) or getattr(result, "ct_label", None)
            score = getattr(output, "score", None) or getattr(result, "score", 0.0)
            if label:
                return _magika_hit(str(label), float(score or 0), "magika-python")
        except Exception:
            pass

    binary = shutil.which("magika")
    if not binary:
        return None
    proc = _run([binary, "--json", str(target)])
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    row = payload[0] if isinstance(payload, list) and payload else payload
    if not isinstance(row, dict):
        return None
    result = row.get("result") or row
    value = result.get("value") if isinstance(result, dict) else {}
    output = (value or {}).get("output") if isinstance(value, dict) else result
    if not isinstance(output, dict):
        output = result if isinstance(result, dict) else {}
    label = output.get("ct_label") or output.get("label") or row.get("label")
    score = output.get("score") or row.get("score") or 0.0
    return _magika_hit(str(label), float(score or 0), "magika-cli") if label else None


def tool_health() -> dict[str, Any]:
    magika_cli = shutil.which("magika")
    try:
        import magika  # type: ignore  # noqa: F401
        magika_python = True
    except ImportError:
        magika_python = False

    tika_cli = shutil.which("tika") or shutil.which("tika-app")
    tika_jar = os.environ.get("TIKA_JAR") or os.environ.get("TIKA_PATH")
    tika_jar_ok = bool(tika_jar and Path(tika_jar).is_file() and shutil.which("java"))
    return {
        "status": "PASS",
        "mode": "READ_ONLY",
        "automatic_install": False,
        "llm_default_parser": False,
        "ocr_enabled": False,
        "magika": {"available": bool(magika_cli or magika_python), "cli": bool(magika_cli), "python": magika_python},
        "tika": {"available": bool(tika_cli or tika_jar_ok), "cli": bool(tika_cli), "jar": tika_jar_ok},
    }


def classify_file(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    if not target.is_file():
        return {"status": "UNKNOWN", "file_class": "UNKNOWN", "language": None, "confidence": 0.0, "detector": "none", "reason": "FILE_MISSING", "immutable_source": True}

    hit = magika_classify(target)
    if hit is not None:
        return {"status": "CLASSIFIED", **hit, "immutable_source": True}

    prefix = target.read_bytes()[:64]
    for signature, file_class, language in _SIGNATURES:
        if prefix.startswith(signature):
            return {"status": "CLASSIFIED", "file_class": file_class, "language": language, "confidence": 1.0, "detector": "signature", "reason": None, "immutable_source": True}

    suffix = target.suffix.lower()
    try:
        sample = target.read_bytes()[:8192]
        text = sample.decode("utf-8")
        if suffix == ".json":
            json.loads(target.read_text(encoding="utf-8-sig"))
            return {"status": "CLASSIFIED", "file_class": "DATA", "language": "json", "confidence": 0.95, "detector": "parser-probe", "reason": None, "immutable_source": True}
        if text or target.stat().st_size == 0:
            return {"status": "TEXT_DETECTED", "file_class": "DOCUMENT" if suffix in {".md", ".txt"} else "CODE_OR_TEXT", "language": _TEXT_HINTS.get(suffix), "confidence": 0.55 if suffix in _TEXT_HINTS else 0.45, "detector": "utf8-probe", "reason": "EXTENSION_HINT_NOT_AUTHORITY", "immutable_source": True}
    except (UnicodeDecodeError, OSError, json.JSONDecodeError):
        pass

    return {"status": "UNKNOWN", "file_class": "UNKNOWN", "language": None, "extension_hint": _TEXT_HINTS.get(suffix), "confidence": 0.0, "detector": "none", "reason": "NO_DETERMINISTIC_CLASSIFIER", "immutable_source": True}


def _tika_cmd(path: Path) -> list[str] | None:
    if shutil.which("tika"):
        return ["tika", "--text", str(path)]
    if shutil.which("tika-app"):
        return ["tika-app", "--text", str(path)]
    jar = os.environ.get("TIKA_JAR") or os.environ.get("TIKA_PATH")
    if jar and Path(jar).is_file() and shutil.which("java"):
        return ["java", "-jar", jar, "-t", str(path)]
    return None


def extract_text(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    if not target.is_file():
        return {"status": "UNAVAILABLE", "reason": "FILE_MISSING", "text": None, "extractor": None, "ocr": False, "immutable_source": True}

    try:
        text = target.read_text(encoding="utf-8-sig")
        return {"status": "EXTRACTED", "reason": None, "text": text[:50000], "extractor": "utf8", "ocr": False, "immutable_source": True}
    except (UnicodeDecodeError, OSError):
        pass

    cmd = _tika_cmd(target)
    if not cmd:
        return {"status": "UNAVAILABLE", "reason": "TIKA_MISSING_OR_BINARY_CONTENT", "text": None, "extractor": None, "ocr": False, "immutable_source": True}
    proc = _run(cmd)
    if proc.returncode != 0:
        return {"status": "UNAVAILABLE", "reason": f"TIKA_FAILED:{proc.returncode}", "text": None, "extractor": "tika", "ocr": False, "immutable_source": True}
    return {"status": "EXTRACTED", "reason": None, "text": proc.stdout[:50000], "extractor": "tika", "ocr": False, "immutable_source": True}
