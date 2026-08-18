"""Text extraction. Tika if available; stdlib fallback. Source remains immutable."""
from __future__ import annotations

import zipfile
from pathlib import Path
from typing import Any

from .adapters import tika_available, tika_extract
from .spi import BaseProvider

TIKA_TYPES = {
    "pdf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
    "odt",
    "ods",
    "odp",
    "epub",
    "html",
    "xml",
    "eml",
    "msg",
}


class TextExtractionProvider(BaseProvider):
    name = "extract"
    capability = "text-extract"
    per_file_cost = 0.05
    accuracy = 0.7

    def health(self) -> dict[str, Any]:
        from .adapters import tika_health

        tika = tika_health()
        return {
            "ok": True,
            "status": "AVAILABLE" if tika_available() else "FALLBACK",
            "tika": tika_available(),
            "tika_adapter": tika,
            "ocr": False,
            "fallback": "stdlib-decode/zipfile",
        }

    def analyze(self, obj: dict[str, Any]) -> dict[str, Any]:
        path = Path(obj["absolute_path"])
        src_hash = obj.get("sha256")
        if obj.get("class") == "ARCHIVE" or path.suffix.lower() == ".zip" or obj.get("mime") == "application/zip":
            return self._zip(path, src_hash)
        lang = (obj.get("language") or "").lower()
        suffix = path.suffix.lower().lstrip(".")
        mime = obj.get("mime") or ""
        needs_tika = (
            lang in TIKA_TYPES
            or suffix in TIKA_TYPES
            or mime.startswith(("application/pdf", "application/msword", "application/vnd."))
        )
        if needs_tika:
            extracted = tika_extract(path)
            extracted["source_hash"] = src_hash
            extracted["immutable_source"] = True
            extracted["ocr"] = False
            if extracted.get("reason"):
                extracted["errors"] = [extracted["reason"]]
            return extracted
        if obj.get("is_text") or _looks_text(path):
            raw = path.read_bytes()
            text, enc = decode_text(raw, obj.get("encoding"))
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


def decode_text(raw: bytes, encoding: str | None = None) -> tuple[str, str]:
    if encoding in {"utf-16", "utf-16-le", "utf-16-be"}:
        return raw.decode("utf-16", errors="replace"), "utf-16"
    if encoding in {"utf-8", "utf-8-sig"}:
        return raw.decode(encoding, errors="replace"), encoding
    if raw.startswith(b"\xff\xfe") or raw.startswith(b"\xfe\xff"):
        return raw.decode("utf-16", errors="replace"), "utf-16"
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw.decode("utf-8-sig", errors="replace"), "utf-8-sig"
    try:
        return raw.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace"), "utf-8-replace"


def _looks_text(path: Path) -> bool:
    try:
        head = path.read_bytes()[:8]
    except OSError:
        return False
    return head.startswith((b"\xff\xfe", b"\xfe\xff", b"\xef\xbb\xbf"))
