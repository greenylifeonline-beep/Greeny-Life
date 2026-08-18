"""SHA-256 evidence artifacts. stdout is not evidence."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .certification import EvidenceLedger as CertificationLedger
from .config import canonical_json, sha256_text, utc_now

EvidenceLedger = CertificationLedger


def write_artifact(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    body = {**payload, "created_at": payload.get("created_at") or utc_now(), "canonical": False}
    text = canonical_json(body)
    digest = sha256_text(text)
    body["sha256"] = digest
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_json(body), encoding="utf-8")
    return body
