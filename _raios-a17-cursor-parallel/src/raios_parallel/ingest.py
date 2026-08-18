"""Teacher artifact ingest for parallel-wave tests and later A17.4/A17.5 consumption."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .identity import FailClosed, canonical_json, deterministic_id, require_sha256, sha256_bytes, utc_now


class ObservationIngest:
    def __init__(self, store: Any) -> None:
        self.store = store

    def normalize(self, artifact: dict[str, Any] | str | Path) -> dict[str, Any]:
        try:
            parsed = self._parse(artifact)
            for field in ("teacher_id", "model", "task_id", "capability"):
                if not parsed.get(field):
                    raise FailClosed("MALFORMED_ARTIFACT:MISSING_" + field.upper())
            raw = str(parsed.get("raw_text") or parsed.get("output") or "")
            digest = sha256_bytes(raw.encode("utf-8") if raw else canonical_json(parsed).encode("utf-8"))
            declared = parsed.get("source_sha256")
            if declared:
                declared = require_sha256(declared)
                if declared != digest:
                    raise FailClosed("SOURCE_HASH_MISMATCH")
            obs_id = deterministic_id("obs", str(parsed["teacher_id"]), digest, str(parsed["task_id"]))
            existing = self.store.conn.execute(
                "SELECT payload_json FROM observations WHERE observation_id = ?", (obs_id,)
            ).fetchone()
            if existing:
                payload = json.loads(existing["payload_json"])
                payload["_idempotent"] = True
                return payload
            payload = {
                "observation_id": obs_id,
                "teacher_id": parsed["teacher_id"],
                "model": parsed["model"],
                "task_id": parsed["task_id"],
                "capability": parsed["capability"],
                "source_sha256": digest,
                "self_reported_claims": parsed.get("self_reported_claims") or [],
                "verification_state": "UNVERIFIED",
                "self_report_authority": "LOWER_THAN_EMPIRICAL",
                "canonical": False,
            }
            self.store.conn.execute(
                """
                INSERT INTO observations(observation_id, teacher_id, source_sha256, verification_state, canonical, payload_json, created_at)
                VALUES (?, ?, ?, 'UNVERIFIED', 0, ?, ?)
                """,
                (obs_id, parsed["teacher_id"], digest, canonical_json(payload), utc_now()),
            )
            self.store.append_event("OBSERVATION_NORMALIZED", obs_id, {"verification_state": "UNVERIFIED"})
            payload["_idempotent"] = False
            return payload
        except FailClosed as exc:
            return self._quarantine(artifact, str(exc))
        except (OSError, json.JSONDecodeError, UnicodeError, TypeError, ValueError, KeyError) as exc:
            return self._quarantine(artifact, f"MALFORMED_ARTIFACT:{type(exc).__name__}")

    def _parse(self, artifact: dict[str, Any] | str | Path) -> dict[str, Any]:
        if isinstance(artifact, dict):
            return dict(artifact)
        path = Path(artifact)
        if path.is_dir():
            meta = json.loads((path / "meta.json").read_text(encoding="utf-8"))
            if not isinstance(meta, dict):
                raise FailClosed("MALFORMED_ARTIFACT:META_NON_OBJECT")
            out = path / "output.txt"
            if out.is_file():
                meta["raw_text"] = out.read_text(encoding="utf-8")
            return meta
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            data = json.loads(text)
            if not isinstance(data, dict):
                raise FailClosed("MALFORMED_ARTIFACT:NON_OBJECT")
            return data
        return {"raw_text": text}

    def _quarantine(self, artifact: Any, reason: str) -> dict[str, Any]:
        qid = deterministic_id("q", reason)
        payload = {"quarantine_id": qid, "reason": reason, "status": "QUARANTINED", "canonical": False}
        self.store.conn.execute(
            "INSERT INTO quarantined(quarantine_id, reason, sha256, payload_json, created_at) VALUES (?, ?, ?, ?, ?)",
            (qid, reason, None, canonical_json(payload), utc_now()),
        )
        self.store.append_event("ARTIFACT_QUARANTINED", qid, payload)
        return payload
