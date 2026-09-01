"""RAIOS live executive manager.

One management loop over the canonical TASKS ledger, existing Command Fabric,
Factory Fabric, Resource Fabric, C5, Cognitive WAL and Evolution Brain.
No second task store, bus, WAL, registry, or authority plane is introduced.
"""
from .live_manager import LiveManager, run_once

__all__ = ["LiveManager", "run_once"]
