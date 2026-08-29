from __future__ import annotations

import re
from typing import Any

from .schema import ProtectedToken


PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("url", re.compile(r"https?://\S+")),
    ("windows_path", re.compile(r"[A-Za-z]:\\[^\s]+")),
    ("posix_path", re.compile(r"(?:(?<=\s)|(?<=^))(?:\.{0,2}/)[A-Za-z0-9._/-]+")),
    ("env_var", re.compile(r"\$[A-Z_][A-Z0-9_]*")),
    ("filename", re.compile(r"\b[A-Za-z][A-Za-z0-9._-]*\.(?:py|ts|tsx|js|json|yaml|yml|md|ps1|sql)\b")),
    ("cli_flag", re.compile(r"(?<![A-Za-z0-9])--[A-Za-z0-9_-]+")),
    ("version", re.compile(r"\bv?\d+\.\d+(?:\.\d+)?\b")),
    ("hash", re.compile(r"\b(?:sha256:)?[a-fA-F0-9]{32,}\b")),
    ("id", re.compile(r"\b[A-Z]{2,}[-_][A-Z0-9-]{3,}\b")),
    ("sku", re.compile(r"\b[HBSO]\d{3}\b")),
    ("qualified_ident", re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+\b")),
    ("function", re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\(\)")),
    ("number", re.compile(r"\b\d+(?:[.,]\d+)?\b")),
]


TECHNICAL_WORDS = {
    "migration",
    "report",
    "executor",
    "deploye",
    "deploy",
    "builden",
    "build",
    "production",
    "database",
    "databasen",
    "qwen",
    "ollama",
    "prisma",
    "wal",
}


def extract_protected_tokens(text: str) -> dict[str, Any]:
    found: list[ProtectedToken] = []
    occupied: list[tuple[int, int]] = []
    evidence: list[str] = []

    def overlaps(span: tuple[int, int]) -> bool:
        for start, end in occupied:
            if not (span[1] <= start or span[0] >= end):
                return True
        return False

    for kind, pattern in PATTERNS:
        for match in pattern.finditer(text):
            span = match.span()
            if overlaps(span):
                continue
            occupied.append(span)
            token = ProtectedToken(text=match.group(0), kind=kind, span=span, translate=False)
            found.append(token)
            evidence.append(f"{kind}:{match.group(0)}")

    for match in re.finditer(r"[A-Za-z][A-Za-z0-9_+.#-]*", text):
        word = match.group(0)
        if word.lower() in TECHNICAL_WORDS:
            span = match.span()
            if overlaps(span):
                continue
            occupied.append(span)
            found.append(ProtectedToken(text=word, kind="technical_term", span=span, translate=False))
            evidence.append(f"technical_term:{word}")

    found.sort(key=lambda t: t.span[0] if t.span else 0)
    return {
        "status": "OK",
        "confidence": 0.9 if found else 0.6,
        "evidence": evidence,
        "tokens": found,
        "warnings": [] if found else ["NO_PROTECTED_TOKENS"],
    }


def preserve_in_text(source: str, realized: str, tokens: list[ProtectedToken]) -> tuple[str, list[str]]:
    warnings: list[str] = []
    output = realized
    for token in tokens:
        if token.text in source and token.text not in output:
            warnings.append(f"MISSING_PROTECTED:{token.text}")
    return output, warnings
