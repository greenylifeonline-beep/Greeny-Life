"""Required execution path. There is no A2A_REQUEST -> EXECUTE shortcut."""

from __future__ import annotations

from typing import Any

PATH = (
    "A2A Request",
    "Identity",
    "Authentication",
    "Semantic normalization",
    "Capability resolution",
    "Policy",
    "Risk classification",
    "RAIOS Intent",
    "Plan",
    "Authority Gate when required",
    "Unified Control Plane",
    "Execution",
    "Verification",
    "Receipt",
    "A2A Task Result / Artifact",
)


def run(gateway: Any, request: Any) -> dict:
    return gateway.handle(request)
