"""RAIOS Resource Fabric. Separate from frozen precanonical command fabric."""

from .schema import SCHEMA, UNKNOWN, EXISTING_LEASE_SYSTEM
from .adapters import ADAPTERS
from .census import collect_world, run_safe_probes, snapshots
from .live import bind_live_accounts
from .factory import place, plan_dispatch, reservoir_view, resource_request
from .c5_awareness import reason as c5_reason, resource_context
from .integration import execute_governed_local_control, unified_resource_registry
from .executable_adapters import (
    ADAPTERS as EXECUTABLE_ADAPTERS,
    ProviderGateError,
    ProviderProof,
    ProviderRequest,
    build_executable_adapter,
)

__all__ = [
    "SCHEMA",
    "UNKNOWN",
    "EXISTING_LEASE_SYSTEM",
    "ADAPTERS",
    "collect_world",
    "run_safe_probes",
    "snapshots",
    "bind_live_accounts",
    "place",
    "plan_dispatch",
    "reservoir_view",
    "resource_request",
    "c5_reason",
    "resource_context",
    "execute_governed_local_control",
    "unified_resource_registry",
    "EXECUTABLE_ADAPTERS",
    "ProviderGateError",
    "ProviderProof",
    "ProviderRequest",
    "build_executable_adapter",
]
