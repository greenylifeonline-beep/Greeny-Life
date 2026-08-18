"""A19 knowledge plane + knowledge debt."""
from __future__ import annotations

import json
from typing import Any

from ..identity import FailClosed, canonical_json, deterministic_id, sha256_obj, utc_now
from ..models import KnowledgeDebtStatus, KnowledgeState
from ..transitions import assert_debt, assert_knowledge

K_REQUIRED = (
    "claim",
    "conditions",
    "evidence",
    "source",
    "source_version",
    "observed_at",
    "valid_from",
    "valid_until",
    "temporal_class",
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
    "maturity",
    "validation_state",
)

D_REQUIRED = (
    "concept",
    "capabilities",
    "missing_prerequisites",
    "frequency",
    "importance",
    "risk",
    "recommended_sources",
    "required_study",
    "required_practice",
    "required_transfer",
    "priority",
)


INGEST_KINDS = (
    "books",
    "papers",
    "documentation",
    "source_code",
    "repositories",
    "standards",
    "postmortems",
    "experiments",
    "case_studies",
    "teacher_notes",
    "human_notes",
    "model_outputs",
)


class KnowledgeLibrary:
    def __init__(self, store: Any, rkg: Any | None = None) -> None:
        self.store = store
        self.rkg = rkg

    def ingest(self, source: dict[str, Any]) -> dict[str, Any]:
        missing = [k for k in K_REQUIRED if k not in source]
        if missing:
            raise FailClosed("KNOWLEDGE_MISSING:" + ",".join(missing))
        kind = source.get("ingest_kind")
        if kind is not None and kind not in INGEST_KINDS:
            raise FailClosed(f"UNKNOWN_KNOWLEDGE_INGEST_KIND:{kind}")
        knowledge_id = deterministic_id("know", str(source["source"]), str(source["source_version"]), str(source["claim"]))
        existing = self.store.conn.execute(
            "SELECT payload_json FROM knowledge_records WHERE knowledge_id = ?", (knowledge_id,)
        ).fetchone()
        if existing:
            payload = json.loads(existing["payload_json"])
            payload["_idempotent"] = True
            return payload
        payload = {
            **source,
            "knowledge_id": knowledge_id,
            "ingest_kind": kind or source.get("ingest_kind"),
            "state": KnowledgeState.DISCOVERED.value,
            "canonical": False,
            "source_sha256": source.get("source_sha256") or sha256_obj(source),
            "created_at": utc_now(),
            "updated_at": utc_now(),
        }
        self.store.conn.execute(
            """
            INSERT INTO knowledge_records(knowledge_id, state, canonical, payload_json, created_at, updated_at)
            VALUES (?, ?, 0, ?, ?, ?)
            """,
            (knowledge_id, payload["state"], canonical_json(payload), payload["created_at"], payload["updated_at"]),
        )
        self.store.conn.execute(
            "INSERT INTO knowledge_fts(knowledge_id, claim, source) VALUES (?, ?, ?)",
            (knowledge_id, str(source["claim"]), str(source["source"])),
        )
        self.store.append_event("KNOWLEDGE_INGESTED", knowledge_id, {"canonical": False})
        if self.rkg:
            self.rkg.add_node("CLAIM", knowledge_id, {"claim": source["claim"]})
            self.rkg.add_node("SOURCE", str(source["source"]), {"license": source.get("license")})
            self.rkg.add_edge(knowledge_id, str(source["source"]), "LEARNED_FROM")
        return payload

    def transition(self, knowledge_id: str, nxt: KnowledgeState, governed: bool = False) -> dict[str, Any]:
        row = self.store.conn.execute(
            "SELECT payload_json FROM knowledge_records WHERE knowledge_id = ?", (knowledge_id,)
        ).fetchone()
        if not row:
            raise FailClosed("KNOWLEDGE_UNKNOWN")
        payload = json.loads(row["payload_json"])
        snapshot = payload["state"]
        try:
            assert_knowledge(KnowledgeState(payload["state"]), nxt, governed=governed)
        except FailClosed:
            after = json.loads(
                self.store.conn.execute(
                    "SELECT payload_json FROM knowledge_records WHERE knowledge_id = ?", (knowledge_id,)
                ).fetchone()["payload_json"]
            )
            if after["state"] != snapshot:
                raise FailClosed("REJECTED_TRANSITION_MUTATED_STATE")
            raise
        payload["state"] = nxt.value
        payload["updated_at"] = utc_now()
        payload["canonical"] = False
        self.store.conn.execute(
            "UPDATE knowledge_records SET state = ?, payload_json = ?, updated_at = ? WHERE knowledge_id = ?",
            (payload["state"], canonical_json(payload), payload["updated_at"], knowledge_id),
        )
        return payload


class KnowledgeDebtEngine:
    def __init__(self, store: Any) -> None:
        self.store = store

    def create(self, record: dict[str, Any]) -> dict[str, Any]:
        missing = [k for k in D_REQUIRED if k not in record]
        if missing:
            raise FailClosed("KNOWLEDGE_DEBT_MISSING:" + ",".join(missing))
        debt_id = record.get("debt_id") or deterministic_id("kdebt", str(record["concept"]))
        payload = {
            **record,
            "debt_id": debt_id,
            "status": KnowledgeDebtStatus.OPEN.value,
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "distinct_from_learning_debt": True,
        }
        self.store.conn.execute(
            """
            INSERT INTO knowledge_debt(debt_id, concept, status, payload_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(debt_id) DO UPDATE SET payload_json=excluded.payload_json, updated_at=excluded.updated_at
            """,
            (debt_id, record["concept"], payload["status"], canonical_json(payload), payload["created_at"], payload["updated_at"]),
        )
        self.store.append_event("KNOWLEDGE_DEBT_CREATED", debt_id, {"concept": record["concept"]})
        return payload

    def pay(self, debt_id: str, *, reading_only: bool, practice: bool, transfer: bool, validation: bool) -> dict[str, Any]:
        if reading_only or not (practice and transfer and validation):
            raise FailClosed("READING_ALONE_DOES_NOT_PAY_DEBT")
        return self.transition(debt_id, KnowledgeDebtStatus.PAID)

    def transition(self, debt_id: str, nxt: KnowledgeDebtStatus) -> dict[str, Any]:
        row = self.store.conn.execute(
            "SELECT payload_json FROM knowledge_debt WHERE debt_id = ?", (debt_id,)
        ).fetchone()
        if not row:
            raise FailClosed("KNOWLEDGE_DEBT_UNKNOWN")
        payload = json.loads(row["payload_json"])
        if nxt is KnowledgeDebtStatus.PAID:
            # walk is required via assert_debt; paying from OPEN is illegal
            pass
        assert_debt(KnowledgeDebtStatus(payload["status"]), nxt)
        payload["status"] = nxt.value
        payload["updated_at"] = utc_now()
        self.store.conn.execute(
            "UPDATE knowledge_debt SET status = ?, payload_json = ?, updated_at = ? WHERE debt_id = ?",
            (payload["status"], canonical_json(payload), payload["updated_at"], debt_id),
        )
        return payload
