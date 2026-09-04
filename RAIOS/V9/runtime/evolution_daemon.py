from __future__ import annotations

import json
import os
import threading
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from evolution_brain import WAL_FILE, atomic_json_write as atomic_json, process_all, status
from raios.search_cortex import SearchCortex

ROOT = Path.home() / ".raios" / "runtime" / "evolution-brain"
HEARTBEAT = ROOT / "heartbeat.json"
SUBCONSCIOUS_CONTEXT = ROOT / "subconscious-retrieval.json"
GAP_RESEARCH = ROOT / "capability-gap-research.json"
LOG = ROOT / "evolution.log"
LOCK = ROOT / ".instance.lock"
POLL_SECONDS = 2.0
FULL_REVIEW_SECONDS = 60.0
LIVENESS_SECONDS = 15.0
MAX_FAILURE_BACKOFF_SECONDS = 60.0
EXTERNAL_GAP_COOLDOWN_SECONDS = 21600.0
MIN_INTERNAL_EVIDENCE = 3


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(message: str) -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    with LOG.open("a", encoding="utf-8") as handle:
        handle.write(f"{now()} {message}\n")


def wal_signature() -> tuple[int, int]:
    try:
        st = WAL_FILE.stat()
        return st.st_size, st.st_mtime_ns
    except FileNotFoundError:
        return 0, 0


def acquire_single_instance():
    ROOT.mkdir(parents=True, exist_ok=True)
    handle = LOCK.open("a+b")
    try:
        import msvcrt

        handle.seek(0)
        if handle.read(1) == b"":
            handle.seek(0)
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    except ImportError:
        pass
    except OSError as exc:
        raise SystemExit("EVOLUTION_BRAIN_ALREADY_RUNNING") from exc
    return handle


def _load_json(path: Path, default: dict) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return default


def _internal_sufficient(result: dict) -> bool:
    verification = result.get("verification") or {}
    return bool(
        verification.get("status") == "PASS"
        and int(verification.get("evidence_count") or 0) >= MIN_INTERNAL_EVIDENCE
        and not (result.get("contradictions") or [])
    )


def _safe_gap_query(family: dict) -> str | None:
    geometry = family.get("geometry") or {}
    pieces = [
        str(geometry.get("tool") or ""),
        str(geometry.get("exception_type") or ""),
        *[str(x) for x in (geometry.get("unresolved_flags") or [])[:6]],
    ]
    clean = " ".join(x.strip() for x in pieces if x and x.strip())
    clean = " ".join(part for part in clean.split() if "\\" not in part and "/" not in part)
    return ("technical capability " + clean)[:300] if clean else None


def _external_gap_research(cortex: SearchCortex, family: dict, internal: dict) -> dict | None:
    query = _safe_gap_query(family)
    if not query:
        return None
    cache = _load_json(GAP_RESEARCH, {"schema": "raios.capability-gap-research.v1", "entries": {}})
    key = str(family.get("family_id") or query)
    old = (cache.get("entries") or {}).get(key) or {}
    try:
        old_at = datetime.fromisoformat(str(old.get("searched_at") or "").replace("Z", "+00:00"))
        if (datetime.now(timezone.utc) - old_at).total_seconds() < EXTERNAL_GAP_COOLDOWN_SECONDS:
            return old
    except (TypeError, ValueError):
        pass
    result = cortex.search(
        query,
        public_allowed=True,
        public_query=query,
        official_allowed=True,
        limit=6,
        deep=True,
        trace=False,
    )
    row = {
        "family_id": family.get("family_id"),
        "searched_at": now(),
        "query": query,
        "knowledge_state": "DISCOVERED",
        "canonical": False,
        "promoted": False,
        "internal_verification": internal.get("verification"),
        "external_verification": result.get("verification"),
        "sources": result.get("sources") or [],
        "results": (result.get("results") or [])[:6],
        "contradictions": result.get("contradictions") or [],
        "law": [
            "INTERNAL_FIRST",
            "EXTERNAL_ONLY_FOR_PROVEN_GAP",
            "EXTERNAL_RESULT_NE_CANONICAL",
            "C1_PROMOTION_REQUIRED",
        ],
    }
    cache.setdefault("entries", {})[key] = row
    cache["generated_at"] = now()
    atomic_json(GAP_RESEARCH, cache)
    return row


def build_subconscious_context() -> dict:
    brain = status()
    cortex = SearchCortex()
    contexts = []
    external_gaps = []
    families = list(brain.get("families") or [])
    families.sort(key=lambda x: x.get("last_seen") or "", reverse=True)
    for family in families[:5]:
        geometry = family.get("geometry") or {}
        query = " ".join(
            str(geometry.get(k) or "")
            for k in ("tool", "exception_type", "message")
        ).strip()
        flags = geometry.get("unresolved_flags") or []
        if flags:
            query += " " + " ".join(str(x) for x in flags)
        if not query:
            continue
        result = cortex.search(
            query,
            public_allowed=False,
            official_allowed=False,
            limit=5,
            deep=True,
            trace=False,
        )
        external = None
        if not _internal_sufficient(result):
            external = _external_gap_research(cortex, family, result)
            if external:
                external_gaps.append(external)
        contexts.append({
            "family_id": family.get("family_id"),
            "query": query,
            "mechanisms": result.get("mechanisms"),
            "results": result.get("results"),
            "internal_sufficient": _internal_sufficient(result),
            "external_gap_research": external,
        })
    payload = {
        "schema": "raios.subconscious-retrieval.v1",
        "generated_at": now(),
        "privacy": "LOCAL_PRIVATE_ONLY",
        "public_web_used": bool(external_gaps),
        "external_gap_count": len(external_gaps),
        "external_gap_research": external_gaps,
        "family_contexts": contexts,
        "shared_search_cortex": True,
        "second_memory_created": False,
        "search_policy": "INTERNAL_FIRST_THEN_EXTERNAL_GAP_ONLY",
        "automatic_canonical_promotion": False,
    }
    atomic_json(SUBCONSCIOUS_CONTEXT, payload)
    return payload


def write_heartbeat(*, state: str, last_result=None, error=None, search_context=None) -> None:
    brain = status()
    atomic_json(
        HEARTBEAT,
        {
            "schema": "raios.evolution-daemon-heartbeat.v1",
            "timestamp": now(),
            "state": state,
            "pid": os.getpid(),
            "poll_seconds": POLL_SECONDS,
            "wal": str(WAL_FILE),
            "wal_signature": wal_signature(),
            "evolution_status": brain,
            "last_result": last_result,
            "search_cortex": {
                "connected": True,
                "shared": True,
                "subconscious_context": str(SUBCONSCIOUS_CONTEXT),
                "family_context_count": len((search_context or {}).get("family_contexts", [])),
                "public_web_used": bool((search_context or {}).get("public_web_used", False)),
            },
            "error": error,
            "continuous_background_cognition": True,
            "canonical_auto_promotion": False,
        },
    )


def safe_write_heartbeat(**kwargs) -> bool:
    try:
        write_heartbeat(**kwargs)
        return True
    except BaseException as exc:
        try:
            log(f"heartbeat FAIL {type(exc).__name__}: {exc}")
        except BaseException:
            pass
        return False


def daemon() -> None:
    lock_handle = acquire_single_instance()
    _ = lock_handle
    log("Evolution Brain daemon started")
    last_sig = None
    last_full = 0.0
    last_result = None
    search_context = None
    failure_streak = 0
    pulse = {"state": "STARTING", "last_result": None, "search_context": None, "error": None}
    safe_write_heartbeat(state="STARTING")

    def publish_liveness() -> None:
        while True:
            time.sleep(LIVENESS_SECONDS)
            safe_write_heartbeat(
                state=str(pulse["state"]),
                last_result=pulse["last_result"],
                search_context=pulse["search_context"],
                error=pulse["error"],
            )

    threading.Thread(
        target=publish_liveness,
        name="RAIOS-Evolution-Liveness-Pulse",
        daemon=True,
    ).start()

    while True:
        sleep_seconds = POLL_SECONDS
        try:
            sig = wal_signature()
            sig_changed = sig != last_sig
            due_full = time.time() - last_full >= FULL_REVIEW_SECONDS
            if sig_changed or due_full:
                pulse.update(state="ACTIVE", error=None)
                started = time.perf_counter()
                last_result = process_all()
                last_result["latency_ms"] = round(
                    (time.perf_counter() - started) * 1000, 3
                )
                if due_full or search_context is None:
                    search_context = build_subconscious_context()
                    last_full = time.time()
                # Keep the pre-consumption signature. A real external append that
                # arrives during processing is observed on the next poll, while
                # internal retrieval is trace-free and cannot feed this loop.
                last_sig = sig
                failure_streak = 0
                pulse.update(
                    state="ACTIVE",
                    last_result=last_result,
                    search_context=search_context,
                    error=None,
                )
                safe_write_heartbeat(
                    state="ACTIVE",
                    last_result=last_result,
                    search_context=search_context,
                )
                log(
                    "consume PASS "
                    f"wal={last_result.get('wal_events')} "
                    f"new={last_result.get('processed_now')} "
                    f"patterns={last_result.get('experience_patterns')} "
                    f"skills={last_result.get('skill_candidates')} "
                    f"latency_ms={last_result.get('latency_ms')}"
                )
            else:
                pulse.update(
                    state="IDLE_COGNITION",
                    last_result=last_result,
                    search_context=search_context,
                    error=None,
                )
        except KeyboardInterrupt:
            safe_write_heartbeat(state="STOPPED", last_result=last_result)
            log("Evolution Brain daemon stopped")
            return
        except BaseException as exc:
            failure_streak += 1
            sleep_seconds = min(
                MAX_FAILURE_BACKOFF_SECONDS,
                POLL_SECONDS * (2 ** min(failure_streak - 1, 5)),
            )
            err = {
                "type": type(exc).__name__,
                "message": str(exc),
                "trace": traceback.format_exc(limit=6),
                "retry_in_seconds": sleep_seconds,
                "failure_streak": failure_streak,
            }
            pulse.update(state="DEGRADED", last_result=last_result, error=err)
            safe_write_heartbeat(
                state="DEGRADED",
                last_result=last_result,
                search_context=search_context,
                error=err,
            )
            try:
                log(
                    f"consume FAIL {err['type']}: {err['message']} "
                    f"retry_in={sleep_seconds}s"
                )
            except BaseException:
                pass
        time.sleep(sleep_seconds)


if __name__ == "__main__":
    daemon()

