"""Where C5 learns from, how it fetches, and where it puts DISCOVERED tiles.

Not Hugging Face weights. Not a web scrape. Not RAIOS/V9. Not a second WAL.
The map is this module. Fetch is local-file read under an allowlist. Put is ingest.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from .kae import redact

ALLOWED_PREFIXES = (
    ".ai-os/CORE-CONTRACT.md",
    ".ai-os/MASTER-PLAN.md",
    ".ai-os/PROJECT.json",
    ".ai-os/LOCAL-AI-PRIVACY.md",
    ".ai-os/MODEL-REGISTRY.json",
    ".ai-os/COMMAND-VISION.md",
    ".ai-os/state/",
    ".ai-os/council/",
    ".ai-os/handoffs/",
    ".ai-os/mcp/",
    ".ai-os/receipts/",
    ".ai-os/board/",
    ".ai-os/learning/C1-GIT-MEMORY.md",
    ".ai-os/learning/TOOLS-LADDER.json",
    ".ai-os/training/",
    "configs/neuro_lingua/",
    "src/raios/neuro_lingua/",
    "scripts/ai-os/",
    "canonical/",
    "gym/",
    "docs/",
    "tests/neuro_lingua/",
)

DENIED_PARTS = (
    "RAIOS/V9",
    ".env",
    "node_modules",
    ".git/",
    "tokens.local",
    "id_rsa",
    "id_ed25519",
    "__pycache__",
)

# role: learn = read as teacher material; facts = catalog truth; index = how to find;
# write = where DISCOVERED goes; forbidden = never fetch.
LIBRARIES: tuple[dict[str, str], ...] = (
    {"id": "core-contract", "path": ".ai-os/CORE-CONTRACT.md", "role": "learn", "how": "read_file", "put": ""},
    {"id": "decisions", "path": ".ai-os/state/DECISIONS.md", "role": "learn", "how": "read_file", "put": ""},
    {"id": "council", "path": ".ai-os/council/", "role": "learn", "how": "read_dir", "put": ""},
    {"id": "handoffs", "path": ".ai-os/handoffs/", "role": "learn", "how": "read_dir", "put": ""},
    {"id": "lawbook", "path": ".ai-os/mcp/C5-LAWBOOK.json", "role": "learn", "how": "read_file", "put": ""},
    {"id": "grant", "path": ".ai-os/mcp/C5-GRANT.json", "role": "learn", "how": "read_file", "put": ""},
    {"id": "concepts", "path": "configs/neuro_lingua/concepts.yaml", "role": "learn", "how": "read_file", "put": ""},
    {"id": "neuro-lingua", "path": "src/raios/neuro_lingua/", "role": "learn", "how": "read_dir", "put": ""},
    {"id": "keepers", "path": "scripts/ai-os/", "role": "learn", "how": "read_dir", "put": ""},
    {"id": "products", "path": "canonical/data/master_products.json", "role": "facts", "how": "read_file", "put": ""},
    {"id": "stock", "path": "canonical/inventory/stock-levels.json", "role": "facts", "how": "read_file", "put": ""},
    {"id": "warehouses", "path": "canonical/inventory/warehouses.json", "role": "facts", "how": "read_file", "put": ""},
    {"id": "shipments", "path": "canonical/logistics/shipments.json", "role": "facts", "how": "read_file", "put": ""},
    {"id": "git-memory", "path": ".ai-os/learning/C1-GIT-MEMORY.md", "role": "learn", "how": "read_file", "put": ""},
    {"id": "digests", "path": ".ai-os/learning/DIGESTS.jsonl", "role": "index", "how": "hash_skim", "put": ""},
    {"id": "index", "path": ".ai-os/learning/INDEX.json", "role": "index", "how": "term_lookup", "put": ""},
    {"id": "lessons", "path": ".ai-os/learning/LESSONS.jsonl", "role": "index", "how": "jsonl", "put": ""},
    {"id": "candidates", "path": ".ai-os/learning/CANDIDATES.jsonl", "role": "write", "how": "ingest", "put": "DISCOVERED"},
    {"id": "kae-receipts", "path": ".ai-os/receipts/c5-kae/", "role": "write", "how": "receipt", "put": "tiles+metrics"},
    {"id": "experience-receipts", "path": ".ai-os/receipts/c5-experience/", "role": "write", "how": "receipt", "put": "Ck"},
    {"id": "wal", "path": "RAIOS/V9/wal/cognitive-events.jsonl", "role": "forbidden", "how": "none", "put": ""},
    {"id": "hf-hub", "path": "gym/huggingface/", "role": "learn", "how": "docs_only", "put": ""},
)


def repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "configs" / "neuro_lingua").exists():
            return parent
    return Path.cwd()


def rel_of(path: str | Path) -> str:
    raw = str(path).replace("\\", "/").lstrip("./")
    root = str(repo_root()).replace("\\", "/")
    if raw.startswith(root):
        raw = raw[len(root) :].lstrip("/")
    return raw


def allowed(path: str) -> bool:
    rel = rel_of(path)
    if any(part in rel for part in DENIED_PARTS):
        return False
    return any(rel == prefix or rel.startswith(prefix) for prefix in ALLOWED_PREFIXES)


def locate() -> dict[str, Any]:
    root = repo_root()
    rows = []
    for item in LIBRARIES:
        path = root / item["path"]
        exists = path.exists()
        rows.append(
            {
                **item,
                "exists": exists,
                "bytes": path.stat().st_size if path.is_file() else None,
                "fetchable": bool(exists and item["role"] in {"learn", "facts"}),
                "writable": item["role"] == "write",
            }
        )
    known = [row for row in rows if row["exists"] and row["role"] != "forbidden"]
    missing = [row["id"] for row in rows if not row["exists"] and row["role"] != "forbidden"]
    return {
        "schema": "raios.kae-libraries.v1",
        "ok": True,
        "knows_where": True,
        "libraries": rows,
        "known_count": len(known),
        "missing": missing,
        "put": {
            "discovered": ".ai-os/learning/CANDIDATES.jsonl",
            "tiles": ".ai-os/receipts/c5-kae/",
            "digests": ".ai-os/learning/DIGESTS.jsonl",
            "index": ".ai-os/learning/INDEX.json",
            "never": ["RAIOS/V9/wal", "CANONICAL auto-promote", "HF weight download"],
        },
        "how": {
            "list": "python3 scripts/ai-os/raios_c5_kae.py --libraries",
            "fetch_path": "python3 scripts/ai-os/raios_c5_kae.py --from-path .ai-os/state/DECISIONS.md",
            "find": "python3 scripts/ai-os/raios_c5_kae.py --query HTTP_2XX",
            "absorb_first": "python3 scripts/ai-os/raios_absorb.py --inherit",
        },
        "not": ["web scrape", "live C2/C3/C4", "Main Cortex", "hidden reasoning", "credentials"],
        "gl005_proven": False,
        "law": [
            "C5_KNOWS_LIBRARIES_VIA_CATALOG",
            "AUTHORIZED_OUTPUT_ONLY",
            "FETCH_IS_LOCAL_ALLOWLIST",
            "PUT_IS_DISCOVERED_CANDIDATE",
        ],
    }


def fetch(path: str, *, max_chars: int = 4000) -> dict[str, Any]:
    rel = rel_of(path)
    if not allowed(rel):
        return {
            "ok": False,
            "error": "SOURCE_LOCKED_OR_SECRET",
            "path": rel,
            "law": "FETCH_IS_LOCAL_ALLOWLIST",
        }
    file_path = repo_root() / rel
    if file_path.is_dir():
        names = sorted(p.name for p in file_path.iterdir() if p.is_file())[:40]
        text = "\n".join(names)
        return {
            "ok": True,
            "path": rel,
            "kind": "dir",
            "text": text,
            "files": names,
            "consult_used": False,
        }
    if not file_path.is_file():
        return {"ok": False, "error": "SOURCE_MISSING", "path": rel}
    raw = file_path.read_text(encoding="utf-8", errors="replace")
    cleaned, redacted = redact(raw)
    text = cleaned[:max_chars]
    return {
        "ok": True,
        "path": rel,
        "kind": "file",
        "bytes": file_path.stat().st_size,
        "redacted": redacted,
        "text": text,
        "truncated": len(cleaned) > max_chars,
        "consult_used": False,
        "external_calls": 0,
    }


def _digest_paths_for_sha(sha: str, *, limit: int = 5) -> list[str]:
    digests = repo_root() / ".ai-os" / "learning" / "DIGESTS.jsonl"
    if not digests.is_file():
        return []
    hits: list[str] = []
    with digests.open(encoding="utf-8") as handle:
        for line in handle:
            if sha not in line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("sha256") == sha and rec.get("path"):
                hits.append(str(rec["path"]))
                if len(hits) >= limit:
                    break
    return hits


def find(query: str, *, limit: int = 8) -> dict[str, Any]:
    q = (query or "").strip()
    hits: list[dict[str, Any]] = []
    root = repo_root()
    index_path = root / ".ai-os" / "learning" / "INDEX.json"
    if q and index_path.is_file():
        try:
            index = json.loads(index_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            index = {}
        terms = re.findall(r"[A-Za-z][A-Za-z0-9_]{2,}|[\u0600-\u06FF]{2,}", q.lower())
        postings = index.get("postings") or {}
        for term in terms:
            for doc in (postings.get(term) or [])[:6]:
                paths = _digest_paths_for_sha(str(doc))
                hits.append({"source": "index", "term": term, "doc": doc, "paths": paths})
                if len(hits) >= limit:
                    break
            if len(hits) >= limit:
                break
    if q:
        needle = q.lower()
        for item in LIBRARIES:
            if item["role"] in {"forbidden", "write", "index"}:
                continue
            path = root / item["path"]
            if path.is_file():
                try:
                    blob = path.read_text(encoding="utf-8", errors="replace")[:20000].lower()
                except OSError:
                    continue
                if needle in blob or any(part.lower() in blob for part in needle.split() if len(part) > 3):
                    hits.append({"source": "catalog", "path": item["path"], "id": item["id"]})
            if len(hits) >= limit * 2:
                break
    return {
        "ok": True,
        "query": q,
        "hits": hits[:40],
        "hit_count": len(hits),
        "consult_used": False,
        "paid_api": False,
        "how": "INDEX sha → DIGESTS path, then catalog file scan. No web.",
        "gl005_proven": False,
    }


def assimilate_path(path: str, *, ingest: bool = True) -> dict[str, Any]:
    from .kae import assimilate

    got = fetch(path)
    if not got.get("ok"):
        got.update({"schema": "raios.kae.v1", "canonical": False, "gl005_proven": False})
        return got
    rec = assimilate(
        str(got.get("text") or ""),
        source_kind="repo_file",
        source_path=got.get("path"),
        external_calls=0,
        ingest=ingest,
    )
    rec["fetched"] = {k: got[k] for k in ("path", "kind", "truncated", "redacted") if k in got}
    return rec


def assimilate_query(query: str, *, ingest: bool = True) -> dict[str, Any]:
    found = find(query)
    path = None
    for hit in found.get("hits") or []:
        if hit.get("path") and allowed(str(hit["path"])):
            path = hit["path"]
            break
        for cand in hit.get("paths") or []:
            if allowed(str(cand)):
                path = cand
                break
        if path:
            break
    if not path:
        return {
            "ok": False,
            "error": "NO_AUTHORIZED_HIT",
            "find": found,
            "gl005_proven": False,
        }
    rec = assimilate_path(str(path), ingest=ingest)
    rec["find"] = {"query": query, "chosen": path, "hit_count": found.get("hit_count")}
    return rec
