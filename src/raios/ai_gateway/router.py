from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RouteRequest:
    capability: str
    privacy: str = "local_preferred"
    latency: str = "normal"
    cost: str = "bounded"
    tools_required: bool = False
    context_tokens: int = 4096


class ModelRouter:
    def __init__(self, repo: Path, config_path: Path | None = None) -> None:
        self.repo = repo.resolve()
        self.config_path = config_path or self.repo / ".ai-os" / "mcp" / "AI-GATEWAY.json"
        self.ollama_url = os.getenv("RAIOS_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")

    def _load_config(self) -> dict[str, Any]:
        try:
            return json.loads(self.config_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return {"schema": "raios.ai-gateway.v1", "providers": []}

    def _ollama_models(self) -> list[dict[str, Any]]:
        req = urllib.request.Request(self.ollama_url + "/api/tags", method="GET")
        try:
            with urllib.request.urlopen(req, timeout=4) as response:
                body = json.loads(response.read().decode("utf-8", errors="replace"))
        except Exception:
            return []
        out = []
        for row in body.get("models", []):
            name = str(row.get("name") or "")
            if not name:
                continue
            out.append({
                "provider_id": "ollama-local",
                "model_id": name,
                "availability": "LIVE",
                "local": True,
                "cost_class": "LOCAL",
                "privacy_class": "LOCAL_PRIVATE",
                "capabilities": self._infer_local_capabilities(name),
                "context_tokens": 16384,
                "tools": False,
            })
        return out

    @staticmethod
    def _infer_local_capabilities(name: str) -> list[str]:
        value = name.casefold()
        caps = ["general_chat", "summarization", "classification"]
        if "qwen" in value or "deepseek" in value or "granite" in value:
            caps += ["reasoning", "code"]
        return sorted(set(caps))

    def registry(self) -> dict[str, Any]:
        cfg = self._load_config()
        providers = []
        local_models = self._ollama_models()
        providers.extend(local_models)
        for provider in cfg.get("providers", []):
            row = dict(provider)
            row.setdefault("availability", "UNPROVEN")
            row.setdefault("local", False)
            row.setdefault("enabled", False)
            providers.append(row)
        return {
            "schema": "raios.ai-gateway.registry.v1",
            "generated_at": utc(),
            "providers": providers,
            "local_model_count": len(local_models),
            "remote_declared_count": sum(1 for x in providers if not x.get("local")),
            "model_ne_council_seat": True,
            "second_bus_created": False,
        }

    def route(self, request: RouteRequest) -> dict[str, Any]:
        registry = self.registry()
        candidates = []
        for row in registry["providers"]:
            capabilities = set(str(x) for x in row.get("capabilities", []))
            if request.capability not in capabilities:
                continue
            if row.get("availability") != "LIVE":
                continue
            if row.get("enabled") is False and not row.get("local"):
                continue
            if request.privacy in {"local_only", "local_private"} and not row.get("local"):
                continue
            if request.tools_required and not row.get("tools"):
                continue
            if int(row.get("context_tokens") or 0) < int(request.context_tokens):
                continue
            score = 0
            if row.get("local"):
                score += 30 if request.privacy != "cloud_preferred" else 5
            if request.cost == "bounded" and row.get("cost_class") in {"LOCAL", "FREE", "LOW"}:
                score += 20
            if request.latency in {"low", "interactive"} and row.get("local"):
                score += 15
            if request.capability == "reasoning" and "reasoning" in capabilities:
                score += 10
            candidates.append((score, row))

        candidates.sort(key=lambda item: (-item[0], str(item[1].get("model_id") or item[1].get("provider_id"))))
        selected = candidates[0][1] if candidates else None
        return {
            "schema": "raios.ai-gateway.route.v1",
            "generated_at": utc(),
            "request": asdict(request),
            "selected": selected,
            "candidate_count": len(candidates),
            "decision": "ROUTE_SELECTED" if selected else "NO_LIVE_PROVIDER",
            "dispatch_executed": False,
            "provider_mutation": False,
            "model_ne_council_seat": True,
        }
