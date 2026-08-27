"""Immutable observations. Current projection may supersede; history is not rewritten."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .schema import UNKNOWN, SCHEMA
from .secrets import assert_no_secrets, mask_record

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_LOG = ROOT / ".ai-os" / "state" / "resource-fabric" / "observations.jsonl"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def observation(
    *,
    provider: str,
    account: str,
    region: str = UNKNOWN,
    resource_or_service: str,
    value: Any,
    source: str,
    probe_id: str = UNKNOWN,
    confidence: str = UNKNOWN,
    provenance_ref: str = UNKNOWN,
    observed_at: str | None = None,
) -> dict[str, Any]:
    rec = {
        "schema": SCHEMA,
        "kind": "Observation",
        "observation_id": f"OBS-{uuid.uuid4().hex[:16]}",
        "provider": provider,
        "account": account,
        "region": region,
        "resource_or_service": resource_or_service,
        "value": value,
        "source": source,
        "observed_at": observed_at or utc(),
        "probe_id": probe_id,
        "confidence": confidence,
        "provenance_ref": provenance_ref,
        "UNOBSERVED_NE_ABSENT": True,
    }
    rec = mask_record(rec)
    assert_no_secrets(rec)
    return rec


class ObservationStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path else DEFAULT_LOG
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.history: list[dict[str, Any]] = []
        if self.path.is_file():
            for line in self.path.read_text(encoding="utf-8-sig").splitlines():
                if line.strip():
                    self.history.append(json.loads(line))

    def append(self, rec: dict[str, Any]) -> dict[str, Any]:
        rec = mask_record(dict(rec))
        assert_no_secrets(rec)
        self.history.append(rec)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return rec

    def rewrite_forbidden(self, observation_id: str, **_kw: Any) -> None:
        raise ValueError("HISTORICAL_OBSERVATION_IMMUTABLE")

    def projection(self) -> dict[str, dict[str, Any]]:
        current: dict[str, dict[str, Any]] = {}
        for rec in self.history:
            key = f"{rec.get('provider')}|{rec.get('account')}|{rec.get('resource_or_service')}"
            current[key] = rec
        return current
