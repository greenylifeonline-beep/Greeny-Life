from __future__ import annotations

import re
from typing import Any

from .schema import CodeSwitchSegment, TokenRole


TECHNICAL_RE = re.compile(
    r"(?:"
    r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+"
    r"|--[A-Za-z0-9_-]+"
    r"|/[A-Za-z0-9._\\/-]+"
    r"|[A-Za-z]:\\[^\s]+"
    r"|https?://\S+"
    r"|\$[A-Z_][A-Z0-9_]*"
    r"|v?\d+\.\d+(?:\.\d+)?"
    r"|sha256:[a-fA-F0-9]{8,}"
    r"|[A-Fa-f0-9]{32,}"
    r"|[A-Za-z_][A-Za-z0-9_]*(?:\(\))"
    r")"
)

LATIN_WORD = re.compile(r"[A-Za-z][A-Za-z0-9_+.#-]*")
ARABIC_RUN = re.compile(r"[\u0600-\u06FF][^A-Za-z]*")


def _role_for(token: str) -> TokenRole:
    if token.startswith(("/", "\\")) or ":\\" in token or token.startswith("http"):
        return TokenRole.PATH if not token.startswith("http") else TokenRole.URL
    if token.startswith("--") or token.startswith("$"):
        return TokenRole.COMMAND
    if re.fullmatch(r"v?\d+\.\d+(?:\.\d+)?", token) or re.fullmatch(r"\d+", token):
        return TokenRole.NUMBER
    if "." in token or token.endswith("()") or "_" in token:
        return TokenRole.IDENTIFIER
    return TokenRole.TECHNICAL


def segment_code_switch(text: str, primary_locale: str) -> dict[str, Any]:
    segments: list[CodeSwitchSegment] = []
    warnings: list[str] = []
    evidence: list[str] = []
    cursor = 0
    for match in LATIN_WORD.finditer(text):
        start, end = match.span()
        if start > cursor:
            prefix = text[cursor:start]
            if prefix.strip():
                locale = primary_locale
                role = TokenRole.NATURAL_LANGUAGE
                if re.search(r"[\u0600-\u06FF]", prefix):
                    locale = primary_locale if primary_locale.startswith("ar") else "ar"
                segments.append(CodeSwitchSegment(text=prefix.strip(), locale=locale, role=role, evidence=["script_run"]))
        token = match.group(0)
        role = _role_for(token)
        locale = "en" if role != TokenRole.NATURAL_LANGUAGE else primary_locale
        segments.append(
            CodeSwitchSegment(
                text=token,
                locale=locale,
                role=role,
                evidence=["latin_token", f"role:{role.value}"],
            )
        )
        evidence.append(f"latin_token:{token}")
        cursor = end
    if cursor < len(text):
        tail = text[cursor:].strip()
        if tail:
            locale = primary_locale
            if re.search(r"[\u0600-\u06FF]", tail) and not primary_locale.startswith("ar"):
                locale = "ar"
            segments.append(CodeSwitchSegment(text=tail, locale=locale, role=TokenRole.NATURAL_LANGUAGE, evidence=["tail"]))

    if not segments:
        segments = [CodeSwitchSegment(text=text, locale=primary_locale, role=TokenRole.NATURAL_LANGUAGE, evidence=["single_span"])]

    merged: list[CodeSwitchSegment] = []
    for seg in segments:
        if merged and merged[-1].locale == seg.locale and merged[-1].role == seg.role == TokenRole.NATURAL_LANGUAGE:
            merged[-1] = CodeSwitchSegment(
                text=(merged[-1].text + " " + seg.text).strip(),
                locale=seg.locale,
                role=seg.role,
                evidence=list(dict.fromkeys(merged[-1].evidence + seg.evidence)),
            )
        else:
            merged.append(seg)

    switched = len({seg.locale for seg in merged}) > 1
    if not switched:
        warnings.append("NO_CODE_SWITCH_DETECTED")
    return {
        "status": "OK",
        "confidence": 0.86 if switched else 0.7,
        "evidence": evidence,
        "segments": merged,
        "warnings": warnings,
        "code_switch": switched,
    }
