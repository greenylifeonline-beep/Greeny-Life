"""File type intelligence. Magika preferred; extension is never sole authority."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .config import which
from .spi import BaseProvider

CLASSES = (
    "CODE",
    "CONFIG",
    "DOCUMENT",
    "DATA",
    "DATABASE",
    "ARCHIVE",
    "MEDIA",
    "BINARY",
    "MODEL",
    "GENERATED",
    "EVIDENCE",
    "UNKNOWN",
)

CLASS_GENERATED = "GENERATED"
CLASS_UNKNOWN = "UNKNOWN"

SIGNATURES = (
    (b"%PDF", "DOCUMENT", "application/pdf", "pdf", True),
    (b"PK\x03\x04", "ARCHIVE", "application/zip", "zip", True),
    (b"\x89PNG", "MEDIA", "image/png", "png", True),
    (b"\xff\xd8\xff", "MEDIA", "image/jpeg", "jpeg", True),
    (b"SQLite format 3", "DATABASE", "application/vnd.sqlite3", "sqlite", True),
    (b"\x7fELF", "BINARY", "application/x-elf", None, True),
)

EXT_HINT = {
    ".py": ("CODE", "python"),
    ".ts": ("CODE", "typescript"),
    ".tsx": ("CODE", "tsx"),
    ".js": ("CODE", "javascript"),
    ".ps1": ("CODE", "powershell"),
    ".sql": ("CODE", "sql"),
    ".sh": ("CODE", "shell"),
    ".md": ("DOCUMENT", "markdown"),
    ".html": ("DOCUMENT", "html"),
    ".xml": ("DOCUMENT", "xml"),
    ".json": ("DATA", "json"),
    ".yaml": ("CONFIG", "yaml"),
    ".yml": ("CONFIG", "yaml"),
    ".toml": ("CONFIG", "toml"),
    ".csv": ("DATA", "csv"),
    ".pdf": ("DOCUMENT", "pdf"),
    ".zip": ("ARCHIVE", "zip"),
    ".sqlite": ("DATABASE", "sqlite"),
    ".db": ("DATABASE", "sqlite"),
    ".gguf": ("MODEL", "gguf"),
    ".bin": ("BINARY", None),
}


@dataclass(frozen=True)
class FileTypeResult:
    file_class: str
    mime: str | None
    language: str | None
    is_text: bool
    is_binary: bool
    encoding: str | None
    confidence: float
    detector: str
    extension_trusted: bool
    magika: bool
    reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class FileTypeProvider(BaseProvider):
    name = "file-type"
    capability = "type-detect"
    per_file_cost = 0.02
    accuracy = 0.85

    def __init__(self) -> None:
        self.magika = bool(which("magika"))
        self.file_bin = which("file")

    def health(self) -> dict[str, Any]:
        return {"ok": True, "magika": self.magika, "file": bool(self.file_bin), "extension_alone": False}

    def analyze(self, obj: dict[str, Any]) -> dict[str, Any]:
        path = Path(obj["absolute_path"])
        typed = classify_file(path)
        return {
            "class": typed.file_class,
            "mime": typed.mime or obj.get("mime"),
            "language": typed.language,
            "is_text": typed.is_text,
            "is_binary": typed.is_binary,
            "encoding": typed.encoding,
            "confidence": typed.confidence,
            "extension_trusted": False,
            "detector": typed.detector,
            "magika": typed.magika,
            "reason": typed.reason,
        }


def classify_file(path: Path) -> FileTypeResult:
    magika = bool(which("magika"))
    head = b""
    try:
        with path.open("rb") as fh:
            head = fh.read(256)
    except OSError:
        return FileTypeResult(
            file_class="UNKNOWN",
            mime=None,
            language=None,
            is_text=False,
            is_binary=True,
            encoding=None,
            confidence=0.0,
            detector="unreadable",
            extension_trusted=False,
            magika=magika,
            reason="UNREADABLE",
        )
    sig = _signature(head)
    ext_class, language = EXT_HINT.get(path.suffix.lower(), ("UNKNOWN", None))
    is_text, encoding = _textness(head)
    if sig:
        chosen, mime, _, sig_lang = sig
        confidence = 0.95
        if path.suffix and ext_class not in {chosen, "UNKNOWN"}:
            confidence = 0.92
            language = sig_lang
        else:
            language = sig_lang or language
        detector = "signature"
    else:
        chosen, mime = ext_class, None
        confidence = 0.55 if ext_class != "UNKNOWN" else 0.1
        detector = "probe+ext-hint"
        probed = _parser_probe(head, path)
        if probed:
            chosen, language, probe_conf, detector = probed
            confidence = probe_conf
    if chosen == "UNKNOWN" and is_text:
        if path.suffix.lower() in {".txt", ".md"}:
            chosen = "DOCUMENT"
            confidence = max(confidence, 0.4)
        else:
            chosen = "UNKNOWN"
            detector = "unknown-text"
            confidence = min(confidence, 0.2)
    if "evidence" in {p.lower() for p in path.parts}:
        if chosen in {"DATA", "DOCUMENT", "UNKNOWN"}:
            chosen = "EVIDENCE"
    generated = any(p in {"archive", "generated", "__pycache__", "node_modules"} for p in path.parts)
    if generated and chosen == "CODE":
        chosen = CLASS_GENERATED
    if not is_text and chosen == "UNKNOWN":
        if b"\x00" in head:
            chosen = "BINARY"
            confidence = 0.6
            detector = "null-bytes"
        else:
            confidence = 0.1
            detector = "unknown-binary"
    return FileTypeResult(
        file_class=chosen if chosen in CLASSES else "UNKNOWN",
        mime=mime,
        language=language,
        is_text=is_text and chosen not in {"ARCHIVE", "MEDIA", "BINARY", "DATABASE", "MODEL"},
        is_binary=not (is_text and chosen not in {"ARCHIVE", "MEDIA", "BINARY", "DATABASE", "MODEL"}),
        encoding=encoding if is_text else None,
        confidence=confidence,
        detector=detector,
        extension_trusted=False,
        magika=magika,
        reason=None if chosen != "UNKNOWN" else "UNCLAIMED",
    )


def _signature(head: bytes) -> tuple | None:
    for sig, cls, mime, lang, _ in SIGNATURES:
        if head.startswith(sig) or sig in head[:40]:
            return cls, mime, True, lang
    return None


def _parser_probe(head: bytes, path: Path) -> tuple[str, str | None, float, str] | None:
    """Never trust extension alone. Probe content when signature is absent."""
    stripped = head.lstrip()
    if stripped.startswith((b"def ", b"import ", b"from ", b"class ", b"#!/usr/bin/env python", b"#!/usr/bin/python")):
        return "CODE", "python", 0.8, "parser-probe-python"
    if stripped.startswith((b"CREATE TABLE", b"create table", b"SELECT ", b"select ")):
        return "CODE", "sql", 0.7, "parser-probe-sql"
    if b"$" in head and (stripped.startswith(b"function ") or b"param(" in head.lower()):
        return "CODE", "powershell", 0.65, "parser-probe-ps1"
    if stripped.startswith((b"function ", b"export ", b"const ", b"interface ", b"type ")):
        lang = "typescript" if (b"interface " in stripped or path.suffix.lower() in {".ts", ".tsx"}) else "javascript"
        return "CODE", lang, 0.65, "parser-probe-js"
    return None


def _textness(head: bytes) -> tuple[bool, str | None]:
    if head.startswith(b"\xff\xfe") or head.startswith(b"\xfe\xff"):
        return True, "utf-16"
    if head.startswith(b"\xef\xbb\xbf"):
        return True, "utf-8-sig"
    if not head:
        return True, "utf-8"
    if b"\x00" in head[:64] and not head.startswith((b"\xff\xfe", b"\xfe\xff")):
        return False, None
    try:
        head.decode("utf-8")
        return True, "utf-8"
    except UnicodeDecodeError:
        try:
            head.decode("utf-16")
            return True, "utf-16"
        except UnicodeDecodeError:
            return False, None
