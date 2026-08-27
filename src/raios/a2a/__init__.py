"""RAIOS A2A foundation package. External interoperability edge only."""

from .flags import (
    A2A_MODE,
    A2A_PRODUCTION_ACTIVATED,
    A2A_PUBLIC_LISTENER_ENABLED,
    AP2_ACTIVATED,
    AP2_IMPLEMENTED,
)
from .gateway import A2ARequest, Gateway, forbidden_direct_execute

__all__ = [
    "A2ARequest",
    "Gateway",
    "forbidden_direct_execute",
    "A2A_MODE",
    "A2A_PRODUCTION_ACTIVATED",
    "A2A_PUBLIC_LISTENER_ENABLED",
    "AP2_IMPLEMENTED",
    "AP2_ACTIVATED",
]
