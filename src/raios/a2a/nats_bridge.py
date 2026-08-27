"""A2A does not replace NATS. Reuse existing transport; create no new subjects."""

from __future__ import annotations

from typing import Any

from .flags import HTTP_FALLBACK_PRESERVED, HTTP_PRIMARY, NATS_PRIMARY, NATS_REPLACED

EXISTING_NATS_PROVIDER = "scripts/ai-os/raios_transport/nats_provider.py"


def status() -> dict[str, Any]:
    return {
        "HTTP_PRIMARY": HTTP_PRIMARY,
        "NATS_PRIMARY": NATS_PRIMARY,
        "NATS_REPLACED": NATS_REPLACED,
        "HTTP_FALLBACK_PRESERVED": HTTP_FALLBACK_PRESERVED,
        "EXISTING_NATS_PROVIDER": EXISTING_NATS_PROVIDER,
        "NEW_SUBJECTS_CREATED": False,
    }
