"""Ready-made tool adapters. Detect and wrap; never download or install."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .config import run, which

# Conservative Magika label -> (class, language). Unmapped labels stay UNKNOWN.
MAGIKA_CLASS = {
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


def magika_available() -> bool:
    if which("magika"):
        return True
    try:
        import magika  # noqa: F401

        return True
    except ImportError:
        return False


def magika_classify(path: Path) -> dict[str, Any] | None:
    """Return Magika hit or None if unavailable/unparseable. Never invent a type."""
    py = _magika_python(path)
    if py is not None:
        return py
    return _magika_cli(path)


def _magika_python(path: Path) -> dict[str, Any] | None:
    try:
        from magika import Magika
    except ImportError:
        return None
    try:
        result = Magika().identify_path(path)
        label = getattr(getattr(result, "output", result), "ct_label", None) or getattr(result, "ct_label", None)
        score = getattr(getattr(result, "output", result), "score", None) or getattr(result, "score", 0.0)
        if not label:
            return None
        return _magika_hit(str(label), float(score or 0), "magika-python")
    except Exception:
        return None


def _magika_cli(path: Path) -> dict[str, Any] | None:
    binary = which("magika")
    if not binary:
        return None
    proc = run(["magika", "--json", str(path)])
    if proc.returncode != 0 or not (proc.stdout or "").strip():
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
    if not label:
        return None
    return _magika_hit(str(label), float(score or 0), "magika-cli")


def _magika_hit(label: str, score: float, detector: str) -> dict[str, Any]:
    mapped = MAGIKA_CLASS.get(label.lower())
    if mapped is None:
        return {
            "file_class": "UNKNOWN",
            "language": None,
            "label": label,
            "confidence": min(float(score), 0.4),
            "detector": detector,
            "magika": True,
            "reason": "UNMAPPED_MAGIKA_LABEL",
        }
    cls, language = mapped
    return {
        "file_class": cls,
        "language": language,
        "label": label,
        "confidence": float(score) if score else 0.9,
        "detector": detector,
        "magika": True,
        "reason": None if cls != "UNKNOWN" else "UNCLAIMED",
    }


def tika_available() -> bool:
    if which("tika") or which("tika-app"):
        return True
    jar = os.environ.get("TIKA_JAR") or os.environ.get("TIKA_PATH")
    return bool(jar and Path(jar).is_file() and which("java"))


def tika_extract(path: Path) -> dict[str, Any]:
    """Text+metadata via Apache Tika if present. No OCR. Source stays immutable."""
    if not tika_available():
        return {
            "status": "UNAVAILABLE",
            "extractor": None,
            "reason": "TIKA_MISSING",
            "text": None,
            "ocr": False,
        }
    cmd = _tika_cmd(path)
    if not cmd:
        return {"status": "UNAVAILABLE", "extractor": None, "reason": "TIKA_MISSING", "text": None, "ocr": False}
    proc = run(cmd, timeout=60.0)
    if proc.returncode != 0:
        return {
            "status": "UNAVAILABLE",
            "extractor": "tika",
            "reason": f"TIKA_FAILED:{proc.returncode}",
            "text": None,
            "ocr": False,
        }
    meta_cmd = _tika_meta_cmd(path)
    metadata: dict[str, Any] = {}
    if meta_cmd:
        meta = run(meta_cmd, timeout=60.0)
        if meta.returncode == 0 and meta.stdout.strip():
            metadata = {"raw": meta.stdout[:8000]}
    return {
        "status": "EXTRACTED",
        "extractor": "tika",
        "text": (proc.stdout or "")[:50000],
        "metadata": metadata,
        "ocr": False,
        "immutable_source": True,
    }


def _tika_cmd(path: Path) -> list[str] | None:
    if which("tika"):
        return ["tika", "--text", str(path)]
    if which("tika-app"):
        return ["tika-app", "--text", str(path)]
    jar = os.environ.get("TIKA_JAR") or os.environ.get("TIKA_PATH")
    if jar and Path(jar).is_file() and which("java"):
        return ["java", "-jar", jar, "-t", str(path)]
    return None


def _tika_meta_cmd(path: Path) -> list[str] | None:
    if which("tika"):
        return ["tika", "--metadata", str(path)]
    jar = os.environ.get("TIKA_JAR") or os.environ.get("TIKA_PATH")
    if jar and Path(jar).is_file() and which("java"):
        return ["java", "-jar", jar, "-m", str(path)]
    return None


def is_universal_ctags() -> bool:
    path = which("ctags")
    if not path:
        return False
    proc = run(["ctags", "--version"])
    text = (proc.stdout or "") + (proc.stderr or "")
    return "Universal Ctags" in text and "Emacs" not in text.splitlines()[0] if text else False


def is_ast_grep() -> bool:
    for name in ("ast-grep", "sg"):
        path = which(name)
        if not path:
            continue
        proc = run([name, "--version"])
        blob = ((proc.stdout or "") + (proc.stderr or "")).lower()
        if "ast-grep" in blob:
            return True
    return False


def jq_available() -> bool:
    return bool(which("jq"))


def yq_available() -> bool:
    return bool(which("yq"))


def magika_health() -> dict[str, Any]:
    avail = magika_available()
    return {
        "ok": avail,
        "status": "AVAILABLE" if avail else "MISSING",
        "adapter": "WRAP",
        "install": False,
        "evidence": ["magika_cli_or_python"] if avail else ["ADAPTER_PRESENT_BINARY_MISSING"],
        "fallback": "signature+parser-probe",
        "preferred": True,
    }


def tika_health() -> dict[str, Any]:
    avail = tika_available()
    java = bool(which("java"))
    return {
        "ok": avail,
        "status": "AVAILABLE" if avail else "MISSING",
        "adapter": "WRAP",
        "install": False,
        "java": java,
        "ocr": False,
        "evidence": ["tika_cli_or_jar"] if avail else ["ADAPTER_PRESENT_BINARY_MISSING"],
        "fallback": "stdlib-decode/zipfile; UNAVAILABLE for PDF/Office",
    }


class MagikaAdapter:
    """Detect-only wrap. Never installs Magika."""

    name = "magika"

    @classmethod
    def health(cls) -> dict[str, Any]:
        return magika_health()

    @classmethod
    def classify(cls, path: Path) -> dict[str, Any] | None:
        return magika_classify(path)


class TikaAdapter:
    """Detect-only wrap. Never downloads a Tika jar. No OCR."""

    name = "tika"

    @classmethod
    def health(cls) -> dict[str, Any]:
        return tika_health()

    @classmethod
    def extract(cls, path: Path) -> dict[str, Any]:
        return tika_extract(path)
