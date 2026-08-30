"""Hash outputs and write worker receipts. Not Cognitive WAL."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_output(payload: Any) -> str:
    if isinstance(payload, bytes):
        return sha256_bytes(payload)
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return sha256_bytes(blob)


class ReceiptWriter:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.receipts: list[dict[str, Any]] = []

    def write(
        self,
        *,
        job_id: str,
        worker_id: str,
        input_hash: str,
        output: Any,
        steps: list[str],
        resumed: bool,
    ) -> dict[str, Any]:
        output_hash = hash_output(output)
        receipt = {
            "schema": "raios.nomadic-receipt.v1",
            "ts": datetime.now(timezone.utc).isoformat(),
            "job_id": job_id,
            "worker_id": worker_id,
            "input_hash": input_hash,
            "output_hash": output_hash,
            "steps": list(steps),
            "resumed": bool(resumed),
            "is_c5": False,
            "gl005_proven": False,
        }
        self.receipts.append(receipt)
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(receipt, ensure_ascii=False) + "\n")
        return receipt
