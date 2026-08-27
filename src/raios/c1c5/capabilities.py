"""Read-only C5 capabilities. No public agent publication."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any, Callable

CAPABILITY_HEALTH = "c5.self_inspect.health"

CONTRACTS: dict[str, dict[str, Any]] = {
    CAPABILITY_HEALTH: {
        "CAPABILITY_ID": CAPABILITY_HEALTH,
        "RISK_CLASS": "LOW",
        "SIDE_EFFECTS": False,
        "PUBLIC_SAFE_SUBSET": False,
        "MODE": "READ_ONLY",
        "REVERSIBLE": True,
    }
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


def invoke(capability_id: str, *, health: HealthFn | None = None) -> dict[str, Any]:
    contract = get_contract(capability_id)
    if capability_id == CAPABILITY_HEALTH:
        fn = health or default_health
        out = fn()
        return {"INVOKED": True, "contract": contract, "result": out}
    raise ValueError(CAPABILITY_NOT_AUTHORIZED)
