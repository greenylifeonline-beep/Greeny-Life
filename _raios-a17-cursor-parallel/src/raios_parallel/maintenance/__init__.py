"""A23 autonomic maintenance contracts + degraded modes."""
from __future__ import annotations

from typing import Any

from ..identity import FailClosed, canonical_json, deterministic_id, utc_now
from ..models import DegradedMode


class Maintenance:
    def __init__(self, store: Any, governance: Any) -> None:
        self.store = store
        self.governance = governance

    def observe(self) -> dict[str, Any]:
        integrity = self.store.integrity_check()
        chain = self.store.verify_event_chain()
        return {
            "sqlite_integrity": integrity,
            "wal_events": chain["count"],
            "disk_pressure": "UNKNOWN",
            "model_availability": "UNKNOWN",
            "provider_drift": "UNKNOWN",
            "adapter_regression": "UNKNOWN",
            "knowledge_corruption": "UNKNOWN",
            "broken_dependencies": "UNKNOWN",
            "failed_migrations": "UNKNOWN",
            "stale_leases": "UNKNOWN",
            "orphan_artifacts": "UNKNOWN",
            "hash_mismatches": "UNKNOWN",
        }

    def diagnose(self) -> dict[str, Any]:
        obs = self.observe()
        return {"ok": obs["sqlite_integrity"] == "ok" and obs["wal_events"] >= 0, "observe": obs}

    def quarantine(self, digest: str, reason: str) -> dict[str, Any]:
        qid = deterministic_id("q", digest, reason)
        self.store.conn.execute(
            "INSERT INTO quarantined(quarantine_id, reason, sha256, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (qid, reason, digest, canonical_json({"reason": reason}), utc_now()),
        )
        return {"quarantine_id": qid, "reason": reason}

    def repair_candidate(self, target: str) -> dict[str, Any]:
        return {"target": target, "repair": "CANDIDATE", "auto_applied": False, "canonical": False}

    def rollback_candidate(self, target: str) -> dict[str, Any]:
        return {"target": target, "rollback": "CANDIDATE", "canonical": False}

    def reindex(self) -> dict[str, Any]:
        return {"reindex": "CANDIDATE", "auto_applied": False}

    def compact_candidate(self) -> dict[str, Any]:
        return {"compact": "CANDIDATE", "auto_applied": False}

    def failover(self, provider: str) -> dict[str, Any]:
        return {"failover_to": provider, "identity_preserved": True}

    def enter_degraded(self, mode: DegradedMode | str) -> dict[str, Any]:
        mode = DegradedMode(mode)
        after = self.store.set_mode(mode)
        self.store.append_event("DEGRADED_MODE", mode.value, {"organism_id": after["organism_id"]})
        self.store.conn.execute(
            "INSERT INTO maintenance_events(event_id, action, payload_json, created_at) VALUES (?, ?, ?, ?)",
            (deterministic_id("mnt", mode.value), "degraded_mode", canonical_json({"mode": mode.value}), utc_now()),
        )
        return {"mode": mode.value, "organism_id": after["organism_id"], "identity_survived": True}

    def auto_repair_canonical(self) -> None:
        self.governance.reject("AUTO_REPAIR_CANONICAL")
