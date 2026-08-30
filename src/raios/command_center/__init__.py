"""Canonical local RAIOS Command Center with dependency-isolated imports."""
from typing import Any

__all__ = ["app"]

def __getattr__(name: str) -> Any:
    if name == "app":
        from .app import app
        return app
    raise AttributeError(name)
