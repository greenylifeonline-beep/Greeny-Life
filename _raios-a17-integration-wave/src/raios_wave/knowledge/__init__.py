"""A19 Knowledge assimilation & cognitive library + knowledge debt."""
from __future__ import annotations

import json
from typing import Any

from ..identity import FailClosed, canonical_json, deterministic_id, sha256_obj, utc_now
from ..models import AuthorityState, EventType, KnowledgeDebtStatus, KnowledgeState
from ..transitions import assert_knowledge_debt_transition, assert_knowledge_state


class KnowledgeLibrary:
    def __init__(self, store: Any, rkg: Any | None = None) -> None:
        self.store = store
        self.rkg = rkg

    def ingest(self, source: dict[str, Any]) -> dict[str, Any]:
        required = (
            "claim",
            "conditions",
            "evidence",
            "source",
            "version",
            "date",
            "temporal_validity",
            "authority",
            "confidence",
            "examples",
            "counterexamples",
            "contradictions",
            "prerequisites",
            "causal_links",
            "provenance",
            "license",
            "freshness",
        )
        missing = [key for key in required if key not in source]
        if missing:
            raise FailClosed("KNOWLEDGE_MISSING:" + ",".join(missing))
        if source.get("summary_only") and not source.get("claim"):
            raise FailClosed("SUMMARY_ONLY_SOURCE_REJECTED")
        knowledge_id = deterministic_id("know", str(source["source"]), str(source["version"]), str(source["claim"]))
        payload = {
            **source,
            "knowledge_id": knowledge_id,
            "state": KnowledgeState.DISCOVERED.value,
            "authority_state": AuthorityState.CANDIDATE.value,
            "canonical": False,
            "source_sha256": source.get("source_sha256") or sha256_obj(source),
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        existing = self.store.conn.execute(
            "SELECT payload_json FROM knowledge_records WHERE knowledge_id = ?",
            (knowledge_id,),
        ).fetchone()
        if existing:
            payload = json.loads(existing["payload_json"])
            payload["_idempotent"] = True
            return payload
        with self.store.transaction():
            self.store.conn.execute(
                """
                INSERT INTO knowledge_records(
                    knowledge_id, source_sha256, state, authority_state, canonical,
                    payload_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, 0, ?, ?, ?)
                """,
                (
                    knowledge_id,
                    payload["source_sha256"],
                    payload["state"],
                    payload["authority_state"],
                    canonical_json(payload),
                    payload["created_at"],
                    payload["updated_at"],
                ),
            )
            self.store.conn.execute(
                "INSERT INTO knowledge_fts(knowledge_id, claim, source) VALUES (?, ?, ?)",
                (knowledge_id, str(source["claim"]), str(source["source"])),
            )
            self.store.append_event(EventType.KNOWLEDGE_INGESTED, knowledge_id, {"state": payload["state"], "canonical": False})
            if self.rkg:
                self.rkg.add_node("CLAIM", knowledge_id, {"claim": source["claim"]})
                self.rkg.add_node("SOURCE", str(source["source"]), {"license": source.get("license")})
                self.rkg.add_edge(knowledge_id, str(source["source"]), "LEARNED_FROM")
                for contra in source.get("contradictions") or []:
                    cid = contra if isinstance(contra, str) else canonical_json(contra)
                    self.rkg.add_node("CLAIM", str(cid)[:80], {"contradiction": True})
                    self.rkg.add_edge(knowledge_id, str(cid)[:80], "CONTRADICTS")
        return payload

    def transition(self, knowledge_id: str, nxt: KnowledgeState, *, governed_canonical: bool = False) -> dict[str, Any]:
        row = self.store.conn.execute(
            "SELECT payload_json FROM knowledge_records WHERE knowledge_id = ?",
            (knowledge_id,),
        ).fetchone()
        if not row:
            raise FailClosed("KNOWLEDGE_UNKNOWN")
        payload = json.loads(row["payload_json"])
        current = KnowledgeState(payload["state"])
        snapshot = dict(payload)
        try:
            assert_knowledge_state(current, nxt, governed_canonical=governed_canonical)
        except FailClosed:
            after = json.loads(
                self.store.conn.execute(
                    "SELECT payload_json FROM knowledge_records WHERE knowledge_id = ?",
                    (knowledge_id,),
                ).fetchone()["payload_json"]
            )
            if after["state"] != snapshot["state"]:
                raise FailClosed("REJECTED_TRANSITION_MUTATED_STATE")
            raise
        payload["state"] = nxt.value
        payload["updated_at"] = utc_now()
        if nxt is KnowledgeState.CANONICAL:
            raise FailClosed("AUTO_CANONICAL_PROMOTION_REJECTED")
        if nxt is KnowledgeState.VALIDATED:
            payload["authority_state"] = AuthorityState.VALIDATED.value
            payload["canonical"] = False
        self.store.conn.execute(
            "UPDATE knowledge_records SET state = ?, authority_state = ?, payload_json = ?, updated_at = ? WHERE knowledge_id = ?",
            (payload["state"], payload["authority_state"], canonical_json(payload), payload["updated_at"], knowledge_id),
        )
        self.store.append_event(EventType.KNOWLEDGE_STATE_CHANGED, knowledge_id, {"state": payload["state"], "canonical": False})
        return payload

    def search(self, query: str) -> list[dict[str, Any]]:
        rows = self.store.conn.execute(
            "SELECT knowledge_id, claim, source FROM knowledge_fts WHERE knowledge_fts MATCH ? LIMIT 50",
            (query,),
        ).fetchall()
        return [dict(row) for row in rows]


class KnowledgeDebtEngine:
    def __init__(self, store: Any, scheduler: Any | None = None) -> None:
        self.store = store
        self.scheduler = scheduler or SchedulerContract()

    def create(self, *, concept: str, record: dict[str, Any]) -> dict[str, Any]:
        debt_id = deterministic_id("kdebt", concept)
        payload = {
            "debt_id": debt_id,
            "concept": concept,
            "missing_prerequisites": list(record.get("missing_prerequisites") or []),
            "importance": float(record.get("importance") or 0.5),
            "frequency": int(record.get("frequency") or 1),
            "risk": float(record.get("risk") or 0.5),
            "recommended_study_sources": list(record.get("recommended_study_sources") or []),
            "practice_requirements": list(record.get("practice_requirements") or []),
            "transfer_requirements": list(record.get("transfer_requirements") or []),
            "priority": float(record.get("priority") or 0.5),
            "status": KnowledgeDebtStatus.OPEN.value,
            "kind": "KNOWLEDGE_DEBT",
            "distinct_from_learning_debt": True,
        }
        with self.store.transaction():
            self.store.conn.execute(
                """
                INSERT INTO knowledge_debt(
                    debt_id, concept, status, priority, payload_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(debt_id) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """,
                (
                    debt_id,
                    concept,
                    payload["status"],
                    payload["priority"],
                    canonical_json(payload),
                    utc_now(),
                    utc_now(),
                ),
            )
            self.store.append_event(EventType.KNOWLEDGE_DEBT_CREATED, debt_id, {"concept": concept})
            self.scheduler.schedule(payload)
        return payload

    def encounter(self, concept: str, extra: dict[str, Any] | None = None) -> dict[str, Any]:
        row = self.store.conn.execute(
            "SELECT payload_json FROM knowledge_debt WHERE concept = ?",
            (concept,),
        ).fetchone()
        if not row:
            record = extra or {}
            record["frequency"] = 1
            return self.create(concept=concept, record=record)
        payload = json.loads(row["payload_json"])
        payload["frequency"] = int(payload.get("frequency") or 1) + 1
        payload["updated_at"] = utc_now()
        self.store.conn.execute(
            "UPDATE knowledge_debt SET payload_json = ?, updated_at = ? WHERE debt_id = ?",
            (canonical_json(payload), payload["updated_at"], payload["debt_id"]),
        )
        return payload

    def transition(self, debt_id: str, nxt: KnowledgeDebtStatus) -> dict[str, Any]:
        row = self.store.conn.execute(
            "SELECT payload_json FROM knowledge_debt WHERE debt_id = ?",
            (debt_id,),
        ).fetchone()
        if not row:
            raise FailClosed("KNOWLEDGE_DEBT_UNKNOWN")
        payload = json.loads(row["payload_json"])
        current = KnowledgeDebtStatus(payload["status"])
        assert_knowledge_debt_transition(current, nxt)
        payload["status"] = nxt.value
        payload["updated_at"] = utc_now()
        self.store.conn.execute(
            "UPDATE knowledge_debt SET status = ?, payload_json = ?, updated_at = ? WHERE debt_id = ?",
            (payload["status"], canonical_json(payload), payload["updated_at"], debt_id),
        )
        return payload


class SchedulerContract:
    """Stub scheduler interface. Real scheduler integration is out of scope."""

    def schedule(self, debt: dict[str, Any]) -> dict[str, Any]:
        return {"scheduled": False, "reason": "SCHEDULER_NOT_BOUND", "debt_id": debt.get("debt_id")}
