"""RAIOS live executive manager.

One management loop over the canonical TASKS ledger, existing Command Fabric,
Factory Fabric, Resource Fabric, C5, Cognitive WAL and Evolution Brain.
No second task store, bus, WAL, registry, or authority plane is introduced.
"""

from __future__ import annotations

from typing import Any

__all__ = ["LiveManager", "run_once"]


def __getattr__(name: str) -> Any:
    """Preserve the public API without importing the executable module twice."""
    if name in __all__:
        from .live_manager import LiveManager, run_once

        return {"LiveManager": LiveManager, "run_once": run_once}[name]
    raise AttributeError(name)
