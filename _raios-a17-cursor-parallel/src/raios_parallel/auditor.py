"""Reality auditor — anti-self-deception inventory. Never invents state."""
from __future__ import annotations

from typing import Any

from .adapter import NativeCortexBridge
from .identity import CORTEX_TARGET, TEMPORARY_TEACHERS, env_flag
from .models import Discovery


class RealityAuditor:
    def __init__(self, runtime: Any) -> None:
        self.rt = runtime
        self.bridge = runtime.bridge

    def audit(self) -> dict[str, Any]:
        disc = self.bridge.discover()
        identity = self.rt.store.identity()
        knowledge_states = self._count("knowledge_records", "state")
        skill_states = self._count("skills", "lifecycle")
        training_states = self._count("training", "lifecycle")
        mastered = self.rt.store.conn.execute(
            "SELECT COUNT(*) AS n FROM live_sessions WHERE state = 'MASTERED'"
        ).fetchone()["n"]
        retirement_eligible = 0
        teachers = self.rt.store.conn.execute(
            "SELECT DISTINCT teacher_id FROM teacher_capability"
        ).fetchall()
        for row in teachers:
            status = self.rt.retirement.status(row["teacher_id"])
            retirement_eligible += sum(
                1 for cap in status["capabilities"] if cap["decision"] == "RETIREMENT_ELIGIBLE"
            )
        canonical_mutations = self.rt.store.conn.execute(
            "SELECT COUNT(*) AS n FROM governance_actions WHERE allowed = 1 AND action LIKE '%CANONICAL%'"
        ).fetchone()["n"]
        qwen_installed = env_flag("RAIOS_QWEN36_INSTALLED", "")
        return {
            "A17.4_teacher_harvest": disc.get("A17.4", Discovery.MISSING.value),
            "A17.5_assimilation": disc.get("A17.5", Discovery.MISSING.value),
            "A17.6+_live_student": disc.get("A17.6-9", Discovery.MISSING.value),
            "main_cortex_installed": False if qwen_installed.lower() not in {"1", "true", "yes"} else "UNKNOWN",
            "main_cortex_bound": False,
            "main_cortex_target": CORTEX_TARGET,
            "teacher_corps_constitution": list(TEMPORARY_TEACHERS),
            "teachers_still_present": (
                Discovery.PENDING.value
                if disc.get("A17.4") == Discovery.MISSING.value
                else Discovery.FOUND.value
            ),
            "teacher_delete_allowed": False,
            "mastered_capability_count": mastered,
            "teacher_retirement_eligibility_count": retirement_eligible,
            "teacher_dependency": "UNKNOWN",
            "knowledge_state_counts": knowledge_states,
            "skill_state_counts": skill_states,
            "training_candidate_counts": training_states,
            "canonical_mutation_count": canonical_mutations,
            "identity": identity["organism_id"],
            "cortex_is_identity": False,
            "current_blockers": [
                "PENDING_RUNTIME_VALIDATION",
                "QWEN36_INSTALL_NOT_AUTHORIZED",
                "A17_4_HARVEST_ROOT_ABSENT" if disc.get("A17.4") == Discovery.MISSING.value else None,
            ],
            "native_cortex_discovery": disc,
            "invented": False,
        }

    def _count(self, table: str, col: str) -> dict[str, int]:
        rows = self.rt.store.conn.execute(f"SELECT {col} AS k, COUNT(*) AS n FROM {table} GROUP BY {col}").fetchall()
        return {r["k"]: r["n"] for r in rows}
