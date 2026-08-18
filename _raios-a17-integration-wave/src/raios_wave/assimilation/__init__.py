"""A17.5 Teacher output normalization.

Consumes harvest artifacts into TeacherObservation records. Teacher self-claims
remain UNVERIFIED and never become canonical. Malformed artifacts are
quarantined. Duplicate source hashes are idempotent. Hash mismatches fail closed.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..identity import FailClosed, canonical_json, deterministic_id, require_sha256, sha256_bytes, utc_now
from ..models import (
    EventType,
    EvidenceState,
    TeacherObservation,
    VerificationState,
    to_jsonable,
)

SECTION_PATTERNS = {
    "claims": re.compile(r"^(?:claim|claims)\s*[:\-]\s*(.+)$", re.I),
    "procedures": re.compile(r"^(?:procedure|step|steps)\s*[:\-]\s*(.+)$", re.I),
    "heuristics": re.compile(r"^(?:heuristic|rule)\s*[:\-]\s*(.+)$", re.I),
    "failure_patterns": re.compile(r"^(?:failure|fail)\s*[:\-]\s*(.+)$", re.I),
    "recovery_patterns": re.compile(r"^(?:recovery|recover)\s*[:\-]\s*(.+)$", re.I),
    "tool_strategies": re.compile(r"^(?:tool|tools)\s*[:\-]\s*(.+)$", re.I),
    "examples": re.compile(r"^(?:example)\s*[:\-]\s*(.+)$", re.I),
    "counterexamples": re.compile(r"^(?:counterexample)\s*[:\-]\s*(.+)$", re.I),
    "transfer_test_candidates": re.compile(r"^(?:transfer)\s*[:\-]\s*(.+)$", re.I),
    "skill_candidates": re.compile(r"^(?:skill)\s*[:\-]\s*(.+)$", re.I),
    "training_candidates": re.compile(r"^(?:training)\s*[:\-]\s*(.+)$", re.I),
    "uncertainties": re.compile(r"^(?:uncertain(?:ty|ties)?|unknown)\s*[:\-]\s*(.+)$", re.I),
    "self_reported_claims": re.compile(r"^(?:self[- ]?report|i (?:am|can)|confidence)\s*[:\-]\s*(.+)$", re.I),
}

REQUIRED_FIELDS = ("teacher_id", "model", "task_id", "capability")


class Normalizer:
    def __init__(self, store: Any) -> None:
        self.store = store

    def normalize_artifact(self, artifact: dict[str, Any] | str | Path) -> dict[str, Any]:
        try:
            parsed = self._parse(artifact)
            self._validate(parsed)
            raw_text = parsed.get("raw_text") or parsed.get("output") or ""
            raw_bytes = raw_text.encode("utf-8") if isinstance(raw_text, str) else bytes(raw_text)
            observed_hash = sha256_bytes(raw_bytes if raw_bytes else canonical_json(parsed).encode("utf-8"))
            declared = parsed.get("source_sha256")
            if declared:
                declared = require_sha256(declared, "SOURCE_SHA256")
                if declared != observed_hash:
                    raise FailClosed("SOURCE_HASH_MISMATCH")
            source_sha256 = declared or observed_hash
            teacher_id = str(parsed["teacher_id"])
            task_id = str(parsed["task_id"])
            capability = str(parsed["capability"])
            observation_id = deterministic_id("obs", teacher_id, source_sha256, task_id, capability)
            existing = self.store.conn.execute(
                "SELECT payload_json FROM observations WHERE observation_id = ?",
                (observation_id,),
            ).fetchone()
            if existing:
                self.store.append_event(
                    EventType.OBSERVATION_IDEMPOTENT_HIT,
                    observation_id,
                    {"source_sha256": source_sha256},
                )
                payload = json.loads(existing["payload_json"])
                payload["_idempotent"] = True
                return payload
            extracted = self._extract(parsed, raw_text if isinstance(raw_text, str) else raw_text.decode("utf-8", "replace"))
            raw_ref = f"artifact://sha256/{self.store.put_bytes(raw_bytes if raw_bytes else canonical_json(parsed).encode('utf-8'))}"
            source_artifact = str(parsed.get("source_artifact") or parsed.get("path") or f"inline:{source_sha256[:12]}")
            observation = TeacherObservation(
                observation_id=observation_id,
                teacher_id=teacher_id,
                model=str(parsed["model"]),
                task_id=task_id,
                capability=capability,
                source_artifact=source_artifact,
                source_sha256=source_sha256,
                raw_text_ref=raw_ref,
                observed_at=str(parsed.get("observed_at") or utc_now()),
                claims=tuple(extracted["claims"]),
                procedures=tuple(extracted["procedures"]),
                heuristics=tuple(extracted["heuristics"]),
                failure_patterns=tuple(extracted["failure_patterns"]),
                recovery_patterns=tuple(extracted["recovery_patterns"]),
                tool_strategies=tuple(extracted["tool_strategies"]),
                examples=tuple(extracted["examples"]),
                counterexamples=tuple(extracted["counterexamples"]),
                transfer_test_candidates=tuple(extracted["transfer_test_candidates"]),
                skill_candidates=tuple(extracted["skill_candidates"]),
                training_candidates=tuple(extracted["training_candidates"]),
                uncertainties=tuple(extracted["uncertainties"]),
                self_reported_claims=tuple(extracted["self_reported_claims"]),
                evidence_state=EvidenceState.HASH_BOUND,
                verification_state=VerificationState.UNVERIFIED,
                canonical=False,
            ).sealed()
            payload = to_jsonable(observation.stable_payload())
            payload["content_sha256"] = observation.content_sha256
            payload["self_report_authority"] = "LOWER_THAN_EMPIRICAL"
            payload["canonical"] = False
            with self.store.transaction():
                self.store.conn.execute(
                    """
                    INSERT INTO observations(
                        observation_id, teacher_id, model, task_id, capability,
                        source_sha256, content_sha256, verification_state, canonical,
                        payload_json, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
                    """,
                    (
                        observation.observation_id,
                        observation.teacher_id,
                        observation.model,
                        observation.task_id,
                        observation.capability,
                        observation.source_sha256,
                        observation.content_sha256,
                        observation.verification_state.value,
                        canonical_json(payload),
                        observation.observed_at,
                    ),
                )
                self.store.append_event(
                    EventType.OBSERVATION_NORMALIZED,
                    observation.observation_id,
                    {
                        "teacher_id": teacher_id,
                        "source_sha256": source_sha256,
                        "verification_state": VerificationState.UNVERIFIED.value,
                    },
                )
            payload["_idempotent"] = False
            return payload
        except FailClosed as exc:
            return self._quarantine(artifact, str(exc))
        except (OSError, json.JSONDecodeError, UnicodeError, TypeError, KeyError, ValueError) as exc:
            return self._quarantine(artifact, f"MALFORMED_ARTIFACT:{type(exc).__name__}")

    def _parse(self, artifact: dict[str, Any] | str | Path) -> dict[str, Any]:
        if isinstance(artifact, dict):
            return dict(artifact)
        path = Path(artifact)
        if path.is_dir():
            return self._parse_directory(path)
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".json":
            data = json.loads(text)
            if not isinstance(data, dict):
                raise FailClosed("MALFORMED_ARTIFACT:NON_OBJECT")
            data.setdefault("source_artifact", str(path))
            return data
        return {"raw_text": text, "source_artifact": str(path)}

    def _parse_directory(self, path: Path) -> dict[str, Any]:
        meta_path = path / "meta.json"
        if not meta_path.is_file():
            raise FailClosed("MALFORMED_ARTIFACT:MISSING_META")
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if not isinstance(meta, dict):
            raise FailClosed("MALFORMED_ARTIFACT:META_NON_OBJECT")
        output_path = path / "output.txt"
        if output_path.is_file():
            meta["raw_text"] = output_path.read_text(encoding="utf-8")
        inventory = path / "capability-inventory.json"
        if inventory.is_file():
            meta["inventory"] = json.loads(inventory.read_text(encoding="utf-8"))
        runtime = path / "runtime.json"
        if runtime.is_file():
            meta["runtime"] = json.loads(runtime.read_text(encoding="utf-8"))
        meta["source_artifact"] = str(path)
        return meta

    def _validate(self, parsed: dict[str, Any]) -> None:
        missing = [field for field in REQUIRED_FIELDS if not parsed.get(field)]
        if missing:
            raise FailClosed("MALFORMED_ARTIFACT:MISSING_" + ",".join(missing).upper())

    def _extract(self, parsed: dict[str, Any], raw_text: str) -> dict[str, list[str]]:
        buckets: dict[str, list[str]] = {key: [] for key in SECTION_PATTERNS}
        for key in buckets:
            provided = parsed.get(key) or []
            if isinstance(provided, str):
                provided = [provided]
            buckets[key].extend(str(item) for item in provided if str(item).strip())
        for line in raw_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            for key, pattern in SECTION_PATTERNS.items():
                match = pattern.match(stripped)
                if match:
                    buckets[key].append(match.group(1).strip())
        # numbered procedures
        for line in raw_text.splitlines():
            if re.match(r"^\s*\d+[.)]\s+\S", line):
                buckets["procedures"].append(line.strip())
        # de-dupe preserving order
        for key, values in buckets.items():
            seen: set[str] = set()
            unique: list[str] = []
            for item in values:
                if item not in seen:
                    seen.add(item)
                    unique.append(item)
            buckets[key] = unique
        return buckets

    def _quarantine(self, artifact: Any, reason: str) -> dict[str, Any]:
        snapshot = artifact if isinstance(artifact, dict) else {"source_artifact": str(artifact)}
        data = canonical_json(snapshot).encode("utf-8")
        digest = self.store.cas.quarantine(data, reason)
        qid = deterministic_id("q", reason, digest)
        payload = {
            "quarantine_id": qid,
            "reason": reason,
            "sha256": digest,
            "status": "QUARANTINED",
            "canonical": False,
        }
        with self.store.transaction():
            self.store.conn.execute(
                """
                INSERT INTO quarantined_artifacts(
                    quarantine_id, source_artifact, reason, sha256, payload_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    qid,
                    str(snapshot.get("source_artifact") or snapshot.get("path") or "inline"),
                    reason,
                    digest,
                    canonical_json(payload),
                    utc_now(),
                ),
            )
            self.store.append_event(EventType.ARTIFACT_QUARANTINED, qid, payload)
        return payload
