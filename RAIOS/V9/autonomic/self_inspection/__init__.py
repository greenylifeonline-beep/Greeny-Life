"""Self-inspection. Receipts go to .ai-os/receipts, not Cognitive WAL."""
from __future__ import annotations

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
