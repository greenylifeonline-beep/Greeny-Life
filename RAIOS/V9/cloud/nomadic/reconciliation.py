"""Detect duplicate outputs and reconcile worker receipts against the ledger."""
from __future__ import annotations

from collections import defaultdict
from typing import Any


def reconcile(receipts: list[dict[str, Any]]) -> dict[str, Any]:
    by_job: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_hash: dict[str, list[str]] = defaultdict(list)
    for row in receipts:
        by_job[str(row.get("job_id"))].append(row)
        digest = str(row.get("output_hash") or "")
        if digest:
            by_hash[digest].append(str(row.get("job_id")))
    duplicates = []
    for job_id, rows in by_job.items():
        hashes = {r.get("output_hash") for r in rows}
        if len(rows) > 1:
            duplicates.append(
                {
                    "job_id": job_id,
                    "receipts": len(rows),
                    "same_output": len(hashes) == 1,
                    "output_hashes": sorted(h for h in hashes if h),
                }
            )
    return {
        "receipts": len(receipts),
        "jobs": len(by_job),
        "duplicate_job_receipts": duplicates,
        "duplicate_output_detected": any(len(v) > 1 for v in by_hash.values()) or any(d["receipts"] > 1 for d in duplicates),
        "same_hash_across_jobs": {h: ids for h, ids in by_hash.items() if len(set(ids)) > 1},
        "ok": True,
        "gl005_proven": False,
    }
