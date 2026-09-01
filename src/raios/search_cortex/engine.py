from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
import multiprocessing as mp
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(os.getenv("RAIOS_CANONICAL_REPO", str(Path(__file__).resolve().parents[3]))).resolve()
V9_RUNTIME = REPO / "RAIOS" / "V9" / "runtime"
if str(V9_RUNTIME) not in sys.path:
    sys.path.insert(0, str(V9_RUNTIME))

from cognitive_event_bus import build_event, emit_event
from git_history_search import search_git_history

WAL = REPO / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
DERIVED_DB = Path.home() / ".raios" / "runtime" / "manager" / "retrieval.sqlite3"
OFFICIAL = Path.home() / ".raios" / "runtime" / "factory-fabric" / "foundry" / "data" / "official-source-snapshot.json"
RUNTIME_ROOT = Path.home() / ".raios" / "runtime" / "search-cortex"
LATEST = RUNTIME_ROOT / "latest.json"
REPO_INDEX_DB = RUNTIME_ROOT / "repo-index-v2.sqlite3"
LEARNING_DIGESTS = REPO / ".ai-os" / "learning" / "DIGESTS.jsonl"

SOURCE_WEIGHT = {
    "CANONICAL_REPO": 1.00,
    "COGNITIVE_WAL": 0.98,
    "LEARNING_DIGEST": 0.94,
    "DERIVED_RETRIEVAL": 0.92,
    "OFFICIAL_PUBLIC": 0.88,
    "GIT_HISTORY": 0.86,
    "PUBLIC_WEB": 0.55,
}

TRUST_SCORE = {
    "HIGH": 1.0,
    "OFFICIAL_SOURCE": 0.96,
    "LOCAL_DIGEST": 0.90,
    "HISTORICAL_EVIDENCE": 0.82,
    "DERIVED": 0.76,
    "UNVERIFIED_PUBLIC": 0.48,
}

OPPOSING_CLAIMS = (
    ("ONLINE", "OFFLINE"),
    ("HEALTHY", "DEGRADED"),
    ("DONE", "BLOCKED"),
    ("PRESENT", "UNPROVEN"),
    ("TRUE", "FALSE"),
)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _atomic(path: Path, obj: Any) -> None:
    """Validated atomic replace with a unique temporary name and bounded retry."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(obj, ensure_ascii=False, indent=2, default=str) + "\n"
    tmp = path.with_name(f"{path.name}.tmp-{os.getpid()}-{time.time_ns()}")
    try:
        tmp.write_text(payload, encoding="utf-8")
        json.loads(tmp.read_text(encoding="utf-8"))
        for attempt in range(5):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.025 * (attempt + 1))
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def _safe_public_query(value: str | None) -> str | None:
    if not value:
        return None
    q = value.strip()
    if not q:
        return None
    blocked = [
        r"[A-Za-z]:\\",
        r".ai-os",
        r"RAIOS[/\\]V9",
        r"@[A-Za-z0-9._-]+\.[A-Za-z]{2,}",
        r"gh[opusr]_[A-Za-z0-9_-]+",
        r"sk-[A-Za-z0-9_-]+",
        r"[0-9a-fA-F]{32,64}",
    ]
    if any(re.search(p, q) for p in blocked):
        return None
    return q[:400]


def _tokens(query: str) -> list[str]:
    return [x.lower() for x in re.findall(r"[\w.-]{3,}", query, flags=re.UNICODE)][:20]


def _score_text(text: str, tokens: list[str]) -> float:
    low = text.lower()
    if not tokens:
        return 0.0
    hits = sum(1 for t in tokens if t in low)
    return hits / len(tokens)


def plan_query(query: str, *, deep: bool = False) -> dict[str, Any]:
    """Build an inspectable retrieval plan without exposing hidden reasoning."""
    normalized = re.sub(r"\s+", " ", (query or "").strip())[:4000]
    lowered = normalized.lower()
    intents: list[str] = []
    intent_rules = (
        ("DIAGNOSE", ("افحص", "فحص", "خطأ", "عطل", "سبب", "diagnos", "error", "fail", "root cause")),
        ("CURRENT_STATE", ("الآن", "الحالي", "حالة", "online", "live", "status", "current")),
        ("COMPARE", ("قارن", "مقارنة", "أفضل", "versus", " vs ", "compare")),
        ("VERIFY", ("تحقق", "اثبت", "دليل", "verify", "prove", "evidence")),
        ("LEARN", ("تعلم", "استيعاب", "ذاكرة", "learn", "assimil", "memory")),
        ("EXECUTE", ("نفذ", "تنفيذ", "مهمة", "execute", "deploy", "task")),
    )
    for intent, markers in intent_rules:
        if any(marker in lowered for marker in markers):
            intents.append(intent)
    if not intents:
        intents.append("RETRIEVE")

    fragments = [
        part.strip(" -:،؛")
        for part in re.split(r"(?:\?|؟|\n|[؛;]|\s+(?:ثم|and then|versus|vs)\s+)", normalized, flags=re.I)
        if part and len(part.strip()) >= 3
    ]
    subqueries = list(dict.fromkeys([normalized, *fragments]))[:5]
    currentness_required = "CURRENT_STATE" in intents or "DIAGNOSE" in intents
    return {
        "schema": "raios.search-plan.v1",
        "normalized_query": normalized,
        "intents": intents,
        "subqueries": subqueries,
        "deep_history": bool(deep),
        "currentness_required": currentness_required,
        "source_order": [
            "CANONICAL_REPO",
            "COGNITIVE_WAL",
            "LEARNING_DIGEST",
            "DERIVED_RETRIEVAL",
            "OFFICIAL_PUBLIC",
            "GIT_HISTORY",
            "PUBLIC_WEB",
        ],
        "gates": [
            "PROVENANCE_REQUIRED",
            "CURRENTNESS_WHEN_REQUIRED",
            "CROSS_SOURCE_CONTRADICTION_SCAN",
            "PRIVATE_QUERY_NE_PUBLIC_QUERY",
        ],
    }


def _learning_search(query: str, limit: int) -> list[dict[str, Any]]:
    digests_path = Path(os.getenv("RAIOS_CANONICAL_REPO", str(REPO))).resolve() / ".ai-os" / "learning" / "DIGESTS.jsonl"
    if not digests_path.is_file():
        return []
    toks = _tokens(query)
    if not toks:
        return []
    rows: list[dict[str, Any]] = []
    try:
        with digests_path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            recent = deque(handle, maxlen=5000)
    except OSError:
        return []
    for raw in recent:
        try:
            rec = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if rec.get("status") == "DEDUPED":
            continue
        blob = " ".join(
            str(rec.get(key) or "")
            for key in ("path", "skim_head", "skim_tail", "law", "text", "prompt", "response")
        )
        relevance = _score_text(blob, toks)
        if relevance <= 0:
            continue
        rows.append({
            "source": "LEARNING_DIGEST",
            "path": rec.get("path"),
            "sha256": rec.get("sha256"),
            "timestamp": rec.get("ts"),
            "excerpt": blob[:1400],
            "trust": "LOCAL_DIGEST",
            "freshness": "DISCOVERED_NOT_CANONICAL",
            "knowledge_state": rec.get("knowledge_state", "DISCOVERED"),
            "score": SOURCE_WEIGHT["LEARNING_DIGEST"] + relevance,
        })
    rows.sort(key=lambda item: float(item.get("score") or 0.0), reverse=True)
    return rows[:limit]


def _citation(row: dict[str, Any]) -> str:
    locator = (
        row.get("path")
        or row.get("source_id")
        or row.get("url")
        or row.get("event_id")
        or row.get("doc_id")
        or "unlocated"
    )
    if row.get("line"):
        locator = f"{locator}:{row['line']}"
    return f"{row.get('source', 'UNKNOWN')}::{locator}"


def _annotate_and_dedupe(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in sorted(rows, key=lambda item: float(item.get("score") or 0.0), reverse=True):
        locator = _citation(row)
        excerpt_hash = hashlib.sha256(str(row.get("excerpt") or "").encode("utf-8")).hexdigest()[:16]
        key = f"{locator}|{excerpt_hash}"
        if key in seen:
            continue
        seen.add(key)
        trust = str(row.get("trust") or "DERIVED")
        annotated = dict(row)
        annotated["trust_score"] = TRUST_SCORE.get(trust, 0.68)
        annotated["citation"] = locator
        annotated["evidence_id"] = f"E{len(selected) + 1:03d}"
        selected.append(annotated)
        if len(selected) >= limit:
            break
    return selected


def _detect_contradictions(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    contradictions: list[dict[str, Any]] = []
    for positive, negative in OPPOSING_CLAIMS:
        pos: list[str] = []
        neg: list[str] = []
        for row in rows:
            text = str(row.get("excerpt") or "").upper()
            has_pos = re.search(rf"(?<![A-Z0-9_]){re.escape(positive)}(?![A-Z0-9_])", text) is not None
            has_neg = re.search(rf"(?<![A-Z0-9_]){re.escape(negative)}(?![A-Z0-9_])", text) is not None
            if has_pos and not has_neg:
                pos.append(str(row.get("evidence_id")))
            elif has_neg and not has_pos:
                neg.append(str(row.get("evidence_id")))
        if pos and neg:
            contradictions.append({
                "claim_pair": [positive, negative],
                "positive_evidence": pos,
                "negative_evidence": neg,
                "resolved": False,
            })
    return contradictions


def _verification(plan: dict[str, Any], rows: list[dict[str, Any]], contradictions: list[dict[str, Any]]) -> dict[str, Any]:
    current = any(
        any(token in str(row.get("freshness") or "").upper() for token in ("CURRENT", "LIVE", "EVENT_TIME"))
        for row in rows
    )
    source_count = len({str(row.get("source")) for row in rows})
    if not rows:
        status = "NO_EVIDENCE"
    elif contradictions:
        status = "CONFLICT"
    elif plan.get("currentness_required") and not current:
        status = "STALE_OR_UNPROVEN"
    else:
        status = "PASS"
    return {
        "status": status,
        "evidence_count": len(rows),
        "source_count": source_count,
        "currentness_required": bool(plan.get("currentness_required")),
        "currentness_satisfied": current,
        "contradiction_count": len(contradictions),
        "execution_claims_allowed": False,
    }


FAST_EXCLUDE_PREFIXES = (
    "archive/",
    "node_modules/",
    ".next/",
    "RAIOS/V9/evaluation/",
    "_GREENY_DIAGNOSTIC_",
)
FAST_MAX_FILE_BYTES = 786432


def _fast_indexable(relative_path: str) -> bool:
    normalized = relative_path.replace("\\", "/")
    if any(normalized.startswith(prefix) for prefix in FAST_EXCLUDE_PREFIXES):
        return False
    if "/__pycache__/" in normalized or normalized.endswith(".pyc"):
        return False
    return True


def refresh_repo_index(max_files: int = 25000) -> dict[str, Any]:
    RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(REPO_INDEX_DB, timeout=5)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA synchronous=NORMAL")
    db.execute(
        "CREATE TABLE IF NOT EXISTS repo_files ("
        "path TEXT PRIMARY KEY, mtime_ns INTEGER, size INTEGER, "
        "content_hash TEXT, indexed_at TEXT)"
    )
    db.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS repo_fts "
        "USING fts5(path UNINDEXED, text, tokenize='unicode61')"
    )

    hot_roots = [
        "src",
        "RAIOS/V9/runtime",
        "RAIOS/V9/continuity",
        "RAIOS/V9/governance",
        "RAIOS/V9/agents",
        "RAIOS/V9/foundry",
        "RAIOS/V9/cli",
        ".ai-os/state",
        ".ai-os/mcp",
        ".ai-os/mail",
        "scripts",
        "configs",
        "docs",
        "canonical",
        "intelligence",
    ]
    proc = subprocess.run(
        [
            "git", "ls-files", "-co", "--exclude-standard", "-z",
            "--", *hot_roots,
        ],
        cwd=REPO,
        capture_output=True,
        timeout=8,
        check=False,
    )
    if proc.returncode != 0:
        db.close()
        return {"status": "GIT_LIST_FAILED", "updated": 0, "removed": 0}

    paths = [
        raw.decode("utf-8", errors="replace")
        for raw in proc.stdout.split(b"\x00")
        if raw
    ][:max_files]
    current = set()
    updated = 0
    skipped = 0

    for relative in paths:
        if not _fast_indexable(relative):
            skipped += 1
            continue
        full = REPO / relative
        try:
            st = full.stat()
        except OSError:
            continue
        if not full.is_file() or st.st_size > FAST_MAX_FILE_BYTES:
            skipped += 1
            continue

        current.add(relative)
        row = db.execute(
            "SELECT mtime_ns,size FROM repo_files WHERE path=?",
            (relative,),
        ).fetchone()
        if row and int(row[0]) == int(st.st_mtime_ns) and int(row[1]) == int(st.st_size):
            continue

        try:
            raw = full.read_bytes()
        except OSError:
            continue
        if b"\x00" in raw[:8192]:
            skipped += 1
            continue
        text = raw.decode("utf-8", errors="replace")
        content_hash = hashlib.sha256(raw).hexdigest()

        db.execute("DELETE FROM repo_fts WHERE path=?", (relative,))
        db.execute(
            "INSERT INTO repo_fts(path,text) VALUES(?,?)",
            (relative, text),
        )
        db.execute(
            "INSERT INTO repo_files(path,mtime_ns,size,content_hash,indexed_at) "
            "VALUES(?,?,?,?,?) "
            "ON CONFLICT(path) DO UPDATE SET "
            "mtime_ns=excluded.mtime_ns,size=excluded.size,"
            "content_hash=excluded.content_hash,indexed_at=excluded.indexed_at",
            (
                relative,
                int(st.st_mtime_ns),
                int(st.st_size),
                content_hash,
                utc(),
            ),
        )
        updated += 1

    removed = 0
    for (known,) in db.execute("SELECT path FROM repo_files").fetchall():
        if known not in current and _fast_indexable(known):
            db.execute("DELETE FROM repo_files WHERE path=?", (known,))
            db.execute("DELETE FROM repo_fts WHERE path=?", (known,))
            removed += 1

    db.commit()
    total = db.execute("SELECT COUNT(*) FROM repo_files").fetchone()[0]
    db.close()
    return {
        "status": "PASS",
        "updated": updated,
        "removed": removed,
        "skipped": skipped,
        "indexed_files": total,
        "derived_cache_only": True,
    }


def _repo_search(query: str, limit: int) -> list[dict[str, Any]]:
    if not REPO_INDEX_DB.is_file():
        return []
    tokens = _tokens(query)
    if not tokens:
        return []
    fts_q = " OR ".join('"' + token.replace('"', "") + '"' for token in tokens[:12])
    try:
        db = sqlite3.connect(
            f"file:{REPO_INDEX_DB}?mode=ro",
            uri=True,
            timeout=0.5,
        )
        found = db.execute(
            "SELECT path,text,bm25(repo_fts) AS rank "
            "FROM repo_fts WHERE repo_fts MATCH ? "
            "ORDER BY rank LIMIT ?",
            (fts_q, limit),
        ).fetchall()
        db.close()
    except Exception:
        return []

    rows: list[dict[str, Any]] = []
    for rank, (path, text, _bm25) in enumerate(found, start=1):
        low = text.lower()
        positions = [low.find(token) for token in tokens if token in low]
        pos = min(positions) if positions else 0
        start = max(0, pos - 220)
        excerpt = text[start:start + 1200].replace("\x00", " ")
        line = text.count("\n", 0, pos) + 1 if pos >= 0 else None
        rows.append({
            "source": "CANONICAL_REPO",
            "path": path,
            "line": line,
            "excerpt": excerpt,
            "trust": "HIGH",
            "freshness": "CURRENT_WORKTREE_INDEX",
            "score": SOURCE_WEIGHT["CANONICAL_REPO"] + (1.0 / (50 + rank)),
        })
    return rows


def _wal_search(query: str, limit: int) -> list[dict[str, Any]]:
    tokens = _tokens(query)
    if not WAL.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with WAL.open("r", encoding="utf-8-sig", errors="replace") as handle:
        for raw in handle:
            if not any(t in raw.lower() for t in tokens):
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError:
                continue
            text = json.dumps(obj, ensure_ascii=False, default=str)
            rows.append({
                "source": "COGNITIVE_WAL",
                "event_id": obj.get("event_id"),
                "event_type": obj.get("event_type"),
                "timestamp": obj.get("timestamp"),
                "excerpt": text[:1200],
                "trust": "HIGH",
                "freshness": "EVENT_TIME",
                "score": SOURCE_WEIGHT["COGNITIVE_WAL"] + _score_text(text, tokens),
            })
    return rows[-limit:]


def _derived_search(query: str, limit: int) -> list[dict[str, Any]]:
    if not DERIVED_DB.is_file():
        return []
    tokens = _tokens(query)
    fts_q = " OR ".join(tokens[:12])
    if not fts_q:
        return []
    try:
        db = sqlite3.connect(f"file:{DERIVED_DB}?mode=ro", uri=True, timeout=1)
        found = db.execute(
            "SELECT f.doc_id,d.source_id,d.access_class,d.trust_class,d.text,bm25(docs_fts) "
            "FROM docs_fts f JOIN docs d ON d.doc_id=f.doc_id "
            "WHERE docs_fts MATCH ? ORDER BY bm25(docs_fts) LIMIT ?",
            (fts_q, limit),
        ).fetchall()
        db.close()
    except Exception:
        return []
    return [{
        "source": "DERIVED_RETRIEVAL",
        "doc_id": row[0],
        "source_id": row[1],
        "access_class": row[2],
        "trust": row[3],
        "excerpt": row[4][:1200],
        "freshness": "DERIVED_CURRENT",
        "score": SOURCE_WEIGHT["DERIVED_RETRIEVAL"] + max(0.0, _score_text(row[4], tokens)),
    } for row in found]


def _official_search(query: str, limit: int) -> list[dict[str, Any]]:
    if not OFFICIAL.is_file():
        return []
    try:
        obj = json.loads(OFFICIAL.read_text(encoding="utf-8-sig"))
    except Exception:
        return []
    tokens = _tokens(query)
    rows = []
    candidates = obj.get("records") if isinstance(obj, dict) else None
    if not isinstance(candidates, list):
        candidates = [obj]
    for item in candidates:
        text = json.dumps(item, ensure_ascii=False, default=str)
        relevance = _score_text(text, tokens)
        if relevance <= 0:
            continue
        rows.append({
            "source": "OFFICIAL_PUBLIC",
            "source_id": item.get("source_id") if isinstance(item, dict) else None,
            "excerpt": text[:1400],
            "trust": "OFFICIAL_SOURCE",
            "freshness": "SNAPSHOT_NEEDS_CURRENTNESS_CHECK",
            "score": SOURCE_WEIGHT["OFFICIAL_PUBLIC"] + relevance,
        })
    rows.sort(key=lambda x: x["score"], reverse=True)
    return rows[:limit]


def _ddgs_worker(query: str, limit: int, queue: Any) -> None:
    try:
        from ddgs import DDGS
        queue.put(list(DDGS().text(query, max_results=limit)))
    except BaseException:
        queue.put([])


def _public_search(
    public_query: str | None,
    limit: int,
    timeout_seconds: float = 8.0,
) -> list[dict[str, Any]]:
    safe = _safe_public_query(public_query)
    if not safe:
        return []

    ctx = mp.get_context("spawn")
    queue = ctx.Queue(maxsize=1)
    process = ctx.Process(
        target=_ddgs_worker,
        args=(safe, limit, queue),
        daemon=True,
    )
    process.start()
    process.join(timeout_seconds)

    if process.is_alive():
        process.terminate()
        process.join(1.0)
        return []

    try:
        found = queue.get_nowait()
    except Exception:
        found = []

    rows = []
    for item in found:
        rows.append({
            "source": "PUBLIC_WEB",
            "title": item.get("title"),
            "url": item.get("href"),
            "excerpt": (item.get("body") or "")[:1200],
            "trust": "UNVERIFIED_PUBLIC",
            "freshness": "LIVE_SEARCH_RESULT",
            "score": SOURCE_WEIGHT["PUBLIC_WEB"],
        })
    return rows


def _git_history_worker(query: str, limit: int, queue: Any) -> None:
    """Run the existing historical search outside the request process."""
    try:
        queue.put({"status": "PASS", "result": search_git_history(query, limit)})
    except BaseException as exc:
        queue.put({
            "status": "ERROR",
            "error": type(exc).__name__,
            "result": {"matches": []},
        })


def _bounded_git_history(
    query: str,
    limit: int,
    timeout_seconds: float = 6.0,
) -> dict[str, Any]:
    """Reuse the canonical history search with a killable latency boundary."""
    ctx = mp.get_context("spawn")
    queue = ctx.Queue(maxsize=1)
    process = ctx.Process(
        target=_git_history_worker,
        args=(query, limit, queue),
        daemon=True,
    )
    process.start()
    process.join(timeout_seconds)
    if process.is_alive():
        process.terminate()
        process.join(1.0)
        return {"status": "TIMEOUT", "matches": []}
    try:
        envelope = queue.get_nowait()
    except Exception:
        return {"status": "NO_RESULT", "matches": []}
    result = envelope.get("result") or {}
    return {
        "status": envelope.get("status") or "ERROR",
        "error": envelope.get("error"),
        "matches": list(result.get("matches") or []),
    }


def search(
    query: str,
    *,
    public_query: str | None = None,
    allow_public: bool = False,
    include_history: bool = False,
    include_official: bool = True,
    limit: int = 20,
    emit_trace: bool = True,
) -> dict[str, Any]:
    """Plan, retrieve, fuse, cite and verify evidence across the one Search Cortex."""
    started = time.perf_counter()
    plan = plan_query(query, deep=include_history)
    pieces: list[dict[str, Any]] = []
    errors: list[str] = []

    private_queries = (plan.get("subqueries") or [query])[:3]
    jobs: list[tuple[Any, str, str]] = []
    for subquery in private_queries:
        jobs.extend([
            (_repo_search, subquery, "CANONICAL_REPO"),
            (_derived_search, subquery, "DERIVED_RETRIEVAL"),
            (_learning_search, subquery, "LEARNING_DIGEST"),
        ])
    jobs.append((_wal_search, query, "COGNITIVE_WAL"))
    if include_official:
        jobs.append((_official_search, query, "OFFICIAL_PUBLIC"))

    with ThreadPoolExecutor(max_workers=min(8, len(jobs) or 1)) as pool:
        futures = {
            pool.submit(fn, subquery, max(limit, 8)): source
            for fn, subquery, source in jobs
        }
        for future in as_completed(futures):
            source = futures[future]
            try:
                pieces.extend(future.result())
            except Exception as exc:
                errors.append(f"{source}::{type(exc).__name__}")

    if include_history:
        try:
            history = _bounded_git_history(query, min(limit, 30))
            if history.get("status") != "PASS":
                errors.append(f"GIT_HISTORY::{history.get('status')}")
            for item in history.get("matches", []):
                pieces.append({
                    "source": "GIT_HISTORY",
                    **item,
                    "trust": "HISTORICAL_EVIDENCE",
                    "freshness": "HISTORICAL",
                    "score": SOURCE_WEIGHT["GIT_HISTORY"],
                })
        except Exception as exc:
            errors.append(f"GIT_HISTORY::{type(exc).__name__}")

    public_used = False
    sanitized_public_query = None
    if allow_public:
        sanitized_public_query = _safe_public_query(public_query)
        if sanitized_public_query:
            pieces.extend(_public_search(sanitized_public_query, limit))
            public_used = True

    selected = _annotate_and_dedupe(pieces, limit)
    contradictions = _detect_contradictions(selected)
    verification = _verification(plan, selected, contradictions)
    result = {
        "schema": "raios.search-cortex.result.v2",
        "generated_at": utc(),
        "query": query,
        "plan": plan,
        "public_query": sanitized_public_query,
        "private_query_sent_to_web": False,
        "public_search_used": public_used,
        "count": len(selected),
        "sources": sorted({str(item.get("source")) for item in selected}),
        "results": selected,
        "evidence": [
            {
                "evidence_id": item.get("evidence_id"),
                "citation": item.get("citation"),
                "source": item.get("source"),
                "trust_score": item.get("trust_score"),
                "freshness": item.get("freshness"),
            }
            for item in selected
        ],
        "contradictions": contradictions,
        "verification": verification,
        "errors": errors,
        "answer_policy": {
            "execution_claims_allowed": False,
            "cite_evidence_ids": True,
            "surface_unresolved_contradictions": True,
            "hidden_reasoning_exported": False,
        },
        "wal_written": bool(emit_trace),
        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
    }
    _atomic(LATEST, result)

    if emit_trace:
        event = build_event(
            event_type="SEARCH",
            actor="RAIOS-SEARCH-CORTEX",
            intent=(
                "Plan and retrieve grounded context across private, historical, "
                "cognitive, official and explicitly separated public sources"
            ),
            success=verification["status"] != "NO_EVIDENCE",
            tool="RAIOS_SEARCH_CORTEX",
            input_ref={
                "query": query,
                "public_query": sanitized_public_query,
                "allow_public": allow_public,
                "intents": plan.get("intents"),
            },
            output_ref={
                "count": result["count"],
                "sources": result["sources"],
                "verification": verification["status"],
                "contradictions": len(contradictions),
                "latency_ms": result["latency_ms"],
                "private_query_sent_to_web": False,
            },
            evidence_refs=[str(LATEST), str(WAL)],
            confidence=0.95 if verification["status"] == "PASS" else 0.70,
        )
        emit_event(event)
    return result


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("query", nargs="?")
    parser.add_argument("--public-query")
    parser.add_argument("--allow-public", action="store_true")
    parser.add_argument("--history", action="store_true")
    parser.add_argument("--no-official", action="store_true")
    parser.add_argument("--refresh-index", action="store_true")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    if args.refresh_index:
        print(json.dumps(refresh_repo_index(), ensure_ascii=False, indent=2))
        return 0
    if not args.query:
        parser.error("query is required unless --refresh-index is used")

    print(
        json.dumps(
            search(
                args.query,
                public_query=args.public_query,
                allow_public=args.allow_public,
                include_history=args.history,
                include_official=not args.no_official,
                limit=args.limit,
            ),
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
