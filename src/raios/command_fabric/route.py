"""NATS primary / HTTP fallback for supported internal targets. Does not flip A2A flags."""

from __future__ import annotations

from typing import Any

NATS_SUPPORTED_TARGETS = frozenset({"C5", "C5@AG", "C5-PUBLIC"})
HTTP_FALLBACK = "HTTP"
NATS = "NATS"


def select_transport(*, target: str, nats_available: bool) -> dict[str, Any]:
    target = str(target or "").strip()
    if target in NATS_SUPPORTED_TARGETS and nats_available:
        return {
            "selected_transport": NATS,
            "fallback_transport": HTTP_FALLBACK,
            "route_reason": "SUPPORTED_INTERNAL_TARGET",
            "NATS_PRIMARY_FOR_TARGET": True,
            "HTTP_FALLBACK_PRESERVED": True,
        }
    if target in NATS_SUPPORTED_TARGETS and not nats_available:
        return {
            "selected_transport": HTTP_FALLBACK,
            "fallback_transport": HTTP_FALLBACK,
            "route_reason": "NATS_UNAVAILABLE_HTTP_FALLBACK",
            "NATS_PRIMARY_FOR_TARGET": False,
            "HTTP_FALLBACK_PRESERVED": True,
        }
    return {
        "selected_transport": HTTP_FALLBACK,
        "fallback_transport": HTTP_FALLBACK,
        "route_reason": "TARGET_NOT_NATS_SUPPORTED",
        "NATS_PRIMARY_FOR_TARGET": False,
        "HTTP_FALLBACK_PRESERVED": True,
    }
