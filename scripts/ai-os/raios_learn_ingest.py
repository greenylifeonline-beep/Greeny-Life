#!/usr/bin/env python3
"""Internal RAIOS ingest only. Not an MCP tool. DISCOVERED candidates, no WAL, no promote."""
from __future__ import annotations

import argparse
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANDIDATES = ROOT / ".ai-os" / "learning" / "CANDIDATES.jsonl"
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def ingest(text: str, source: str, evidence_refs: list[str]) -> dict:
    rec = {
        "schema": "raios.learning-candidate.v1",
        "id": str(uuid.uuid4()),
        "ts": utc(),
        "from": "C4",
        "source": source,
        "text": text,
        "evidence_refs": evidence_refs,
        "knowledge_state": "DISCOVERED",
        "validated": False,
        "promoted": False,
        "canonical": False,
        "wal_written": False,
        "gl005_proven": False,
        "law": "LEARNING_CANDIDATE_NE_CANONICAL",
    }
    rec["receipt_sha256"] = hashlib.sha256(
        json.dumps(rec, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    CANDIDATES.parent.mkdir(parents=True, exist_ok=True)
    before = WAL.stat().st_mtime if WAL.exists() else None
    with CANDIDATES.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
    after = WAL.stat().st_mtime if WAL.exists() else None
    rec["wal_mtime_unchanged"] = before == after
    if rec["wal_written"] or rec["promoted"] or rec["canonical"]:
        raise SystemExit("INGEST_VIOLATION")
    return rec


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--text", required=True)
    p.add_argument("--source", default="mcp-rendezvous")
    p.add_argument("--ref", action="append", default=[])
    args = p.parse_args()
    rec = ingest(args.text, args.source, args.ref)
    print(json.dumps(rec, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
