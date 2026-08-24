"""Self-inspection. Receipts go to .ai-os/receipts, not Cognitive WAL.

Census *.py files are shims over engine.py. Import inspect from this package.
"""
from __future__ import annotations

# Constants first so engine.py `from . import ACTIONS, CENSUSES` cannot cycle.
ACTIONS = ("KEEP", "MERGE", "ARCHIVE", "DELETE_CANDIDATE", "RESEARCH_REQUIRED", "REPAIR_REQUIRED")
CENSUSES = (
    "tool_census",
    "model_census",
    "duplicate_census",
    "runtime_graph_census",
    "storage_census",
    "health_census",
    "knowledge_gap_census",
    "security_census",
    "neurolingua_census",
    "cloud_capacity_census",
)

from .engine import (  # noqa: E402,F401
    cloud_capacity_census,
    duplicate_census,
    health_census,
    inspect,
    knowledge_gap_census,
    model_census,
    neurolingua_census,
    runtime_graph_census,
    security_census,
    storage_census,
    tool_census,
)
