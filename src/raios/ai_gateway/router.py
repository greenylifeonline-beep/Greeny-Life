from __future__ import annotations

import json
import os
import re
import subprocess
import urllib.request
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .http_dispatch import (
    load_deepseek_api_key,
    load_lightning_api_key,
    ollama_chat,
    openai_compatible_chat,
)
from .traces import append_call_trace, response_hash


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


class BudgetExceeded(RuntimeError):
    """Raised when estimated cost exceeds RAIOS_AI_GATEWAY_MAX_COST_USD."""


class ModelRouter:
    def __init__(self, repo: Path, config_path: Path | None = None) -> None:
        self.repo = repo.resolve()
        self.config_path = config_path or self.repo / ".ai-os" / "mcp" / "AI-GATEWAY.json"
        self.ollama_url = os.getenv("RAIOS_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")

    def _load_config(self) -> dict[str, Any]:
        try:
            return json.loads(self.config_path.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError):
            return {"schema": "raios.ai-gateway.v1", "providers": [], "task_class_routing": {}}

    def _canonical_head(self) -> str:
        try:
            proc = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=str(self.repo),
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if proc.returncode == 0:
                return (proc.stdout or "").strip() or "UNKNOWN"
        except Exception:
            pass
        return "UNKNOWN"

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
            provider_id = "ollama-local-" + re.sub(r"[^a-z0-9]+", "-", name.casefold()).strip("-")
            out.append({
                "provider_id": provider_id,
                "model_id": name,
                "availability": "LIVE",
                "enabled": True,
                "local": True,
                "cost_class": "LOCAL",
                "privacy_class": "LOCAL_PRIVATE",
                "deployment_location": "local-ollama",
                "cascade_tier": "local",
                "capabilities": self._infer_local_capabilities(name),
                "context_tokens": 16384,
                "tools": False,
                "protocol": "ollama_chat",
            })
        return out

    @staticmethod
    def _infer_local_capabilities(name: str) -> list[str]:
        value = name.casefold()
        if "embedding" in value or "embed" in value:
            return ["embedding"]
        caps = ["general_chat", "summarization", "classification", "routing", "health"]
        if "qwen" in value or "deepseek" in value or "granite" in value:
            caps.append("reasoning")
        if "coder" in value or "code" in value or "qwen" in value or "deepseek" in value or "granite" in value:
            caps.append("code")
        return sorted(set(caps))

    def _merge_declared_with_live(self, cfg: dict[str, Any], live_local: list[dict[str, Any]]) -> list[dict[str, Any]]:
        live_names = {str(x.get("model_id") or "") for x in live_local}
        providers: list[dict[str, Any]] = []
        for provider in cfg.get("providers", []):
            row = dict(provider)
            if row.get("deprecated"):
                providers.append(row)
                continue
            model_id = str(row.get("model_id") or "")
            if row.get("local") and model_id and any(
                name == model_id or name.startswith(model_id + ":") or name.startswith(model_id)
                for name in live_names
            ):
                # Exact or tag family match (e.g. qwen3:0.6b / qwen3:0.6b-...)
                matched = next(
                    (n for n in live_names if n == model_id or n.startswith(model_id)),
                    model_id,
                )
                row["model_id"] = matched if matched in live_names else model_id
                if any(n == model_id or n.startswith(model_id) for n in live_names):
                    exact = model_id in live_names or any(n.split(":")[0:2] and n == model_id for n in live_names)
                    if model_id in live_names or any(n == model_id for n in live_names):
                        row["availability"] = "LIVE"
                        row["enabled"] = True
                    elif any(n.startswith(model_id) for n in live_names):
                        row["availability"] = "LIVE"
                        row["enabled"] = True
            providers.append(row)
        # Keep dynamic ollama discovery for models not declared as tier providers.
        declared_local_ids = {
            str(p.get("model_id") or "") for p in providers if p.get("local")
        }
        for live in live_local:
            mid = str(live.get("model_id") or "")
            if mid in declared_local_ids or any(mid.startswith(d) for d in declared_local_ids if d):
                continue
            providers.append(live)
        return providers

    def registry(self) -> dict[str, Any]:
        cfg = self._load_config()
        local_models = self._ollama_models()
        providers = self._merge_declared_with_live(cfg, local_models)
        return {
            "schema": "raios.ai-gateway.registry.v1",
            "generated_at": utc(),
            "providers": providers,
            "local_model_count": len(local_models),
            "remote_declared_count": sum(1 for x in providers if not x.get("local")),
            "model_ne_council_seat": True,
            "second_bus_created": False,
            "task_class_routing": cfg.get("task_class_routing") or {},
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

    def _privacy_allows_remote(self, privacy_class: str) -> bool:
        value = (privacy_class or "").casefold()
        if value in {"local_only", "local_private", "confidential", "private"}:
            return False
        return value in {"cloud_ok", "cloud_preferred", "public", "local_preferred", ""}

    def _provider_by_id(self, providers: list[dict[str, Any]], provider_id: str) -> dict[str, Any] | None:
        for row in providers:
            if str(row.get("provider_id") or "") == provider_id:
                return row
        return None

    def _live_usable(self, row: dict[str, Any] | None, *, allow_remote: bool) -> bool:
        if not row:
            return False
        if row.get("deprecated"):
            return False
        if row.get("availability") != "LIVE":
            return False
        if row.get("enabled") is False:
            return False
        if not row.get("local") and not allow_remote:
            return False
        return True

    def _cascade_provider_ids(
        self,
        task_class: str,
        cfg: dict[str, Any],
        *,
        privacy_class: str = "local_preferred",
    ) -> list[str]:
        routing = (cfg.get("task_class_routing") or {}).get(str(task_class).upper()) or {}
        preferred = [str(x) for x in routing.get("preferred") or []]
        # Default C1 cascade order: local → qwen cloud → deepseek flash → deepseek pro
        default = [
            "ollama-local-qwen3-0.6b",
            "ollama-local-deepseek-r1-1.5b",
            "lightning-qwen-3.8-27b",
            "deepseek-v4-flash",
            "deepseek-v4-pro",
        ]
        tc = str(task_class).upper()
        privacy = (privacy_class or "").casefold()
        if tc in {"HEALTH", "ROUTING", "CLASSIFICATION"}:
            base = [p for p in preferred + default if p.startswith("ollama-local")]
        elif tc in {"HARD_ARCHITECTURE", "CRITICAL_REVIEW"}:
            # Preferred heavy reasoner first, then remainder of default cascade.
            base = preferred + default
        elif privacy == "cloud_preferred":
            # Cloud-preferred chat: qwen → flash → pro → local fallback.
            base = [
                "lightning-qwen-3.8-27b",
                "deepseek-v4-flash",
                "deepseek-v4-pro",
                "ollama-local-qwen3-0.6b",
                "ollama-local-deepseek-r1-1.5b",
            ]
        else:
            base = default
        ordered: list[str] = []
        for pid in base:
            if pid not in ordered:
                ordered.append(pid)
        return ordered

    def estimate_cost_usd(self, provider: dict[str, Any], *, input_tokens: int = 0, output_tokens: int = 0) -> float:
        cfg = self._load_config()
        defaults = ((cfg.get("cost_guards") or {}).get("default_cost_estimate_usd") or {})
        pid = str(provider.get("provider_id") or "")
        base = float(defaults.get(pid, defaults.get(str(provider.get("cascade_tier") or ""), 0.0)) or 0.0)
        # Tiny token-proportional bump for API tiers (still mocked-safe).
        if provider.get("cost_class") in {"LOW", "MEDIUM", "HIGH"}:
            base += (max(0, int(input_tokens)) + max(0, int(output_tokens))) * 1e-6
        if provider.get("local") or provider.get("cost_class") in {"LOCAL", "FREE"}:
            return 0.0
        return round(base, 8)

    def check_cost_guard(self, cost_estimate: float) -> None:
        raw = os.environ.get("RAIOS_AI_GATEWAY_MAX_COST_USD")
        if raw is None or str(raw).strip() == "":
            return
        try:
            budget = float(raw)
        except ValueError:
            return
        if float(cost_estimate) > budget:
            raise BudgetExceeded(
                f"cost_estimate={cost_estimate} exceeds RAIOS_AI_GATEWAY_MAX_COST_USD={budget}"
            )

    def route_for_task_class(
        self,
        task_class: str,
        privacy_class: str = "local_preferred",
        *,
        seat: str = "C5",
        task_id: str | None = None,
        dispatch: bool = False,
        messages: list[dict[str, str]] | None = None,
        max_tokens: int = 64,
    ) -> dict[str, Any]:
        cfg = self._load_config()
        registry = self.registry()
        providers = list(registry.get("providers") or [])
        allow_remote = self._privacy_allows_remote(privacy_class)
        ordered_ids = self._cascade_provider_ids(task_class, cfg, privacy_class=privacy_class)
        # Append dynamically discovered local chat/code providers without replacing
        # the explicit C1 preference order. Embedding-only models never enter chat routing.
        tc = str(task_class).upper()
        required_capability = "code" if tc == "CODE" else "reasoning" if tc in {"COMPLEX_REASONING", "HARD_ARCHITECTURE", "CRITICAL_REVIEW"} else "general_chat"
        dynamic_local_ids = [
            str(row.get("provider_id") or "")
            for row in providers
            if row.get("local")
            and row.get("availability") == "LIVE"
            and row.get("enabled") is not False
            and required_capability in set(str(x) for x in row.get("capabilities", []))
        ]
        for provider_id in dynamic_local_ids:
            if provider_id and provider_id not in ordered_ids:
                ordered_ids.append(provider_id)
        attempts: list[dict[str, Any]] = []
        selected: dict[str, Any] | None = None
        fallback_reason: str | None = None
        head = self._canonical_head()

        for provider_id in ordered_ids:
            row = self._provider_by_id(providers, provider_id)
            usable = self._live_usable(row, allow_remote=allow_remote)
            capability_ok = bool(row and required_capability in set(str(x) for x in row.get("capabilities", [])))
            usable = usable and capability_ok
            attempts.append({
                "provider_id": provider_id,
                "usable": usable,
                "required_capability": required_capability,
                "capability_ok": capability_ok,
                "availability": (row or {}).get("availability"),
                "enabled": (row or {}).get("enabled"),
                "local": (row or {}).get("local"),
            })
            if not usable:
                if row is None:
                    fallback_reason = f"{provider_id}:NOT_DECLARED"
                elif row.get("availability") != "LIVE" or row.get("enabled") is False:
                    fallback_reason = f"{provider_id}:UNPROVEN_OR_DISABLED"
                elif not row.get("local") and not allow_remote:
                    fallback_reason = f"{provider_id}:PRIVACY_BLOCKS_REMOTE"
                elif not capability_ok:
                    fallback_reason = f"{provider_id}:CAPABILITY_MISMATCH"
                else:
                    fallback_reason = f"{provider_id}:SKIPPED"
                continue
            selected = row
            break

        if selected is None:
            result = {
                "schema": "raios.ai-gateway.task-route.v1",
                "generated_at": utc(),
                "task_class": str(task_class).upper(),
                "privacy_class": privacy_class,
                "decision": "NO_LIVE_PROVIDER",
                "selected": None,
                "cascade": ordered_ids,
                "attempts": attempts,
                "fallback_reason": fallback_reason or "CASCADE_EXHAUSTED",
                "dispatch_executed": False,
                "seat": seat,
                "task_id": task_id,
                "canonical_head": head,
                "model_ne_council_seat": True,
                "second_bus_created": False,
            }
            append_call_trace(self.repo, {
                "seat": seat,
                "task_id": task_id,
                "provider": None,
                "model_id": None,
                "deployment_location": None,
                "request_class": str(task_class).upper(),
                "privacy_class": privacy_class,
                "input_tokens": 0,
                "output_tokens": 0,
                "latency_ms": 0,
                "cost_estimate": 0.0,
                "fallback_reason": result["fallback_reason"],
                "canonical_head": head,
                "response_hash": response_hash(""),
                "ok": False,
                "decision": result["decision"],
                "dispatch_executed": False,
            })
            return result

        cost_estimate = self.estimate_cost_usd(selected)
        try:
            self.check_cost_guard(cost_estimate)
        except BudgetExceeded as exc:
            append_call_trace(self.repo, {
                "seat": seat,
                "task_id": task_id,
                "provider": selected.get("provider_id"),
                "model_id": selected.get("model_id"),
                "deployment_location": selected.get("deployment_location"),
                "request_class": str(task_class).upper(),
                "privacy_class": privacy_class,
                "input_tokens": 0,
                "output_tokens": 0,
                "latency_ms": 0,
                "cost_estimate": cost_estimate,
                "fallback_reason": "COST_GUARD_REFUSED",
                "canonical_head": head,
                "response_hash": response_hash(""),
                "ok": False,
                "decision": "COST_GUARD_REFUSED",
                "dispatch_executed": False,
                "error": str(exc),
            })
            return {
                "schema": "raios.ai-gateway.task-route.v1",
                "generated_at": utc(),
                "task_class": str(task_class).upper(),
                "privacy_class": privacy_class,
                "decision": "COST_GUARD_REFUSED",
                "selected": selected,
                "cascade": ordered_ids,
                "attempts": attempts,
                "fallback_reason": "COST_GUARD_REFUSED",
                "dispatch_executed": False,
                "cost_estimate": cost_estimate,
                "seat": seat,
                "task_id": task_id,
                "canonical_head": head,
                "error": str(exc),
                "model_ne_council_seat": True,
                "second_bus_created": False,
            }

        dispatch_result: dict[str, Any] | None = None
        if dispatch:
            dispatch_result = self.dispatch_chat(
                selected,
                messages=messages or [{"role": "user", "content": "."}],
                max_tokens=max_tokens,
                seat=seat,
                task_id=task_id,
                request_class=str(task_class).upper(),
                privacy_class=privacy_class,
                fallback_reason=fallback_reason,
            )

        return {
            "schema": "raios.ai-gateway.task-route.v1",
            "generated_at": utc(),
            "task_class": str(task_class).upper(),
            "privacy_class": privacy_class,
            "decision": "ROUTE_SELECTED",
            "selected": selected,
            "cascade": ordered_ids,
            "attempts": attempts,
            "fallback_reason": fallback_reason,
            "dispatch_executed": bool(dispatch_result and dispatch_result.get("dispatch_executed")),
            "dispatch": dispatch_result,
            "cost_estimate": cost_estimate,
            "seat": seat,
            "task_id": task_id,
            "canonical_head": head,
            "model_ne_council_seat": True,
            "second_bus_created": False,
        }

    def mark_provider_live(self, provider_id: str, *, proven: bool) -> None:
        """Update config availability after honest live proof. Never stores secrets."""
        cfg = self._load_config()
        changed = False
        for row in cfg.get("providers", []):
            if str(row.get("provider_id") or "") != provider_id:
                continue
            if proven:
                row["availability"] = "LIVE"
                row["enabled"] = True
            else:
                row["availability"] = "UNPROVEN"
                row["enabled"] = False
            changed = True
            break
        if changed:
            self.config_path.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")

    def dispatch_chat(
        self,
        provider: dict[str, Any],
        *,
        messages: list[dict[str, str]],
        max_tokens: int = 64,
        seat: str = "C5",
        task_id: str | None = None,
        request_class: str = "NORMAL_CHAT",
        privacy_class: str = "local_preferred",
        fallback_reason: str | None = None,
    ) -> dict[str, Any]:
        import time

        if os.environ.get("RAIOS_AI_GATEWAY_ALLOW_OLLAMA_PULL", "").strip() in {"1", "true", "TRUE"}:
            # Explicitly ignore — weight download / ollama pull is forbidden by C1.
            pass

        cost_estimate = self.estimate_cost_usd(provider)
        self.check_cost_guard(cost_estimate)
        head = self._canonical_head()
        started = time.perf_counter()
        content = ""
        http_status = None
        ok = False
        error = None
        in_tok = sum(len(str(m.get("content") or "").split()) for m in messages)
        out_tok = 0

        protocol = str(provider.get("protocol") or "")
        model_id = str(provider.get("model_id") or "")
        try:
            if protocol == "ollama_chat" or provider.get("local"):
                result = ollama_chat(
                    base_url=self.ollama_url,
                    model=model_id,
                    messages=messages,
                    num_predict=max_tokens,
                )
                http_status = result.get("http")
                body = result.get("json") if isinstance(result.get("json"), dict) else {}
                content = str(((body or {}).get("message") or {}).get("content") or "")
                ok = bool(result.get("ok") and content)
                error = result.get("error")
            elif protocol == "openai_chat_completions":
                pid = str(provider.get("provider_id") or "")
                if pid.startswith("lightning"):
                    api_key = load_lightning_api_key()
                    if not api_key:
                        raise RuntimeError("LIGHTNING_API_KEY_MISSING")
                    endpoint = str(provider.get("endpoint") or "https://lightning.ai/api/v1/chat/completions")
                elif "deepseek" in pid:
                    api_key = load_deepseek_api_key()
                    if not api_key:
                        raise RuntimeError("DEEPSEEK_API_KEY_MISSING")
                    endpoint = str(provider.get("endpoint") or "https://api.deepseek.com/chat/completions")
                else:
                    raise RuntimeError(f"UNSUPPORTED_PROVIDER:{pid}")
                result = openai_compatible_chat(
                    endpoint=endpoint,
                    api_key=api_key,
                    model=model_id,
                    messages=messages,
                    max_tokens=max_tokens,
                )
                # Drop local reference immediately.
                api_key = ""
                http_status = result.get("http")
                body = result.get("json") if isinstance(result.get("json"), dict) else {}
                choices = (body or {}).get("choices") or []
                if choices and isinstance(choices[0], dict):
                    content = str(((choices[0].get("message") or {}).get("content")) or "")
                usage = (body or {}).get("usage") if isinstance(body, dict) else {}
                if isinstance(usage, dict):
                    in_tok = int(usage.get("prompt_tokens") or in_tok or 0)
                    out_tok = int(usage.get("completion_tokens") or 0)
                ok = bool(result.get("ok") and (content or choices))
                error = result.get("error")
            else:
                raise RuntimeError(f"UNSUPPORTED_PROTOCOL:{protocol}")
        except BudgetExceeded:
            raise
        except Exception as exc:
            ok = False
            error = str(exc)
            # Never include secret material in error strings.
            if any(s in error.casefold() for s in ("bearer", "api_key", "sk-")):
                error = type(exc).__name__

        latency_ms = int((time.perf_counter() - started) * 1000)
        if not out_tok and content:
            out_tok = len(content.split())
        cost_estimate = self.estimate_cost_usd(provider, input_tokens=in_tok, output_tokens=out_tok)

        trace = {
            "seat": seat,
            "task_id": task_id,
            "provider": provider.get("provider_id"),
            "model_id": model_id,
            "deployment_location": provider.get("deployment_location"),
            "request_class": request_class,
            "privacy_class": privacy_class,
            "input_tokens": in_tok,
            "output_tokens": out_tok,
            "latency_ms": latency_ms,
            "cost_estimate": cost_estimate,
            "fallback_reason": fallback_reason,
            "canonical_head": head,
            "response_hash": response_hash(content),
            "ok": ok,
            "decision": "DISPATCH_OK" if ok else "DISPATCH_FAILED",
            "dispatch_executed": True,
            "http_status": http_status,
            "error": error,
        }
        append_call_trace(self.repo, trace)
        return {
            "schema": "raios.ai-gateway.dispatch.v1",
            "ok": ok,
            "content": content if ok else "",
            "dispatch_executed": True,
            "http_status": http_status,
            "error": error,
            "latency_ms": latency_ms,
            "cost_estimate": cost_estimate,
            "response_hash": trace["response_hash"],
            "provider": provider.get("provider_id"),
            "model_id": model_id,
            # Explicit non-actions:
            "ollama_pull_executed": False,
            "weight_download_executed": False,
        }
