"""RAIOS A2A foundation package. External interoperability edge only.

Gateway symbols are lazy so internal receipt/presence code does not require the
optional external A2A SDK merely by importing a submodule.
"""

from .flags import (
    A2A_MODE,
    A2A_PRODUCTION_ACTIVATED,
    A2A_PUBLIC_LISTENER_ENABLED,
    AP2_ACTIVATED,
    AP2_IMPLEMENTED,
)

_GATEWAY_EXPORTS = {"A2ARequest", "Gateway", "forbidden_direct_execute"}


def __getattr__(name):
    if name in _GATEWAY_EXPORTS:
        from . import gateway
        return getattr(gateway, name)
    raise AttributeError(name)

__all__ = [
    "A2ARequest", "Gateway", "forbidden_direct_execute",
    "A2A_MODE", "A2A_PRODUCTION_ACTIVATED", "A2A_PUBLIC_LISTENER_ENABLED",
    "AP2_IMPLEMENTED", "AP2_ACTIVATED",
]
