"""Read-only C5 capabilities. No public agent publication."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Callable

CAPABILITY_HEALTH = "c5.self_inspect.health"
CAPABILITY_HANGING = "raios.system.hanging_work"
CAPABILITY_ECOLOGY = "raios.system.model_ecology"

_READ_ONLY = {
    "RISK_CLASS": "LOW",
    "SIDE_EFFECTS": False,
    "PUBLIC_SAFE_SUBSET": False,
    "MODE": "READ_ONLY",
    "REVERSIBLE": True,
}

CONTRACTS: dict[str, dict[str, Any]] = {
    CAPABILITY_HEALTH: {"CAPABILITY_ID": CAPABILITY_HEALTH, **_READ_ONLY},
    CAPABILITY_HANGING: {"CAPABILITY_ID": CAPABILITY_HANGING, **_READ_ONLY},
    CAPABILITY_ECOLOGY: {"CAPABILITY_ID": CAPABILITY_ECOLOGY, **_READ_ONLY},
}

UNKNOWN_CAPABILITY = "UNKNOWN_CAPABILITY"
CAPABILITY_NOT_AUTHORIZED = "CAPABILITY_NOT_AUTHORIZED"

HealthFn = Callable[[], dict[str, Any]]


def get_contract(capability_id: str) -> dict[str, Any]:
    if capability_id not in CONTRACTS:
        raise ValueError(UNKNOWN_CAPABILITY)
    return dict(CONTRACTS[capability_id])


def default_health() -> dict[str, Any]:
    request = urllib.request.Request("http://127.0.0.1:8766/health")
    try:
        with urllib.request.urlopen(request, timeout=4) as response:
            body = json.loads(response.read().decode("utf-8-sig"))
            return {"LIVE": response.status == 200, "http_status": response.status, "body": body}
    except urllib.error.URLError as exc:
        return {"LIVE": False, "http_status": 0, "error": str(exc)}
    except Exception as exc:
        return {"LIVE": False, "http_status": 0, "error": f"{type(exc).__name__}:{exc}"}


def _hanging_work() -> dict[str, Any]:
    from pathlib import Path

    from raios.command_center.board_now import hanging_work

    root = Path(__file__).resolve().parents[3]
    path = root / ".ai-os" / "state" / "TASKS.json"
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        return {"LIVE": False, "error": f"{type(exc).__name__}:{exc}"}
    tasks = doc.get("tasks") if isinstance(doc, dict) else []
    out = hanging_work(tasks if isinstance(tasks, list) else [])
    out["LIVE"] = True
    return out


def _model_ecology() -> dict[str, Any]:
    from raios.factory_fabric.orchestrator import model_ecology_probe

    out = model_ecology_probe()
    out["LIVE"] = str(out.get("status") or "").upper() == "PASS"
    return out


def invoke(capability_id: str, *, health: HealthFn | None = None) -> dict[str, Any]:
    contract = get_contract(capability_id)
    if capability_id == CAPABILITY_HEALTH:
        fn = health or default_health
        out = fn()
        return {"INVOKED": True, "contract": contract, "result": out}
    if capability_id == CAPABILITY_HANGING:
        return {"INVOKED": True, "contract": contract, "result": _hanging_work()}
    if capability_id == CAPABILITY_ECOLOGY:
        return {"INVOKED": True, "contract": contract, "result": _model_ecology()}
    raise ValueError(CAPABILITY_NOT_AUTHORIZED)
