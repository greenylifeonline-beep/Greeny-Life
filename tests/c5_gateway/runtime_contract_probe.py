from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("RAIOS_RUNTIME_ROOT", str(ROOT / ".runtime-test"))

from raios.c5_gateway import gateway
from raios.c5_gateway.ollama_client import CortexResult


def result(ok=True, content="تم الرد بالعربية", error=None, status_code=200):
    return CortexResult("req-test", ok, status_code, "qwen3:0.6b", content, error, 0.01, {}, "now")


checks = {}
original_chat = gateway.client.chat
try:
    gateway.client.chat = lambda *args, **kwargs: result()
    legacy = gateway.ChatRequest(text="مرحبا", language="ar")
    alias = gateway.ChatRequest.model_validate({"message": "مرحبا", "locale": "ar", "stream": False})
    checks["legacy_text"] = legacy.text == "مرحبا"
    checks["message_alias"] = alias.text == "مرحبا" and alias.language == "ar"
    body = gateway.chat(alias)
    checks["arabic_response"] = body["response"] == "تم الرد بالعربية"
    checks["response_aliases"] = body["response"] == body["content"] == body["reply"]
    try:
        gateway.ChatRequest.model_validate({"message": "   "})
        checks["blank_rejected"] = False
    except Exception:
        checks["blank_rejected"] = True
    gateway.client.chat = lambda *args, **kwargs: result(False, "", "TimeoutError::timed out", None)
    try:
        gateway.chat(gateway.ChatRequest(text="اختبار", timeout_seconds=3))
        checks["timeout_504"] = False
    except gateway.HTTPException as exc:
        checks["timeout_504"] = exc.status_code == 504 and exc.detail["error"] == "MAIN_CORTEX_TIMEOUT"
finally:
    gateway.client.chat = original_chat

failed = sorted(name for name, passed in checks.items() if not passed)
print(json.dumps({"checks": checks, "failed": failed}, ensure_ascii=False))
raise SystemExit(1 if failed else 0)