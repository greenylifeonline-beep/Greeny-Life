"""Scandinavian isolation: shared understanding, locale-specific realization.

Norwegian, Swedish and Danish share vocabulary. NeuroLingua must not emit a
mixed Scandinavian language. Leakage detection uses distinctive tokens from
``configs/neuro_lingua/scandinavian.yaml``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from raios.neuro_lingua.types import SCANDINAVIAN_LOCALES


@dataclass
class LeakageReport:
    target_locale: str
    leaked_tokens: list[str]
    passed: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_locale": self.target_locale,
            "leaked_tokens": list(self.leaked_tokens),
            "passed": self.passed,
        }


class ScandinavianIsolator:
    def __init__(self, path: Path) -> None:
        payload: dict[str, Any] = {}
        if path.exists():
            payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        self.distinctive: dict[str, set[str]] = {
            locale: {tok.casefold() for tok in tokens}
            for locale, tokens in (payload.get("distinctive") or {}).items()
        }
        self.forbidden: dict[str, set[str]] = {
            locale: {tok.casefold() for tok in (cfg or {}).get("forbidden") or []}
            for locale, cfg in (payload.get("leakage") or {}).items()
        }
        self.infinitive = {
            locale: {tok.casefold() for tok in tokens}
            for locale, tokens in (payload.get("infinitive_markers") or {}).items()
        }

    def detect_leakage(self, text: str, target_locale: str) -> LeakageReport:
        if target_locale not in SCANDINAVIAN_LOCALES:
            return LeakageReport(target_locale=target_locale, leaked_tokens=[], passed=True)
        tokens = [tok.casefold() for tok in re.findall(r"[A-Za-zÀ-ÖØ-öø-ÿ]+", text)]
        forbidden = self.forbidden.get(target_locale, set())
        leaked = [tok for tok in tokens if tok in forbidden]
        # Infinitive marker leakage (å vs att vs at) — only when used as a word.
        for locale, markers in self.infinitive.items():
            if locale == target_locale:
                continue
            for marker in markers:
                if marker in tokens and marker not in self.infinitive.get(target_locale, set()):
                    leaked.append(marker)
        unique = list(dict.fromkeys(leaked))
        return LeakageReport(
            target_locale=target_locale,
            leaked_tokens=unique,
            passed=not unique,
        )

    def sibling_tokens(self, locale: str) -> set[str]:
        siblings: set[str] = set()
        for other, tokens in self.distinctive.items():
            if other != locale:
                siblings |= tokens
        return siblings
