from __future__ import annotations

from pathlib import Path
from typing import Any

LIVE_IDS = ("mind-fill", "absorb", "index", "kae", "book", "neurolingua-speak")
OSS_IN_USE = ("RapidFuzz", "Ollama", "NATS", "FastAPI", "C5 inverted INDEX", "Search Cortex")
OSS_REJECTED_SECOND_PLANE = (
    "LangChain", "Chroma", "LightRAG", "Lucene/Solr second index",
    "Apache Tika as a second ingest bus",
)
OSS_UPGRADE_CANDIDATES = (
    {
        "id": "datasketch",
        "license": "MIT",
        "use": "MinHash LSH beside absorb/KAE near-dup — not a second index",
        "installed": False,
        "status": "UNPROVEN_CANDIDATE",
    },
)


def _load(path: Path, default: Any) -> Any:
    try:
        import json
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError, TypeError):
        return default


def snapshot(repo: Path, *, home: Path | None = None) -> dict[str, Any]:
    repo = Path(repo).resolve()
    home = Path(home or Path.home())
    inv = _load(repo / ".ai-os" / "reports" / "RAIOS-MERGE-ENGINES-INVENTORY.json", {})
    live_ids = list(inv.get("live_ids") or LIVE_IDS)
    rows = []
    for row in inv.get("engines") or []:
        rel = str(row.get("path") or "")
        path = repo / rel if rel else None
        exists = bool(path and path.exists())
        eid = str(row.get("id") or "")
        rows.append({
            "id": eid,
            "name_ar": row.get("name_ar"),
            "status": row.get("status"),
            "path": rel,
            "path_exists": exists,
            "live_keeper": eid in live_ids,
            "execute_here": row.get("execute_here") is True,
        })
    if not rows:
        for eid in LIVE_IDS:
            rows.append({"id": eid, "status": "CATALOG_MISSING_INVENTORY",
                         "path_exists": False, "live_keeper": True, "execute_here": True})
    mind = _load(repo / ".ai-os" / "receipts" / "c5-mind-fill" / "LAST.json", {})
    book = _load(repo / ".ai-os" / "receipts" / "c5-book" / "LAST.json", {})
    merge = _load(repo / ".ai-os" / "receipts" / "c5-merge-engines" / "LAST.json", {})
    pres = home / ".raios" / "runtime" / "council-ops" / "presence.json"
    digests = repo / ".ai-os" / "learning" / "DIGESTS.jsonl"
    index = repo / ".ai-os" / "learning" / "INDEX.json"
    return {
        "schema": "raios.live-engine-plane.v1",
        "inventory_is_execution": False,
        "merged_now": False,
        "automatic_merge": False,
        "second_search_bus": False,
        "langchain": False,
        "new_kernel": False,
        "live_ids": live_ids,
        "live_path_ok": all(
            (repo / str(r.get("path") or "")).exists()
            for r in rows if r.get("id") in live_ids and r.get("path")
        ),
        "engines": rows,
        "drowning_controls": {
            "lock_is_effective": True,
            "presence_bytes": pres.stat().st_size if pres.is_file() else None,
            "digests_bytes": digests.stat().st_size if digests.is_file() else None,
            "index_bytes": index.stat().st_size if index.is_file() else None,
            "search_cortex_dedupe": True,
            "absorb_digest_dedupe": True,
            "expired_lease_does_not_pin_files": True,
        },
        "last_receipts": {
            "mind_fill_ts": mind.get("ts"),
            "mind_fill_deduped": mind.get("deduped"),
            "book_ts": book.get("ts"),
            "merge_inventory_ok": merge.get("ok") is True,
            "merge_executed": merge.get("merged_now") is True,
        },
        "oss_in_use": list(OSS_IN_USE),
        "oss_rejected_as_second_plane": list(OSS_REJECTED_SECOND_PLANE),
        "oss_upgrade_candidates": list(OSS_UPGRADE_CANDIDATES),
        "law": [
            "FILE_NAMED_ENGINE_NE_LIVE_ENGINE",
            "MERGE_INVENTORY_NE_MERGE_EXECUTION",
            "REUSE_BEFORE_BUILD",
            "NO_SECOND_SEARCH_BUS",
            "AUTOMATIC_MERGE_FALSE",
        ],
    }
