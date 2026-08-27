"""A2A protocol extensions. Do not fork A2A. AP2 is a hook only."""

from __future__ import annotations

from .flags import AP2_ACTIVATED, AP2_IMPLEMENTED
from .semantic import SEMANTIC_EXTENSION_URI

AP2_EXTENSION_URI = "urn:raios:a2a:ap2-future:v0"


def semantic_extension(*, required: bool) -> dict[str, object]:
    return {
        "uri": SEMANTIC_EXTENSION_URI,
        "description": "RAIOS governed semantic context",
        "required": required,
        "params": {"version": "1"},
    }


def ap2_hook() -> dict[str, object]:
    return {
        "uri": AP2_EXTENSION_URI,
        "description": "Future A2A -> AP2 payment extension. Not implemented.",
        "required": False,
        "params": {
            "AP2_IMPLEMENTED": AP2_IMPLEMENTED,
            "AP2_ACTIVATED": AP2_ACTIVATED,
            "path": "A2A -> future extension -> AP2",
        },
    }
