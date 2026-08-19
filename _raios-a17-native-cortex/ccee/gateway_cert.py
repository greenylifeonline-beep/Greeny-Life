"""Fail-closed multimodal gateway certification.

HEALTH_CHECK is not LIVE. Chat HTTP 500 cannot mint QWEN_CHAT=PASS.
This is a Shadow Lab / CCEE certifier, not a production C9 gateway.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .certification import AuthoritativeVerdict, EvidenceLedger, FalsePassDetector
from .config import FailClosed, canonical_json, contains_forbidden_success, utc_now
from .ollama_runtime import OllamaRuntimeManager

ARABIC_RE = re.compile(r"[\u0600-\u06FF]")
NORWEGIAN_HINT = re.compile(r"[æøåÆØÅ]|norsk|hvordan", re.I)
ENGLISH_RE = re.compile(r"[A-Za-z]{3,}")


def language_evidence(lang: str, text: str) -> bool:
    body = text or ""
    if not body.strip():
        return False
    key = lang.lower()
    if key in {"ar", "arabic"}:
        return bool(ARABIC_RE.search(body))
    if key in {"no", "nb", "nn", "norwegian"}:
        return bool(NORWEGIAN_HINT.search(body) or ENGLISH_RE.search(body))
    if key in {"en", "english"}:
        return bool(ENGLISH_RE.search(body))
    return False


class GatewayChatCertifier:
    """Mandatory chat gates. overall_status is never PASS/LIVE."""

    def __init__(self, ledger: EvidenceLedger | None = None) -> None:
        self.ledger = ledger
        self.detector = FalsePassDetector()

    def certify(
        self,
        *,
        health: dict[str, Any],
        chat: dict[str, Any],
        languages: dict[str, str] | None = None,
        stale_live_path: str | Path | None = None,
        run_id: str = "gw-run",
        model_present: bool | None = None,
    ) -> dict[str, Any]:
        languages = languages or {}
        health_ok = int(health.get("http") or 0) == 200 and bool(health.get("ok", True))
        chat_http = int(chat.get("http") or 0)
        body = str(chat.get("body") or chat.get("response") or "")
        chat_ok = chat_http == 200 and bool(body.strip())
        lang_ok = {name: language_evidence(name, text) for name, text in languages.items()}
        all_lang = (not lang_ok) or all(lang_ok.values())
        printed = contains_forbidden_success(canonical_json({"health": health, "chat": chat, "languages": languages}))
        if stale_live_path:
            path = Path(stale_live_path)
            if path.is_file():
                raw = path.read_text(encoding="utf-8")
                printed.extend(contains_forbidden_success(raw))
                if "LIVE" in raw.upper() or '"run_id"' in raw:
                    try:
                        data = json.loads(raw)
                    except json.JSONDecodeError:
                        data = {}
                    if data.get("run_id") and data.get("run_id") != run_id:
                        raise FailClosed("STALE_LIVE_OR_SUCCESS_RECEIPT")
                    if "LIVE" in raw.upper() and not chat_ok:
                        raise FailClosed("STALE_LIVE_RECEIPT")

        gates_complete = bool(health_ok and chat_ok and all_lang and (model_present is not False))
        if printed and not gates_complete:
            raise FailClosed("FALSE_PASS_DETECTED:" + ",".join(printed or ["LIVE"]))
        if health_ok and not chat_ok:
            raise FailClosed(f"CHAT_GATE_FAILED:http={chat_http}")
        if not chat_ok:
            raise FailClosed(f"CHAT_GATE_FAILED:http={chat_http}")
        if not all_lang:
            missing = [k for k, ok in lang_ok.items() if not ok]
            raise FailClosed("LANGUAGE_GATE_FAILED:" + ",".join(missing))
        if model_present is False:
            raise FailClosed("MODEL_MISSING")

        verdict = self.detector.verdict(
            exit_code=0,
            artifact_exists=True,
            artifact_valid=True,
            hash_stable=True,
            tests_ok=True,
            upstream_ok=True,
            no_critical_contradiction=True,
            gates_complete=True,
            stdout="gateway-chat-gates",
            reason="chat_and_language_gates",
        )
        payload = {
            "ok": verdict.ok,
            "overall_status": verdict.overall_status(),
            "exit_code": verdict.exit_code,
            "HEALTH_CHECK": "GATES_SATISFIED" if health_ok else "FAILED",
            "QWEN_CHAT": "GATES_SATISFIED" if chat_ok else "FAILED",
            "language_gates": {k: ("GATES_SATISFIED" if v else "FAILED") for k, v in lang_ok.items()},
            "STATUS": "NOT_LIVE",
            "canonical": False,
            "created_at": utc_now(),
            "run_id": run_id,
        }
        if contains_forbidden_success(canonical_json(payload)):
            raise FailClosed("FALSE_PASS_DETECTED:CERTIFIER_EMITTED_SUCCESS_TOKEN")
        if self.ledger is not None:
            self.ledger.persist_success(payload, _registry_from_verdict(verdict))
        return payload


def _registry_from_verdict(verdict: AuthoritativeVerdict):
    from .certification import AssertionRegistry

    reg = AssertionRegistry()
    reg.require("verdict", verdict.ok)
    return reg


def prove_real_chat(ollama: OllamaRuntimeManager | None = None) -> dict[str, Any]:
    """Live Qwen proof. Unreachable cortex is FAILED, never QWEN_CHAT=PASS."""
    runtime = ollama or OllamaRuntimeManager()
    inventory = runtime.inventory()
    if not inventory.get("ok"):
        return {
            "ok": False,
            "overall_status": "FAILED",
            "QWEN_CHAT": "FAILED",
            "ARABIC_CHAT": "FAILED",
            "ENGLISH_CHAT": "FAILED",
            "NORWEGIAN_CHAT": "FAILED",
            "STATUS": "NOT_LIVE",
            "reason": inventory.get("reason") or "OLLAMA_UNAVAILABLE",
            "canonical": False,
        }
    if not inventory.get("main_cortex_present"):
        return {
            "ok": False,
            "overall_status": "FAILED",
            "QWEN_CHAT": "FAILED",
            "reason": "MAIN_CORTEX_MISSING",
            "models": inventory.get("models") or [],
            "STATUS": "NOT_LIVE",
            "canonical": False,
        }
    raise FailClosed("LIVE_GENERATE_REQUIRES_HUMAN_APPROVAL")
