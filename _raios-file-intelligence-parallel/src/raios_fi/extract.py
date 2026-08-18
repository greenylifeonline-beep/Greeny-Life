"""Text extraction. Tika if available; stdlib fallback. Source remains immutable."""
from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any

from .config import FailClosed, which
from .spi import BaseProvider


class TextExtractionProvider(BaseProvider):
    name = "extract"
    capability = "text-extract"
    per_file_cost = 0.05
    accuracy = 0.7

    def health(self) -> dict[str, Any]:
        return {"ok": True, "tika": bool(which("tika")), "ocr": False}

    def analyze(self, obj: dict[str, Any]) -> dict[str, Any]:
        path = Path(obj["absolute_path"])
        src_hash = obj.get("sha256")
        if obj.get("class") == "ARCHIVE" or path.suffix.lower() == ".zip" or obj.get("mime") == "application/zip":
            return self._zip(path, src_hash)
        if obj.get("language") in {"pdf"} or path.suffix.lower() == ".pdf" or (obj.get("mime") == "application/pdf"):
            if which("tika"):
                return {"status": "TIKA_AVAILABLE_NOT_INVOKED", "extractor": "tika"}
            return {
                "status": "UNAVAILABLE",
                "extractor": None,
                "reason": "TIKA_MISSING",
                "text": None,
                "source_hash": src_hash,
                "immutable_source": True,
            }
        if obj.get("is_text"):
            enc = obj.get("encoding") or "utf-8"
            raw = path.read_bytes()
            text = raw.decode(enc, errors="replace")
            return {
                "status": "EXTRACTED",
                "extractor": "stdlib-decode",
                "text": text[:50000],
                "metadata": {"encoding": enc, "bytes": len(raw)},
                "embedded_resources": [],
                "source_hash": src_hash,
                "immutable_source": True,
            }
        return {"status": "SKIPPED_BINARY", "text": None, "source_hash": src_hash, "immutable_source": True}

    def _zip(self, path: Path, src_hash: str | None) -> dict[str, Any]:
        names = []
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
        return {
            "status": "MANIFEST",
            "extractor": "zipfile",
            "text": "\n".join(names),
            "embedded_resources": names,
            "source_hash": src_hash,
            "immutable_source": True,
        }


class ArchiveProvider(BaseProvider):
    name = "archive"
    capability = "archive-read"

    def analyze(self, obj: dict[str, Any]) -> dict[str, Any]:
        return TextExtractionProvider().analyze(obj)
