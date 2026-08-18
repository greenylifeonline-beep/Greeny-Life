"""Ollama runtime manager. HTTP 500 is a typed event, never a generic crash."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

from .config import CORTEX_TARGET, TEMPORARY_TEACHERS, FailClosed, env_flag
from .event_bus import EventBus


class OllamaServerError(FailClosed):
    def __init__(self, status: int, body: str = "") -> None:
        super().__init__(f"OLLAMA_SERVER_ERROR:{status}")
        self.status = status
        self.body = body


class CircuitOpen(FailClosed):
    def __init__(self) -> None:
        super().__init__("OLLAMA_CIRCUIT_OPEN")


class OllamaRuntimeManager:
    def __init__(self, bus: EventBus | None = None, base_url: str | None = None) -> None:
        self.bus = bus
        self.base_url = (base_url or env_flag("OLLAMA_HOST") or "http://127.0.0.1:11434").rstrip("/")
        self.failures = 0
        self.circuit_open = False
        self.timeout = 8.0

    def _request(self, path: str, payload: dict[str, Any] | None = None, method: str = "GET") -> dict[str, Any]:
        if self.circuit_open and self.failures >= 3:
            raise CircuitOpen()
        url = self.base_url + path
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = resp.read().decode("utf-8")
                self.failures = 0
                return json.loads(body) if body else {}
        except urllib.error.HTTPError as exc:
            raw = exc.read().decode("utf-8", errors="replace")
            if exc.code >= 500:
                self.failures += 1
                if self.failures >= 3:
                    self.circuit_open = True
                if self.bus:
                    self.bus.emit("OLLAMA_SERVER_ERROR", "ollama", {"status": exc.code, "path": path, "body": raw[:300]})
                raise OllamaServerError(exc.code, raw) from exc
            raise FailClosed(f"OLLAMA_HTTP:{exc.code}") from exc
        except urllib.error.URLError as exc:
            self.failures += 1
            raise FailClosed(f"OLLAMA_UNAVAILABLE:{exc.reason}") from exc
        except TimeoutError as exc:
            raise FailClosed("OLLAMA_TIMEOUT") from exc

    def health(self) -> dict[str, Any]:
        try:
            self._request("/api/tags")
            return {"ok": True}
        except FailClosed as exc:
            return {"ok": False, "reason": str(exc)}

    def inventory(self) -> dict[str, Any]:
        health = self.health()
        if not health.get("ok"):
            return {"ok": False, "models": [], "main_cortex": CORTEX_TARGET, "teachers": list(TEMPORARY_TEACHERS), "reason": health.get("reason")}
        tags = self._request("/api/tags")
        names = [m.get("name") for m in tags.get("models") or []]
        return {
            "ok": True,
            "models": names,
            "main_cortex_present": any(CORTEX_TARGET in str(n) or "qwen3.6" in str(n) for n in names),
            "teachers_present": {t: any(t.split(":")[0] in str(n) for n in names) for t in TEMPORARY_TEACHERS},
        }

    def classify_http(self, status: int) -> str:
        if status >= 500:
            return "OLLAMA_SERVER_ERROR"
        if status == 404:
            return "OLLAMA_NOT_FOUND"
        if status in {408, 429}:
            return "OLLAMA_RETRYABLE"
        return f"OLLAMA_HTTP_{status}"

    def retry(self, fn, attempts: int = 3) -> Any:
        delay = 0.05
        last = None
        for i in range(attempts):
            try:
                return fn()
            except OllamaServerError as exc:
                last = exc
                time.sleep(delay)
                delay *= 2
        raise last or FailClosed("OLLAMA_RETRY_EXHAUSTED")
