"""Canonical orchestration package for RAIOS factory capabilities.

Submodules are loaded lazily so importing :mod:`raios.factory_fabric` never probes
resources or initializes runtime state. The public API remains backward compatible.
"""

from __future__ import annotations

from typing import Any

__all__ = ["run_all", "import_factory_estate"]


def __getattr__(name: str) -> Any:
    if name == "run_all":
        from .orchestrator import run_all

        return run_all
    if name == "import_factory_estate":
        from .state_import import import_factory_estate

        return import_factory_estate
    raise AttributeError(name)
