#!/usr/bin/env python3
"""Invented C5 retrieval: inverted index over digests. Stdlib only. Faster than unloaded embeddings."""
from __future__ import annotations

import json
import re
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIGESTS = ROOT / ".ai-os" / "learning" / "DIGESTS.jsonl"
OUT = ROOT / ".ai-os" / "learning" / "INDEX.json"
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{2,}|[\u0600-\u06FF]{2,}")
STOP = {
    "the",
    "and",
    "for",
    "that",
    "this",
    "with",
    "from",
    "not",
    "are",
    "was",
    "json",
    "true",
    "false",
    "none",
}


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def tokens(text: str) -> list[str]:
    out = []
    for match in TOKEN_RE.finditer(text or ""):
        tok = match.group(0).lower()
        if tok not in STOP:
            out.append(tok)
    return out


def build() -> dict:
    t0 = time.perf_counter()
    wal_before = WAL.stat().st_mtime if WAL.exists() else None
    postings: dict[str, list[str]] = defaultdict(list)
    docs = 0
    if DIGESTS.exists():
        for raw in DIGESTS.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if rec.get("status") == "DEDUPED":
                continue
            docs += 1
            blob = " ".join(
                [
                    str(rec.get("path") or ""),
                    str(rec.get("skim_head") or ""),
                    str(rec.get("skim_tail") or ""),
                    str(rec.get("law") or ""),
                ]
            )
            seen_terms: set[str] = set()
            doc_id = rec.get("sha256") or rec.get("path")
            for tok in tokens(blob):
                if tok in seen_terms:
                    continue
                seen_terms.add(tok)
                bucket = postings[tok]
                if len(bucket) < 24:
                    bucket.append(str(doc_id))
    # cap terms
    ranked = sorted(postings.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:1800]
    index = {
        "schema": "raios.c5-index.v1",
        "from": "C5",
        "ts": utc(),
        "docs": docs,
        "terms": len(ranked),
        "postings": {k: v for k, v in ranked},
        "paid_api": False,
        "embedding_model": False,
        "wal_written": False,
        "gl005_proven": False,
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        "law": "INVERTED_INDEX_NE_UNLOADED_EMBEDDING",
    }
    wal_after = WAL.stat().st_mtime if WAL.exists() else None
    if wal_before != wal_after:
        raise SystemExit("INDEX_WAL_VIOLATION")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(index, ensure_ascii=False) + "\n", encoding="utf-8")
    return index


def main() -> int:
    index = build()
    print(json.dumps({"from": "C5", "docs": index["docs"], "terms": index["terms"], "ms": index["elapsed_ms"], "gl005_proven": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
