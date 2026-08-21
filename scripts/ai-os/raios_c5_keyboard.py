#!/usr/bin/env python3
"""Decode Arabic typed on an English keyboard (layout flipped). Stdlib only. No WAL."""
from __future__ import annotations

import re
from typing import Any

# Microsoft Arabic 101, unshifted. Capitals mean the same letters (founder holds Shift
# while the OS keyboard is still English).
EN_TO_AR = {
    "q": "ض",
    "w": "ص",
    "e": "ث",
    "r": "ق",
    "t": "ف",
    "y": "غ",
    "u": "ع",
    "i": "ه",
    "o": "خ",
    "p": "ح",
    "[": "ج",
    "]": "د",
    "a": "ش",
    "s": "س",
    "d": "ي",
    "f": "ب",
    "g": "ل",
    "h": "ا",
    "j": "ت",
    "k": "ن",
    "l": "م",
    ";": "ك",
    "'": "ط",
    "z": "ئ",
    "x": "ء",
    "c": "ؤ",
    "v": "ر",
    "b": "لا",
    "n": "ى",
    "m": "ة",
    ",": "و",
    ".": "ز",
    "/": "ظ",
    "`": "ذ",
}

ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
LATIN_RE = re.compile(r"[A-Za-z]")
PROTECT_RE = re.compile(
    r"\b(?:C[0-5]|GL-?00[0-9]|H00\d+|WH-\d+|SHIP-[A-Z0-9-]+|SKU)\b",
    re.I,
)
KEEP_WORDS = {
    "http",
    "https",
    "python",
    "git",
    "oss",
    "gpu",
    "cpu",
    "ollama",
    "index",
    "json",
    "true",
    "false",
}
ENGLISH_HINTS = {
    "the",
    "and",
    "for",
    "with",
    "this",
    "that",
    "from",
    "you",
    "are",
    "is",
    "to",
    "of",
    "hello",
    "what",
    "who",
    "how",
    "please",
    "status",
    "screen",
    "true",
    "false",
}


def _protect(text: str) -> tuple[str, list[str]]:
    held: list[str] = []

    def stash(match: re.Match[str]) -> str:
        held.append(match.group(0))
        return f"\x00{len(held) - 1}\x00"

    return PROTECT_RE.sub(stash, text), held


def _restore(text: str, held: list[str]) -> str:
    def unstash(match: re.Match[str]) -> str:
        return held[int(match.group(1))]

    return re.sub(r"\x00(\d+)\x00", unstash, text)


def transliterate_en_to_ar(text: str) -> str:
    out: list[str] = []
    for char in text:
        lower = char.lower()
        out.append(EN_TO_AR.get(lower, char))
    return "".join(out)


def looks_flipped(text: str) -> bool:
    arabic = len(ARABIC_RE.findall(text))
    latin = len(LATIN_RE.findall(text))
    if latin < 4:
        return False
    if arabic > latin:
        return False
    words = {w.lower() for w in re.findall(r"[A-Za-z]+", text)}
    if words & ENGLISH_HINTS and not any(ch in text for ch in ";[]"):
        return False
    if any(ch in text for ch in ";[]`"):
        return True
    return arabic == 0


def decode_flipped_keyboard(text: str) -> dict[str, Any]:
    original = text or ""
    stripped = original.strip()
    protected, held = _protect(stripped)
    if not looks_flipped(protected):
        rec = {
            "flipped": False,
            "original": original,
            "decoded": original,
            "applied": False,
        }
        return rec
    decoded = _restore(transliterate_en_to_ar(protected), held)
    rec = {
        "flipped": True,
        "original": original,
        "decoded": decoded,
        "applied": decoded != original,
    }
    return rec


def teach_text(text: str) -> str:
    rec = decode_flipped_keyboard(text)
    return rec["decoded"] if rec["applied"] else rec["original"]
