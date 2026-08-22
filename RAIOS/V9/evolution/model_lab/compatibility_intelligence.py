"""Compatibility intelligence. Architecture/size/license gates. No merge yet."""
from __future__ import annotations

from typing import Any


def compatible(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    arch_a = a.get("arch")
    arch_b = b.get("arch")
    size_a = a.get("params")
    size_b = b.get("params")
    same_arch = bool(arch_a and arch_b and arch_a == arch_b)
    size_close = size_a == size_b if size_a and size_b else None
    if not arch_a or not arch_b:
        return {
            "ok": False,
            "reason": "ARCH_UNKNOWN",
            "merge_allowed": False,
            "a": a.get("id"),
            "b": b.get("id"),
        }
    return {
        "ok": same_arch,
        "reason": "SAME_ARCH" if same_arch else "ARCH_MISMATCH",
        "size_close": size_close,
        "merge_allowed": False,
        "note": "Compatibility is a gate. Executor still refuses weight merge here.",
        "a": a.get("id"),
        "b": b.get("id"),
    }
