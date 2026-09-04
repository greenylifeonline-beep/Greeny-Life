"""Closed cognitive loop for C5 live chat: retrieve Ã¢â€ â€™ ground Ã¢â€ â€™ respond Ã¢â€ â€™ assimilate.

Laws:
- STUDENT_NE_MAIN_CORTEX
- ABSORB_DIGEST_NE_WAL_DUMP
- LEARNING_CANDIDATE_NE_CANONICAL
- NO_SECOND_SEARCH_BUS (all retrieval goes through the shared Search Cortex)
- FAIL_OPEN_ON_RETRIEVAL (chat continues if grounding fails)
- KAE_REUSE_BEFORE_NEW_ASSIMILATOR (authorized output is re-tiled by existing KAE)
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import threading
import time
import uuid
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{2,}|[\u0600-\u06FF]{2,}")
STOP = {
    "the", "and", "for", "that", "this", "with", "from", "not", "are", "was",
    "json", "true", "false", "none", "Ã™â€¡Ã™â€ž", "Ã™â€¦Ã˜Â§", "Ã™ÂÃ™Å ", "Ã™â€¦Ã™â€ ", "Ã˜Â¹Ã™â€žÃ™â€°", "Ã˜Â¥Ã™â€žÃ™â€°",
}


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def _repo_root() -> Path:
    env = os.getenv("RAIOS_CANONICAL_REPO")
    if env:
        return Path(env).resolve()
    # Deployed C5 runtime keeps the source repo path in deployment.json
    runtime = Path(os.getenv("RAIOS_RUNTIME_ROOT", str(Path.home() / ".raios" / "runtime" / "c5")))
    manifest = runtime / "deployment.json"
    if manifest.is_file():
        try:
            obj = json.loads(manifest.read_text(encoding="utf-8-sig"))
            source = obj.get("source_repo")
            if source and (Path(source) / ".ai-os").is_dir():
                return Path(source).resolve()
        except Exception:
            pass
    # c5_gateway -> raios -> src -> repo (dev import path)
    candidate = Path(__file__).resolve().parents[3]
    if (candidate / ".ai-os").is_dir():
        return candidate
    return Path(r"C:\Users\Ghanam\Documents\Codex\Greeny-Life")


def learning_root(repo: Path | None = None) -> Path:
    if repo is not None:
        return repo / ".ai-os" / "learning"
    configured = os.getenv("RAIOS_LEARNING_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    cognitive_store = os.getenv("RAIOS_COGNITIVE_STORE_ROOT")
    if cognitive_store:
        return Path(cognitive_store).expanduser().resolve() / "learning"
    return _repo_root() / ".ai-os" / "learning"


def runtime_base() -> Path:
    configured = os.getenv("RAIOS_RUNTIME_BASE")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path.home() / ".raios" / "runtime"


def manager_root() -> Path:
    return runtime_base() / "manager"


def evolution_root() -> Path:
    return runtime_base() / "evolution-brain"


def tokens(text: str) -> list[str]:
    out: list[str] = []
    for match in TOKEN_RE.finditer(text or ""):
        tok = match.group(0).lower()
        if tok not in STOP and len(tok) >= 2:
            out.append(tok)
    return out


def _load_digests(path: Path, limit: int = 4000) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for raw in path.read_text(encoding="utf-8-sig").splitlines():
            if not raw.strip():
                continue
            try:
                rec = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if rec.get("status") == "DEDUPED":
                continue
            rows.append(rec)
            if len(rows) > limit:
                rows = rows[-limit:]
    except OSError:
        return []
    return rows


def _digest_score(rec: dict[str, Any], toks: list[str]) -> float:
    blob = " ".join(
        str(rec.get(k) or "")
        for k in ("path", "skim_head", "skim_tail", "law", "text", "prompt", "response")
    ).lower()
    score = 0.0
    for tok in toks:
        if tok in blob:
            score += 1.0 + (0.25 if tok in str(rec.get("path") or "").lower() else 0.0)
    return score


def _index_hits(index_path: Path, toks: list[str], limit: int) -> list[str]:
    if not index_path.is_file() or not toks:
        return []
    try:
        obj = json.loads(index_path.read_text(encoding="utf-8-sig"))
    except Exception:
        return []
    postings = obj.get("postings") if isinstance(obj, dict) else None
    if not isinstance(postings, dict):
        return []
    counts: dict[str, int] = {}
    for tok in toks[:24]:
        for doc_id in postings.get(tok, [])[:24]:
            counts[str(doc_id)] = counts.get(str(doc_id), 0) + 1
    ranked = sorted(counts.items(), key=lambda x: x[1], reverse=True)
    return [doc for doc, _ in ranked[:limit]]


def _sqlite_fts(query: str, limit: int) -> list[dict[str, Any]]:
    db_path = manager_root() / "retrieval.sqlite3"
    if not db_path.is_file():
        return []
    toks = tokens(query)[:12]
    if not toks:
        return []
    fts_q = " OR ".join(toks)
    try:
        db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=1)
        try:
            found = db.execute(
                "SELECT d.source_id,d.trust_class,d.text "
                "FROM docs_fts f JOIN docs d ON d.doc_id=f.doc_id "
                "WHERE docs_fts MATCH ? ORDER BY bm25(docs_fts) LIMIT ?",
                (fts_q, limit),
            ).fetchall()
        finally:
            db.close()
    except Exception:
        return []
    rows = []
    for source_id, trust, text in found:
        rows.append(
            {
                "source": "MANAGER_FTS",
                "source_id": source_id,
                "trust": trust or "DERIVED",
                "excerpt": str(text or "")[:800],
                "score": 2.0,
            }
        )
    return rows


def retrieve_grounding(query: str, *, limit: int = 6, timeout_ms: int = 2500) -> dict[str, Any]:
    """Fail-open retrieval through the one shared Search Cortex. Never writes WAL."""
    started = time.perf_counter()
    hits: list[dict[str, Any]] = []
    errors: list[str] = []
    search_meta: dict[str, Any] = {}
    try:
        from raios.search_cortex import SearchCortex

        result = SearchCortex().search(
            query,
            public_allowed=False,
            official_allowed=False,
            limit=limit,
            deep=False,
            trace=False,
        )
        search_meta = {
            "schema": result.get("schema"),
            "plan": result.get("plan"),
            "verification": result.get("verification"),
            "contradictions": result.get("contradictions") or [],
            "sources": result.get("sources") or [],
        }
        errors.extend(result.get("errors") or [])
        for row in (result.get("results") or [])[:limit]:
            hits.append({
                "source": row.get("source"),
                "path": row.get("path"),
                "source_id": row.get("source_id"),
                "sha256": row.get("sha256"),
                "trust": row.get("trust"),
                "trust_score": row.get("trust_score"),
                "freshness": row.get("freshness"),
                "excerpt": str(row.get("excerpt") or "")[:900],
                "score": row.get("score"),
                "evidence_id": row.get("evidence_id"),
                "citation": row.get("citation"),
            })
    except Exception as exc:
        errors.append(f"SEARCH_CORTEX::{type(exc).__name__}")

    return {
        "schema": "raios.grounding-envelope.v2",
        "generated_at": utc(),
        "query": query[:500],
        "count": len(hits),
        "results": hits,
        "receipts": [row.get("sha256") for row in hits if row.get("sha256")],
        "evidence_refs": [row.get("citation") for row in hits if row.get("citation")],
        "search": search_meta,
        "shared_search_cortex": True,
        "timeout_budget_ms": timeout_ms,
        "execution_claims_allowed": False,
        "gl005_proven": False,
        "wal_written": False,
        "latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
        "errors": errors,
        "law": [
            "GROUNDING_IS_LOCAL_TRUTH_FOR_TURN",
            "NO_EXECUTION_CLAIM_WITHOUT_RECEIPT",
            "NO_SECOND_SEARCH_BUS",
            "ABSORB_DIGEST_NE_WAL_DUMP",
        ],
    }


def format_grounded_user_message(text: str, envelope: dict[str, Any]) -> str:
    compact = {
        "schema": envelope.get("schema"),
        "generated_at": envelope.get("generated_at"),
        "count": envelope.get("count"),
        "execution_claims_allowed": False,
        "receipts": envelope.get("receipts") or [],
        "evidence_refs": envelope.get("evidence_refs") or [],
        "verification": (envelope.get("search") or {}).get("verification"),
        "contradictions": (envelope.get("search") or {}).get("contradictions") or [],
        "results": [
            {
                "evidence_id": r.get("evidence_id"),
                "source": r.get("source"),
                "path": r.get("path"),
                "citation": r.get("citation"),
                "trust": r.get("trust"),
                "freshness": r.get("freshness"),
                "excerpt": r.get("excerpt"),
            }
            for r in (envelope.get("results") or [])[:6]
        ],
    }
    return (
        "GROUNDING_ENVELOPE:\n"
        + json.dumps(compact, ensure_ascii=False, indent=2)
        + "\n\nUSER_MESSAGE:\n"
        + text
    )


_APPEND_LOCK = threading.Lock()


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    """Append one durable JSONL record without killing the chat path on transient I/O."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(row, ensure_ascii=False) + "\n"
    with _APPEND_LOCK:
        for attempt in range(4):
            try:
                with path.open("a", encoding="utf-8") as handle:
                    handle.write(payload)
                    handle.flush()
                    os.fsync(handle.fileno())
                return
            except PermissionError:
                if attempt == 3:
                    raise
                time.sleep(0.025 * (attempt + 1))


def _digest_exists(path: Path, digest_sha: str, limit: int = 5000) -> bool:
    if not path.is_file():
        return False
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            recent = deque(handle, maxlen=limit)
    except OSError:
        return False
    needle = f'"sha256": "{digest_sha}"'
    compact = f'"sha256":"{digest_sha}"'
    return any(needle in raw or compact in raw for raw in recent)


def assimilate_turn(
    *,
    prompt: str,
    response: str,
    conversation_id: str,
    model: str,
    grounding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Retile authorized output with existing KAE, then write DISCOVERED evidence."""
    repo = _repo_root()
    root = learning_root()
    digests = root / "DIGESTS.jsonl"
    candidates = root / "CANDIDATES.jsonl"
    cognitive_store = os.getenv("RAIOS_COGNITIVE_STORE_ROOT")
    wal = (
        Path(cognitive_store).expanduser().resolve() / "wal" / "cognitive-events.jsonl"
        if cognitive_store else repo / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
    )
    wal_before = wal.stat().st_mtime_ns if wal.exists() else None

    blob = f"{prompt}\n{response}"
    digest_sha = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    duplicate = _digest_exists(digests, digest_sha)
    kae: dict[str, Any]
    try:
        from raios.neuro_lingua.kae import assimilate as kae_assimilate

        kae = kae_assimilate(
            response,
            source_kind="authorized_text",
            external_calls=0,
            ingest=False,
        )
    except Exception as exc:
        kae = {
            "ok": False,
            "error": f"KAE::{type(exc).__name__}",
            "canonical": False,
            "promoted": False,
            "wal_written": False,
        }

    tiles = kae.get("tiles") if isinstance(kae.get("tiles"), dict) else {}
    replay = kae.get("replay") if isinstance(kae.get("replay"), dict) else {}
    contradictions = kae.get("contradictions") if isinstance(kae.get("contradictions"), list) else []
    evidence_refs = list((grounding or {}).get("evidence_refs") or [])
    digest = {
        "schema": "raios.absorb-digest.v2",
        "kind": "LIVE_CHAT_TURN",
        "path": f"live-chat/{conversation_id}/{digest_sha[:12]}",
        "sha256": digest_sha,
        "bytes": len(blob.encode("utf-8")),
        "status": "DEDUPED" if duplicate else "ABSORBED",
        "knowledge_state": "DISCOVERED",
        "prompt": prompt[:4000],
        "response": response[:4000],
        "text": blob[:4000],
        "skim_head": prompt[:500],
        "skim_tail": response[:500],
        "model": model,
        "conversation_id": conversation_id,
        "grounding_count": int((grounding or {}).get("count") or 0),
        "evidence_refs": evidence_refs[:20],
        "search_verification": ((grounding or {}).get("search") or {}).get("verification"),
        "kae": {
            "ok": bool(kae.get("ok")),
            "rule": tiles.get("RULE"),
            "invariant": tiles.get("INVARIANT"),
            "skill_candidate": tiles.get("SKILL_CANDIDATE"),
            "replayed": bool(replay.get("replayed")),
            "reused_on_unseen": int(replay.get("reused_on_unseen") or 0),
            "contradictions": contradictions,
        },
        "ts": utc(),
        "from": "C5",
        "wal_written": False,
        "gl005_proven": False,
        "law": ["ABSORB_DIGEST_NE_WAL_DUMP", "KAE_REUSE_BEFORE_NEW_ASSIMILATOR"],
    }
    if not duplicate:
        _append_jsonl(digests, digest)

    review_ready = bool(
        kae.get("ok")
        and replay.get("replayed")
        and not any(item.get("severity") == "HIGH" for item in contradictions)
    )
    candidate = {
        "schema": "raios.learning-candidate.v2",
        "id": str(uuid.uuid4()),
        "ts": utc(),
        "from": "C5",
        "source": "c5-live-cognitive-loop+existing-kae",
        "text": f"{tiles.get('RULE') or 'UNCLASSIFIED'}: {tiles.get('FACT') or response[:1000]}",
        "source_digest_sha256": digest_sha,
        "evidence_refs": [digest_sha, *evidence_refs][:24],
        "knowledge_state": "DISCOVERED",
        "review_state": "READY_FOR_VALIDATION" if review_ready else "NEEDS_REVIEW",
        "validation_gates": {
            "authorized_output": True,
            "kae_ok": bool(kae.get("ok")),
            "replayed": bool(replay.get("replayed")),
            "grounded": bool((grounding or {}).get("count")),
            "contradictions": len(contradictions),
            "duplicate": duplicate,
        },
        "skill_candidate": tiles.get("SKILL_CANDIDATE"),
        "validated": False,
        "promoted": False,
        "canonical": False,
        "wal_written": False,
        "gl005_proven": False,
        "law": "LEARNING_CANDIDATE_NE_CANONICAL",
    }
    candidate["receipt_sha256"] = hashlib.sha256(
        json.dumps(candidate, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()
    if not duplicate:
        _append_jsonl(candidates, candidate)

    if not duplicate:
        try:
            _bump_index(root / "INDEX.json", digest)
        except Exception:
            pass

    wal_after = wal.stat().st_mtime_ns if wal.exists() else None
    if wal_before != wal_after:
        raise RuntimeError("ASSIMILATE_WAL_VIOLATION")

    return {
        "schema": "raios.assimilate-turn.v2",
        "digest_sha256": digest_sha,
        "candidate_id": None if duplicate else candidate["id"],
        "duplicate": duplicate,
        "kae_ok": bool(kae.get("ok")),
        "replayed": bool(replay.get("replayed")),
        "review_state": "DEDUPED" if duplicate else candidate["review_state"],
        "skill_candidate": tiles.get("SKILL_CANDIDATE"),
        "wal_written": False,
        "gl005_proven": False,
        "promoted": False,
        "canonical": False,
        "at": utc(),
    }


def _bump_index(index_path: Path, digest: dict[str, Any]) -> None:
    postings: dict[str, list[str]] = {}
    docs = 0
    if index_path.is_file():
        try:
            obj = json.loads(index_path.read_text(encoding="utf-8-sig"))
            if isinstance(obj, dict):
                postings = {str(k): list(v) for k, v in (obj.get("postings") or {}).items() if isinstance(v, list)}
                docs = int(obj.get("docs") or 0)
        except Exception:
            postings = {}
            docs = 0
    docs += 1
    doc_id = str(digest.get("sha256"))
    blob = " ".join(
        str(digest.get(k) or "")
        for k in ("path", "skim_head", "skim_tail", "law", "text", "prompt", "response")
    )
    for tok in set(tokens(blob)):
        bucket = postings.setdefault(tok, [])
        if doc_id not in bucket and len(bucket) < 24:
            bucket.append(doc_id)
    payload = {
        "schema": "raios.c5-index.v1",
        "generated_at": utc(),
        "docs": docs,
        "terms": len(postings),
        "embedding_model": False,
        "postings": postings,
        "law": "INVERTED_INDEX_NE_UNLOADED_EMBEDDING",
    }
    index_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = index_path.with_name(f"{index_path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex}")
    try:
        tmp.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
        json.loads(tmp.read_text(encoding="utf-8"))
        for attempt in range(5):
            try:
                os.replace(tmp, index_path)
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


def _process_alive(pid: Any) -> bool:
    try:
        process_id = int(pid)
    except (TypeError, ValueError):
        return False
    if process_id <= 0:
        return False
    if os.name == "nt":
        try:
            import ctypes

            handle = ctypes.windll.kernel32.OpenProcess(0x1000, False, process_id)
            if not handle:
                return False
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        except Exception:
            return False
    try:
        os.kill(process_id, 0)
        return True
    except OSError:
        return False


def manager_liveness(stale_after_seconds: float = 120.0) -> dict[str, Any]:
    root = manager_root()
    stable = root / "heartbeat.json"
    candidates = [stable] if stable.is_file() else []
    candidates.extend(root.glob("heartbeat.live-*.json"))
    if not candidates:
        return {"alive": False, "age_seconds": None, "reason": "HEARTBEAT_MISSING"}

    parsed: list[tuple[datetime, dict[str, Any], Path]] = []
    last_error: Exception | None = None
    for heartbeat in candidates[:20]:
        try:
            obj = json.loads(heartbeat.read_text(encoding="utf-8-sig"))
            ts = str(obj.get("generated_at") or obj.get("at") or "")
            instant = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            parsed.append((instant, obj, heartbeat))
        except Exception as exc:
            last_error = exc
            continue
    if not parsed:
        return {
            "alive": False,
            "age_seconds": None,
            "reason": (
                f"{type(last_error).__name__}:{last_error}"
                if last_error else "HEARTBEAT_UNREADABLE"
            ),
        }

    instant, obj, heartbeat = max(parsed, key=lambda row: row[0])
    age = (datetime.now(timezone.utc) - instant).total_seconds()
    process_id = obj.get("manager_pid")
    process_alive = _process_alive(process_id)
    age_current = -300.0 <= age <= stale_after_seconds
    alive = age_current and process_alive
    return {
        "alive": alive,
        "age_seconds": round(max(0.0, age), 3),
        "generated_at": instant.isoformat(),
        "state": obj.get("state") or "RUNNING",
        "manager_pid": process_id,
        "process_alive": process_alive,
        "heartbeat_file": heartbeat.name,
        "single_cognitive_wal": obj.get("single_cognitive_wal"),
        "reason": (
            "OK" if alive else
            "PROCESS_MISSING" if not process_alive else
            "STALE"
        ),
    }


def evolution_liveness(stale_after_seconds: float = 120.0) -> dict[str, Any]:
    heartbeat = evolution_root() / "heartbeat.json"
    if not heartbeat.is_file():
        return {"alive": False, "age_seconds": None, "reason": "HEARTBEAT_MISSING"}
    try:
        obj = json.loads(heartbeat.read_text(encoding="utf-8-sig"))
        instant = datetime.fromisoformat(str(obj.get("timestamp") or "").replace("Z", "+00:00"))
    except Exception as exc:
        return {
            "alive": False,
            "age_seconds": None,
            "reason": f"HEARTBEAT_UNREADABLE:{type(exc).__name__}",
        }

    age = (datetime.now(timezone.utc) - instant).total_seconds()
    process_id = obj.get("pid")
    process_alive = _process_alive(process_id)
    state = str(obj.get("state") or "UNKNOWN")
    state_current = state in {"ACTIVE", "IDLE_COGNITION"}
    wal = str(obj.get("wal") or "")
    configured_root = os.getenv("RAIOS_COGNITIVE_STORE_ROOT")
    expected_wal = str(Path(configured_root).expanduser().resolve() / "wal" / "cognitive-events.jsonl") if configured_root else wal
    wal_matches = bool(wal) and Path(wal).resolve() == Path(expected_wal).resolve()
    age_current = -300.0 <= age <= stale_after_seconds
    alive = process_alive and state_current and age_current and wal_matches
    return {
        "alive": alive,
        "age_seconds": round(max(0.0, age), 3),
        "generated_at": instant.isoformat(),
        "state": state,
        "pid": process_id,
        "process_alive": process_alive,
        "wal": wal,
        "expected_wal": expected_wal,
        "single_wal": wal_matches,
        "reason": (
            "OK" if alive else
            "PROCESS_MISSING" if not process_alive else
            "BAD_STATE" if not state_current else
            "WAL_MISMATCH" if not wal_matches else
            "STALE"
        ),
    }


def _jsonl_summary(path: Path, *, limit: int = 5000) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False, "records_observed": 0, "states": {}, "review_states": {}}
    states: Counter[str] = Counter()
    reviews: Counter[str] = Counter()
    schemas: Counter[str] = Counter()
    observed = 0
    invalid = 0
    try:
        with path.open("r", encoding="utf-8-sig", errors="replace") as handle:
            recent = deque(handle, maxlen=limit)
        for raw in recent:
            try:
                row = json.loads(raw)
            except json.JSONDecodeError:
                invalid += 1
                continue
            observed += 1
            states[str(row.get("knowledge_state") or row.get("status") or "UNKNOWN")] += 1
            reviews[str(row.get("review_state") or "UNREVIEWED")] += 1
            schemas[str(row.get("schema") or "UNKNOWN")] += 1
    except OSError:
        return {"exists": True, "records_observed": 0, "states": {}, "review_states": {}, "read_error": True}
    return {
        "exists": True,
        "records_observed": observed,
        "invalid_records": invalid,
        "states": dict(states),
        "review_states": dict(reviews),
        "schemas": dict(schemas),
        "window_limit": limit,
    }


def loop_status() -> dict[str, Any]:
    root = learning_root()
    digests = root / "DIGESTS.jsonl"
    candidates = root / "CANDIDATES.jsonl"
    index = root / "INDEX.json"
    mgr = manager_liveness()
    evolution = evolution_liveness()
    digest_summary = _jsonl_summary(digests)
    candidate_summary = _jsonl_summary(candidates)
    maintenance_receipt_path = runtime_base() / "c5" / "maintenance-assimilation.json"
    maintenance_receipt: dict[str, Any] = {}
    if maintenance_receipt_path.is_file():
        try:
            maintenance_receipt = json.loads(maintenance_receipt_path.read_text(encoding="utf-8-sig"))
        except Exception:
            maintenance_receipt = {}
    maintenance_results = maintenance_receipt.get("results") if isinstance(maintenance_receipt.get("results"), list) else []
    maintenance_ready = sum(1 for row in maintenance_results if row.get("review_state") in {"READY_FOR_VALIDATION", "DEDUPED"})
    closed = bool(
        mgr.get("alive") and evolution.get("alive") and
        digests.is_file() and candidates.is_file() and index.is_file()
    )
    return {
        "schema": "raios.cognitive-loop.status.v3",
        "at": utc(),
        "closed_loop": closed,
        "planes": {
            "retrieve": True,
            "ground": True,
            "student_chat": True,
            "assimilate": True,
            "index": index.is_file(),
            "continuous_manager": bool(mgr.get("alive")),
            "continuous_evolution": bool(evolution.get("alive")),
        },
        "artifacts": {
            "digests_exist": digests.is_file(),
            "candidates_exist": candidates.is_file(),
            "index_exist": index.is_file(),
            "digests_bytes": digests.stat().st_size if digests.is_file() else 0,
            "digests": digest_summary,
            "candidates": candidate_summary,
        },
        "search_cortex": {"shared": True, "second_search_bus": False},
        "assimilation": {"existing_kae_reused": True, "auto_canonical_promotion": False},
        "maintenance_assimilation": {
            "receipt_present": maintenance_receipt_path.is_file(),
            "law_count": int(maintenance_receipt.get("law_count") or 0),
            "ready_or_deduped": maintenance_ready,
            "all_wal_clean": bool(maintenance_receipt.get("all_wal_clean")),
            "complete": bool(maintenance_receipt.get("law_count")) and maintenance_ready == int(maintenance_receipt.get("law_count") or 0),
            "receipt": str(maintenance_receipt_path),
        },
        "manager": mgr,
        "evolution": evolution,
        "cognitive_store": {
            "root": os.getenv("RAIOS_COGNITIVE_STORE_ROOT"),
            "learning_root": str(learning_root()),
            "single_wal": bool(evolution.get("single_wal")),
            "outside_git": bool(
                os.getenv("RAIOS_COGNITIVE_STORE_ROOT") and
                not Path(os.environ["RAIOS_COGNITIVE_STORE_ROOT"]).resolve().is_relative_to(_repo_root()) and
                not learning_root().resolve().is_relative_to(_repo_root())
            ),
        },
        "main_cortex_identity": "qwen3.6:35b-a3b",
        "main_cortex_state": "HOLD",
        "student_env": os.getenv("RAIOS_STUDENT_MODEL") or os.getenv("RAIOS_MAIN_CORTEX") or "qwen3:0.6b",
        "law": [
            "STUDENT_NE_MAIN_CORTEX",
            "ABSORB_DIGEST_NE_WAL_DUMP",
            "LEARNING_CANDIDATE_NE_CANONICAL",
            "NO_SECOND_SEARCH_BUS",
            "KAE_REUSE_BEFORE_NEW_ASSIMILATOR",
        ],
    }
