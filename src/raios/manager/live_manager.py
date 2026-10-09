from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from array import array
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from raios.orchestration.tasks_write import load_tasks_document, replace_tasks_document, StaleTasksWriteError

def maintenance_observation(path: Path, now: datetime | None = None) -> tuple[bool, dict[str, Any]]:
    """Bounded observation of existing continuity state; no execution authority."""
    try:
        if path.stat().st_size > 1048576:
            return False, {"reason": "OVERSIZED"}
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        stamp = data.get("generated_at") or data.get("observed_at") or data.get("timestamp")
        at = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
        age = ((now or datetime.now(timezone.utc)) - at).total_seconds()
        if not 0 <= age <= 900:
            return False, {"reason": "STALE_OR_FUTURE"}
        services = data.get("services", {})
        if not isinstance(services, dict):
            return False, {"reason": "INVALID_SERVICES"}
        # Semantic content excludes heartbeat times, PIDs and raw logs.
        payload = {"status": str(data.get("status", "UNKNOWN")),
                   "services": {str(k): v for k, v in services.items() if isinstance(v, bool)},
                   "observation_only": True, "engine_execution_proven": False}
        context = data.get("maintenance_context", {})
        if isinstance(context, dict):
            payload["capability_context"] = {
                "inventory_alignment": context.get("inventory_alignment", "UNKNOWN"),
                "routing_authority": context.get("routing_authority"),
                "engines": [{k: row.get(k) for k in ("id", "role", "activation_mode", "state", "health_source", "freshness", "execution_proven", "historical_execution_evidence")}
                            for row in context.get("engines", [])[:25] if isinstance(row, dict)],
                "automatic_inventory_execution": False,
            }
        return True, payload
    except (OSError, ValueError, TypeError):
        return False, {"reason": "UNAVAILABLE_OR_INVALID"}


# Metrics collector
class MetricsCollector:
    """Thread-safe metrics with Prometheus-style exposition."""
    
    def __init__(self):
        from collections import defaultdict
        self._counters = {}
        self._gauges = {}
        self._histograms = {}
        self._lock = threading.RLock()
        self._start_time = time.time()
    
    def inc(self, name: str, value: float = 1.0, labels = None):
        key = self._make_key(name, labels)
        with self._lock:
            self._counters[key] = self._counters.get(key, 0) + value
    
    def gauge(self, name: str, value: float, labels = None):
        key = self._make_key(name, labels)
        with self._lock:
            self._gauges[key] = value
    
    def observe(self, name: str, value: float, labels = None):
        key = self._make_key(name, labels)
        with self._lock:
            self._histograms[key] = self._histograms.get(key, []) + [value]
            if len(self._histograms[key]) > 1000:
                self._histograms[key] = self._histograms[key][-1000:]
    
    def _make_key(self, name: str, labels) -> str:
        if not labels:
            return name
        label_str = ",".join(f'{k}="{v}"' for k, v in sorted(labels.items()))
        return f'{name}{{{label_str}}}'
    
    def snapshot(self):
        with self._lock:
            return {
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
                "histograms": {k: {"count": len(v), "sum": sum(v), "min": min(v), "max": max(v)} 
                              for k, v in self._histograms.items() if v},
                "uptime_seconds": time.time() - getattr(self, '_start_time', time.time()),
            }

metrics = MetricsCollector()

metrics = MetricsCollector()

class StructuredLogger:
    """Structured JSON logger with context propagation."""
    _level = 20  # INFO
    _lock = threading.Lock()
    
    @classmethod
    def set_level(cls, level: int):
        cls._level = level
    
    @classmethod
    def _log(cls, level: int, message: str, **kwargs):
        if level < cls._level:
            return
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"][level // 10] if level in [10, 20, 30, 40, 50] else "UNKNOWN",
            "logger": "live_manager",
            "message": message,
            "context": kwargs,
            "pid": os.getpid(),
            "thread": threading.get_ident(),
        }
        with cls._lock:
            print(json.dumps(entry, ensure_ascii=False), file=sys.stdout)
            MANAGER_ROOT.mkdir(parents=True, exist_ok=True)
            with LOG_FILE.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    @classmethod
    def debug(cls, msg: str, **kw): cls._log(10, msg, **kw)
    @classmethod
    def info(cls, msg: str, **kw): cls._log(20, msg, **kw)
    @classmethod
    def warning(cls, msg: str, **kw): cls._log(30, msg, **kw)
    @classmethod
    def error(cls, msg: str, **kw): cls._log(40, msg, **kw)
    @classmethod
    def critical(cls, msg: str, **kw): cls._log(50, msg, **kw)

CREATE_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


# MessageWorker availability
try:
    from raios.command_center.message_worker import (
    MessageWorker,
    MessagePriority,
    MessageType,
    EngineState,
    EngineDescriptor,
)
    MESSAGE_WORKER_AVAILABLE = True
except ImportError:
    MESSAGE_WORKER_AVAILABLE = False


def windowless_startupinfo():
    if os.name != "nt":
        return None
    info = subprocess.STARTUPINFO()
    info.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    info.wShowWindow = subprocess.SW_HIDE
    return info


REPO = Path(__file__).resolve().parents[3]
USER_PROFILE = Path(os.getenv("RAIOS_USER_PROFILE", os.getenv("USERPROFILE", str(Path.home())))).expanduser().resolve()
RUNTIME_BASE = Path(os.getenv("RAIOS_RUNTIME_BASE", str(USER_PROFILE / ".raios" / "runtime"))).expanduser().resolve()
SRC = REPO / "src"
V9_RUNTIME = REPO / "RAIOS" / "V9" / "runtime"
if str(V9_RUNTIME) not in sys.path:
    sys.path.insert(0, str(V9_RUNTIME))

from cognitive_event_bus import WAL_FILE, build_event, emit_event
from raios.council_ops.operations import _live as council_presence_live
from raios.search_cortex import SearchCortex

TASKS = REPO / ".ai-os" / "state" / "TASKS.json"
LOCKS = REPO / ".ai-os" / "state" / "LOCKS.json"
MAIL_INBOX = REPO / ".ai-os" / "mail" / "INBOX.jsonl"
MAIL_RECEIPT = REPO / ".ai-os" / "mail" / "COLLECT-RECEIPT.json"
FACTORY_LATEST = RUNTIME_BASE / "factory-fabric" / "FACTORY-FABRIC-LATEST.json"
COUNCIL_PRESENCE = RUNTIME_BASE / "council-ops" / "presence.json"
MANAGER_ROOT = RUNTIME_BASE / "manager"
HEARTBEAT = MANAGER_ROOT / "heartbeat.json"
STATE = MANAGER_ROOT / "state.json"
SOURCE_SNAPSHOT = MANAGER_ROOT / "source-snapshot.json"
RESOURCE_LIVE = MANAGER_ROOT / "resource-live.json"
GITHUB_LIVE = MANAGER_ROOT / "github-live.json"
ANALYSIS = MANAGER_ROOT / "analysis.json"
INDEX_DB = MANAGER_ROOT / "retrieval.sqlite3"
LOG_FILE = MANAGER_ROOT / "live-manager.log"
INSTANCE_LOCK = MANAGER_ROOT / ".instance.lock"

C5_HEALTH = "http://127.0.0.1:8766/health"
C5_CHAT = "http://127.0.0.1:8766/v1/chat"
CC_HEALTH = "http://127.0.0.1:8770/health"
EVOLUTION_HEARTBEAT = RUNTIME_BASE / "evolution-brain" / "heartbeat.json"
OLLAMA_TAGS = "http://127.0.0.1:11434/api/tags"
OLLAMA_EMBED = "http://127.0.0.1:11434/api/embed"
EMBED_MODEL = "qwen3-embedding:0.6b"

LOCAL_TICK_SECONDS = 15.0
MAIL_REFRESH_SECONDS = 20.0
GITHUB_REFRESH_SECONDS = 30.0
RESOURCE_REFRESH_SECONDS = 90.0
SEARCH_REFRESH_SECONDS = 300.0
EMBED_REFRESH_SECONDS = 60.0
OFFICIAL_REFRESH_SECONDS = 900.0
FACTORY_REFRESH_SECONDS = 1800.0
REASON_SECONDS = 15.0
REASON_RETRY_SECONDS = 300.0
EVOLUTION_SECONDS = 10.0

MANAGER_ACTOR = "RAIOS-MANAGER"
C1_AUTHORITY = "C1 direct instruction: RAIOS is the executive manager and owns canonical work-list generation."


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(message: str) -> None:
    MANAGER_ROOT.mkdir(parents=True, exist_ok=True)
    line = f"{utc()} {message}"
    with LOG_FILE.open("a", encoding="utf-8") as handle:
        handle.write(line + "\n")


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def load_jsonl(path: Path, limit: int = 100) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            for raw in handle:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    rows.append(json.loads(raw))
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    return rows[-limit:]


def atomic_json(path: Path, value: Any) -> None:
    """Validated atomic replace resilient to transient Windows reader locks."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    try:
        tmp.write_text(
            json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        json.loads(tmp.read_text(encoding="utf-8"))
        for attempt in range(8):
            try:
                os.replace(tmp, path)
                return
            except PermissionError:
                if attempt == 7:
                    raise
                time.sleep(0.025 * (attempt + 1))
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


def write_heartbeat(value: dict[str, Any]) -> Path:
    """Publish one live heartbeat with a stable projection on Windows.

    The unique live snapshot is the durable fallback. The stable filename is a
    projection for legacy readers and must never block manager progress.
    """
    live = HEARTBEAT.with_name(
        f"heartbeat.live-{os.getpid()}-{time.time_ns()}.json"
    )
    atomic_json(live, value)
    written = live
    try:
        atomic_json(HEARTBEAT, value)
        written = HEARTBEAT
    except PermissionError:
        # A reader may deny DELETE sharing and therefore block os.replace while
        # still permitting an in-place rewrite. Keep this best-effort and never
        # let projection publication stall the manager tick.
        try:
            payload = json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n"
            with HEARTBEAT.open("w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            json.loads(HEARTBEAT.read_text(encoding="utf-8"))
            written = HEARTBEAT
        except (OSError, PermissionError, json.JSONDecodeError):
            written = live
    try:
        versions: list[tuple[int, Path]] = []
        with os.scandir(HEARTBEAT.parent) as entries:
            for entry in entries:
                if not entry.is_file(follow_symlinks=False):
                    continue
                if not (entry.name.startswith("heartbeat.live-") and entry.name.endswith(".json")):
                    continue
                versions.append(
                    (entry.stat(follow_symlinks=False).st_mtime_ns, Path(entry.path))
                )
                if len(versions) >= 32:
                    break
        versions.sort(key=lambda item: item[0], reverse=True)
        for _, stale in versions[12:]:
            stale.unlink(missing_ok=True)
    except OSError:
        pass

    # Keep fallback publishing bounded. Transient Windows reader locks can
    # leave temp projections behind; they are never authority and must not
    # accumulate or become an input to health decisions.
    try:
        cutoff_ns = time.time_ns() - 120 * 1_000_000_000
        seen = 0
        for candidate in HEARTBEAT.parent.glob("heartbeat.json.tmp-*"):
            if seen >= 64:
                break
            seen += 1
            try:
                if candidate.stat().st_mtime_ns < cutoff_ns:
                    candidate.unlink(missing_ok=True)
            except OSError:
                pass
    except OSError:
        pass
    return written


def sha(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def sanitize(value: Any) -> Any:
    secret_keys = ("token", "secret", "password", "cookie", "authorization", "private_key")
    if isinstance(value, dict):
        out = {}
        for key, val in value.items():
            if any(x in str(key).lower() for x in secret_keys):
                out[key] = "***REDACTED***"
            else:
                out[key] = sanitize(val)
        return out
    if isinstance(value, list):
        return [sanitize(x) for x in value]
    if isinstance(value, str):
        value = re.sub(r"(?i)(gh[opusr]_[A-Za-z0-9_\-]{8,}|sk-[A-Za-z0-9_\-]{8,}|hf_[A-Za-z0-9_\-]{8,})", "***REDACTED***", value)
    return value


VOLATILE_OBSERVATION_KEYS = {
    "latency_ms",
    "duration_ms",
    "elapsed_ms",
    "generated_at",
    "checked_at",
    "observed_at",
    "updated_at",
    "timestamp",
    "at",
    "age_seconds",
    "checked_in_at",
    "last_seen",
    "lease_expires_at",
    "receipt",
}


def semantic_observation(value: Any) -> Any:
    """Remove transport telemetry while preserving operational state changes."""
    if isinstance(value, dict):
        return {
            key: semantic_observation(item)
            for key, item in value.items()
            if str(key).lower() not in VOLATILE_OBSERVATION_KEYS
        }
    if isinstance(value, list):
        return [semantic_observation(item) for item in value]
    return sanitize(value)


def safe_council_presence_live(row: Any) -> bool:
    try:
        return bool(council_presence_live(row))
    except (AttributeError, TypeError, ValueError):
        return False


def http_json(url: str, timeout: float = 1.5) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "RAIOS-Live-Manager/1.0"})
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(1000000)
            body = json.loads(raw.decode("utf-8", errors="replace")) if raw[:1] in (b"{", b"[") else {}
            return {
                "live": resp.status == 200,
                "http_status": resp.status,
                "latency_ms": round((time.perf_counter() - started) * 1000, 3),
                "body": sanitize(body),
            }
    except Exception as exc:
        return {
            "live": False,
            "http_status": None,
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "error": type(exc).__name__,
        }


def run(args: list[str], timeout: float = 8.0, cwd: Path | None = None) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            args,
            cwd=cwd or REPO,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
            creationflags=CREATE_NO_WINDOW,
            startupinfo=windowless_startupinfo(),
        )
        return {
            "ok": proc.returncode == 0,
            "code": proc.returncode,
            "stdout": sanitize((proc.stdout or "")[-12000:]),
            "stderr": sanitize((proc.stderr or "")[-4000:]),
        }
    except Exception as exc:
        return {"ok": False, "code": None, "error": type(exc).__name__}


@dataclass
class Source:
    source_id: str
    access_class: str
    authority_class: str
    trust_class: str
    live: bool
    freshness: str
    payload: Any
    evidence: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "access_class": self.access_class,
            "authority_class": self.authority_class,
            "trust_class": self.trust_class,
            "live": self.live,
            "freshness": self.freshness,
            "payload": sanitize(self.payload),
            "evidence": self.evidence,
        }

    def semantic_dict(self) -> dict[str, Any]:
        """Stable state used for change events, retrieval and reasoning identity."""
        return semantic_observation(self.as_dict())


class HybridMemory:
    def __init__(self, path: Path = INDEX_DB):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("PRAGMA synchronous=NORMAL")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS docs (doc_id TEXT PRIMARY KEY, source_id TEXT, access_class TEXT, trust_class TEXT, updated_at TEXT, content_hash TEXT, text TEXT)"
        )
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS embeddings (doc_id TEXT PRIMARY KEY, model TEXT, dims INTEGER, vector BLOB, content_hash TEXT)"
        )
        try:
            self.db.execute("CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(doc_id UNINDEXED, text)")
            self.fts = True
        except sqlite3.OperationalError:
            self.fts = False
        self.db.commit()

    def _embed(self, texts: list[str]) -> list[list[float]] | None:
        if not texts:
            return []
        payload = json.dumps({"model": EMBED_MODEL, "input": texts}).encode("utf-8")
        req = urllib.request.Request(OLLAMA_EMBED, data=payload, method="POST", headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                obj = json.loads(resp.read(5000000).decode("utf-8"))
                rows = obj.get("embeddings")
                if isinstance(rows, list) and len(rows) == len(texts):
                    return rows
        except Exception:
            return None
        return None

    def upsert(self, docs: list[dict[str, str]], embed_limit: int = 16) -> dict[str, int]:
        changed: list[dict[str, str]] = []
        for doc in docs:
            h = hashlib.sha256(doc["text"].encode("utf-8", errors="replace")).hexdigest()
            row = self.db.execute("SELECT content_hash FROM docs WHERE doc_id=?", (doc["doc_id"],)).fetchone()
            if row and row[0] == h:
                continue
            self.db.execute(
                "INSERT INTO docs(doc_id,source_id,access_class,trust_class,updated_at,content_hash,text) VALUES(?,?,?,?,?,?,?) "
                "ON CONFLICT(doc_id) DO UPDATE SET source_id=excluded.source_id,access_class=excluded.access_class,trust_class=excluded.trust_class,updated_at=excluded.updated_at,content_hash=excluded.content_hash,text=excluded.text",
                (doc["doc_id"], doc["source_id"], doc["access_class"], doc["trust_class"], utc(), h, doc["text"]),
            )
            if self.fts:
                self.db.execute("DELETE FROM docs_fts WHERE doc_id=?", (doc["doc_id"],))
                self.db.execute("INSERT INTO docs_fts(doc_id,text) VALUES(?,?)", (doc["doc_id"], doc["text"]))
            changed.append({**doc, "content_hash": h})
        self.db.commit()

        selected = changed[:embed_limit]
        vectors = self._embed([x["text"][:6000] for x in selected])
        embedded = 0
        if vectors is not None:
            for doc, vec in zip(selected, vectors):
                try:
                    blob = array("f", [float(x) for x in vec]).tobytes()
                    self.db.execute(
                        "INSERT INTO embeddings(doc_id,model,dims,vector,content_hash) VALUES(?,?,?,?,?) "
                        "ON CONFLICT(doc_id) DO UPDATE SET model=excluded.model,dims=excluded.dims,vector=excluded.vector,content_hash=excluded.content_hash",
                        (doc["doc_id"], EMBED_MODEL, len(vec), blob, doc["content_hash"]),
                    )
                    embedded += 1
                except Exception:
                    continue
            self.db.commit()
        return {"changed": len(changed), "embedded": embedded}

    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        if not a or not b or len(a) != len(b):
            return -1.0
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(y * y for y in b))
        return dot / (na * nb) if na and nb else -1.0

    def query(self, query: str, limit: int = 12) -> list[dict[str, Any]]:
        ranks: dict[str, float] = {}
        if self.fts:
            tokens = re.findall(r"[A-Za-z0-9_\-]+", query)
            fts_q = " OR ".join(tokens[:16])
            if fts_q:
                try:
                    rows = self.db.execute(
                        "SELECT doc_id,bm25(docs_fts) AS score FROM docs_fts WHERE docs_fts MATCH ? ORDER BY score LIMIT 30",
                        (fts_q,),
                    ).fetchall()
                    for rank, (doc_id, _) in enumerate(rows, start=1):
                        ranks[doc_id] = ranks.get(doc_id, 0.0) + 1.0 / (60 + rank)
                except sqlite3.OperationalError:
                    pass

        qvecs = self._embed([query[:4000]])
        if qvecs:
            qvec = qvecs[0]
            sims: list[tuple[str, float]] = []
            for doc_id, dims, blob in self.db.execute("SELECT doc_id,dims,vector FROM embeddings WHERE model=?", (EMBED_MODEL,)):
                try:
                    vec = array("f")
                    vec.frombytes(blob)
                    if len(vec) == dims:
                        sims.append((doc_id, self._cosine(qvec, list(vec))))
                except Exception:
                    continue
            sims.sort(key=lambda x: x[1], reverse=True)
            for rank, (doc_id, _) in enumerate(sims[:50], start=1):
                ranks[doc_id] = ranks.get(doc_id, 0.0) + 1.0 / (60 + rank)

        ordered = sorted(ranks.items(), key=lambda x: x[1], reverse=True)[:limit]
        out = []
        for doc_id, score in ordered:
            row = self.db.execute(
                "SELECT source_id,access_class,trust_class,text FROM docs WHERE doc_id=?", (doc_id,)
            ).fetchone()
            if row:
                out.append({
                    "doc_id": doc_id,
                    "source_id": row[0],
                    "access_class": row[1],
                    "trust_class": row[2],
                    "score": round(score, 6),
                    "text": row[3][:3000],
                })
        return out


class LiveManager:
    def __init__(
        self,
        allow_task_write: bool = True,
        enable_refreshes: bool = True,
        enable_reasoning: bool = True,
        message_worker: Optional[Any] = None,
    ):
        MANAGER_ROOT.mkdir(parents=True, exist_ok=True)
        self.allow_task_write = allow_task_write
        self.enable_refreshes = enable_refreshes
        self.enable_reasoning = enable_reasoning
        self.message_worker = message_worker
        self._mw_integration_enabled = MESSAGE_WORKER_AVAILABLE and message_worker is not None
        if self._mw_integration_enabled:
            self._register_manager_engines()
            self._register_manager_circuit_breakers()
            log("MessageWorker integration enabled")
        else:
            log("MessageWorker integration disabled" + (" (not available)" if not MESSAGE_WORKER_AVAILABLE else " (not provided)"))
        self.state = load_json(STATE, {
            "schema": "raios.manager-state.v1",
            "last_hashes": {},
            "last_runs": {},
            "manager_authority": C1_AUTHORITY,
        })
        self.memory = HybridMemory()
        self.search_cortex = SearchCortex()
        self._reason_lock = threading.Lock()
        self._reason_inflight = False
        self._search_refresh_process: subprocess.Popen[Any] | None = None
        self._refresh_processes: dict[str, subprocess.Popen[Any]] = {}
        self._evolution_recovery_process: subprocess.Popen[Any] | None = None
        self._evolution_recovery_attempt = 0
        self._evolution_recovery_next_at = 0.0
        self._evolution_was_down = False
        self._evolution_recovery_lock = threading.Lock()

    def _register_manager_engines(self) -> None:
        """Register core system engines with MessageWorker for health tracking."""
        if not self._mw_integration_enabled:
            return
        
        # Register C5 engine
        self.message_worker.register_engine(EngineDescriptor(
            engine_id="c5_brain",
            engine_type="reasoning_engine",
            endpoint=C5_CHAT,
            health_check=lambda: http_json(C5_HEALTH, 2.0).get("live", False),
            dependencies=["ollama"],
            metadata={"critical": True, "endpoint": C5_HEALTH}
        ))
        
        # Register Command Center engine
        self.message_worker.register_engine(EngineDescriptor(
            engine_id="command_center",
            engine_type="api_gateway",
            endpoint=CC_HEALTH,
            health_check=lambda: http_json(CC_HEALTH, 2.0).get("live", False),
            metadata={"critical": True, "endpoint": CC_HEALTH}
        ))
        
        # Register Ollama engine
        self.message_worker.register_engine(EngineDescriptor(
            engine_id="ollama",
            engine_type="model_server",
            endpoint=OLLAMA_TAGS,
            health_check=lambda: http_json(OLLAMA_TAGS, 3.0).get("live", False),
            metadata={"critical": True, "endpoint": OLLAMA_TAGS}
        ))
        
        # Register GitHub CLI engine
        self.message_worker.register_engine(EngineDescriptor(
            engine_id="github_cli",
            engine_type="external_api",
            health_check=lambda: run(["gh", "auth", "status"], timeout=5).get("ok", False),
            metadata={"critical": False}
        ))
        
        # Register Resource Fabric engine
        self.message_worker.register_engine(EngineDescriptor(
            engine_id="resource_fabric",
            engine_type="resource_census",
            health_check=lambda: True,  # Will be checked via census
            metadata={"critical": True}
        ))
        
        # Register Factory Fabric engines
        self._register_factory_fabric_engines()
        
        # Subscribe to engine health signals
        self._subscribe_engine_signals()
        
        # Start capability activation loop
        self._start_capability_activation_loop()




    def _source(self, source_id: str, access: str, authority: str, trust: str, live: bool, payload: Any, evidence: list[str]) -> Source:
        return Source(source_id, access, authority, trust, live, "LIVE" if live else "UNAVAILABLE_OR_STALE", payload, evidence)

    def gather(self) -> list[Source]:
        tasks = load_json(TASKS, {"tasks": []})
        locks = load_json(LOCKS, {"locks": []})
        presence = load_json(COUNCIL_PRESENCE, {"seats": {}})
        factory = load_json(FACTORY_LATEST, {})
        resources = load_json(RESOURCE_LIVE, {})
        mail = load_jsonl(MAIL_INBOX, 50)
        mail_receipt = load_json(MAIL_RECEIPT, {})

        with ThreadPoolExecutor(max_workers=3) as pool:
            f_c5 = pool.submit(http_json, C5_HEALTH)
            f_cc = pool.submit(http_json, CC_HEALTH)
            f_ollama = pool.submit(http_json, OLLAMA_TAGS)
            c5 = f_c5.result()
            cc = f_cc.result()
            ollama = f_ollama.result()

        gh = run(["gh", "auth", "status", "--hostname", "github.com"], timeout=5)
        gh_repo = run(["gh", "repo", "view", "greenylifeonline-beep/Greeny-Life", "--json", "nameWithOwner,viewerPermission"], timeout=6) if gh.get("ok") else {}

        official_snapshot = load_json(
            RUNTIME_BASE / "factory-fabric" / "foundry" / "data" / "official-source-snapshot.json",
            {},
        )
        model_ecology = load_json(
            RUNTIME_BASE / "factory-fabric" / "model-ecology" / "MODEL-ECOLOGY.json",
            {},
        )

        maintenance_live, maintenance = maintenance_observation(RUNTIME_BASE / "continuity" / "status.json")

        active_tasks = [x for x in tasks.get("tasks", []) if x.get("status") not in {"DONE", "CANCELLED", "ARCHIVED"}]
        active_locks = [x for x in locks.get("locks", []) if x.get("status") == "ACTIVE"]
        seats = presence.get("seats", {})
        present = [
            seat for seat, row in seats.items() if safe_council_presence_live(row)
        ]

        return [
            self._source("CONTINUITY_MAINTENANCE", "PRIVATE_INTERNAL", "RAIOS_INTERNAL", "HIGH", maintenance_live,
                         maintenance, [str(RUNTIME_BASE / "continuity" / "status.json")]),
            self._source("CANONICAL_TASKS", "PRIVATE_INTERNAL", "CANONICAL", "HIGH", TASKS.is_file(),
                         {"active": active_tasks, "total": len(tasks.get("tasks", []))}, [str(TASKS)]),
            self._source("CANONICAL_LOCKS", "PRIVATE_INTERNAL", "CANONICAL", "HIGH", LOCKS.is_file(),
                         {"active": active_locks, "count": len(active_locks)}, [str(LOCKS)]),
            self._source("COUNCIL_PRESENCE", "PRIVATE_INTERNAL", "RUNTIME_AUTHENTICATED", "HIGH", bool(present),
                         {"present": present, "seats": seats}, [str(COUNCIL_PRESENCE)]),
            self._source("C5_LIVE_BRAIN", "PRIVATE_INTERNAL", "RAIOS_INTERNAL", "HIGH", bool(c5.get("live")), c5, [C5_HEALTH]),
            self._source("COMMAND_CENTER", "PRIVATE_INTERNAL", "RAIOS_INTERNAL", "HIGH", bool(cc.get("live")), cc, [CC_HEALTH]),
            self._source("OLLAMA_MODEL_POOL", "PRIVATE_INTERNAL", "LOCAL_RUNTIME", "HIGH", bool(ollama.get("live")), ollama, [OLLAMA_TAGS]),
            self._source("FACTORY_FABRIC", "PRIVATE_INTERNAL", "CANONICAL_CAPABILITY", "HIGH", bool(factory), factory, [str(FACTORY_LATEST)]),
            self._source("RESOURCE_FABRIC_LIVE", "PRIVATE_AUTHENTICATED_EXTERNAL", "AUTHORIZED_ACCOUNTS", "HIGH", bool(resources), resources, [str(RESOURCE_LIVE)]),
            self._source("GITHUB_PRIVATE", "PRIVATE_AUTHENTICATED_EXTERNAL", "OWNER_AUTHENTICATED", "HIGH", bool(gh.get("ok")),
                         {"auth": gh, "repo": gh_repo}, ["windows-keyring:gh-cli/github.com"]),
            self._source("GITHUB_MAIL", "PRIVATE_AUTHENTICATED_EXTERNAL", "UNVERIFIED_MESSAGE_INGRESS", "MEDIUM", bool(gh.get("ok")),
                         {"receipt": mail_receipt, "messages": mail}, [str(MAIL_INBOX)]),
            self._source("PUBLIC_OFFICIAL_KNOWLEDGE", "PUBLIC_EXTERNAL", "OFFICIAL_SOURCE", "HIGH", bool(official_snapshot),
                         official_snapshot, [str(RUNTIME_BASE / "factory-fabric" / "foundry" / "data" / "official-source-snapshot.json")]),
            self._source("MODEL_ECOLOGY", "PRIVATE_INTERNAL", "CANONICAL_CAPABILITY", "HIGH", bool(model_ecology), model_ecology,
                         [str(RUNTIME_BASE / "factory-fabric" / "model-ecology" / "MODEL-ECOLOGY.json")]),
        ]

    def _docs(self, sources: list[Source]) -> list[dict[str, str]]:
        docs: list[dict[str, str]] = []
        for source in sources:
            payload = source.semantic_dict()
            text = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
            docs.append({
                "doc_id": f"source:{source.source_id}",
                "source_id": source.source_id,
                "access_class": source.access_class,
                "trust_class": source.trust_class,
                "text": text[:30000],
            })

            if source.source_id == "CANONICAL_TASKS":
                for task in source.payload.get("active", [])[:200]:
                    docs.append({
                        "doc_id": "task:" + str(task.get("id")),
                        "source_id": source.source_id,
                        "access_class": source.access_class,
                        "trust_class": source.trust_class,
                        "text": json.dumps(task, ensure_ascii=False, sort_keys=True)[:12000],
                    })
            if source.source_id == "GITHUB_MAIL":
                for item in source.payload.get("messages", [])[-50:]:
                    docs.append({
                        "doc_id": "mail:" + str(item.get("id")),
                        "source_id": source.source_id,
                        "access_class": source.access_class,
                        "trust_class": source.trust_class,
                        "text": json.dumps(sanitize(item), ensure_ascii=False, sort_keys=True)[:12000],
                    })
        return docs
    def _emit_changes(self, sources: list[Source]) -> int:
        emitted = 0
        hashes = self.state.setdefault("last_hashes", {})
        for source in sources:
            current = sha(source.semantic_dict())
            if hashes.get(source.source_id) == current:
                continue
            event = build_event(
                event_type="OBSERVATION",
                actor=MANAGER_ACTOR,
                intent=f"Observe live source {source.source_id}",
                success=source.live,
                tool="RAIOS_SOURCE_FUSION",
                output_ref={
                    "source_id": source.source_id,
                    "access_class": source.access_class,
                    "authority_class": source.authority_class,
                    "trust_class": source.trust_class,
                    "live": source.live,
                    "freshness": source.freshness,
                },
                evidence_refs=source.evidence,
                confidence=0.98 if source.live else 0.75,
                metadata={"source_hash": current},
            )
            emit_event(event)
            hashes[source.source_id] = current
            emitted += 1
        return emitted

    def _gaps(self, sources: list[Source]) -> list[dict[str, Any]]:
        by = {s.source_id: s for s in sources}
        gaps: list[dict[str, Any]] = []

        def gap(
            code: str,
            severity: int,
            title: str,
            objective: str,
            scopes: list[str],
            risk: str = "LOW",
            blocked: str | None = None,
            caps: list[str] | None = None,
        ) -> None:
            gaps.append({
                "code": code,
                "severity": severity,
                "title": title,
                "objective": objective,
                "scope": scopes,
                "risk_class": risk,
                "blocked_by": blocked,
                "required_capabilities": caps or [],
            })

        maintenance = by.get("CONTINUITY_MAINTENANCE")
        if maintenance and (not maintenance.live or any(v is False for v in maintenance.payload.get("services", {}).values())):
            gap("CONTINUITY_MAINTENANCE_REPAIR", 96, "Restore canonical continuity maintenance",
                "Reconcile observed failed services through existing Maintain-RAIOS-Online and C5 recovery; prove health without adding a supervisor.",
                ["scripts/runtime/Maintain-RAIOS-Online.ps1"], caps=["runtime_repair"])
        if not by["C5_LIVE_BRAIN"].live:
            gap(
                "RESTORE_C5",
                100,
                "Restore C5 live brain",
                "Restore and prove C5 health and reasoning endpoint without creating a second brain.",
                ["src/raios", "scripts/runtime"],
                caps=["runtime_repair"],
            )
        if not by["COMMAND_CENTER"].live:
            gap(
                "RESTORE_COMMAND_CENTER",
                95,
                "Restore canonical Command Center",
                "Restore the one canonical Command Center and prove health.",
                ["src/raios/command_center", "scripts/runtime"],
                caps=["runtime_repair"],
            )
        presence_payload = by["COUNCIL_PRESENCE"].payload
        if not presence_payload.get("present"):
            gap(
                "RESTORE_PRESENCE",
                90,
                "Restore authenticated council presence",
                "Establish truthful self-signed seat presence so the Worker can dispatch only to present eligible executors.",
                ["src/raios/council_ops", ".ai-os/state"],
                risk="MEDIUM",
                caps=["council_operations"],
            )
        if not by["GITHUB_PRIVATE"].live:
            gap(
                "GITHUB_AUTH",
                85,
                "Reconnect GitHub owner account",
                "Restore authenticated GitHub access using the system keyring; never store the token in the repository.",
                [".ai-os/mail"],
                risk="MEDIUM",
                blocked="C1_INTERACTIVE_AUTH_REQUIRED",
            )
        if not by["RESOURCE_FABRIC_LIVE"].live:
            gap(
                "RESOURCE_REFRESH",
                80,
                "Refresh live Resource Fabric",
                "Probe all registered owned or authorized resource accounts read-only and refresh the live resource view.",
                ["src/raios/resource_fabric"],
                caps=["resource_probe"],
            )
        if not by["PUBLIC_OFFICIAL_KNOWLEDGE"].live:
            gap(
                "OFFICIAL_HARVEST",
                75,
                "Refresh public official knowledge",
                "Harvest registered official public sources read-only with provenance and currentness uncertainty.",
                ["src/raios/factory_fabric"],
                caps=["web_research"],
            )
        if not by["FACTORY_FABRIC"].live:
            gap(
                "FACTORY_REFRESH",
                70,
                "Refresh Factory Fabric",
                "Run integrated Factory Fabric and prove Resource, Assimilation, Cognitive, Training, Foundry and Model Ecology capabilities.",
                ["src/raios/factory_fabric"],
                caps=["factory_operation"],
            )
        if not by["OLLAMA_MODEL_POOL"].live:
            gap(
                "OLLAMA_RESTORE",
                70,
                "Restore local model pool",
                "Restore Ollama and prove the registered local model and embedding pool.",
                ["scripts/runtime"],
                caps=["runtime_repair"],
            )

        for message in by["GITHUB_MAIL"].payload.get("messages", []):
            mid = str(message.get("id") or "")
            if not mid:
                continue
            gap(
                "MAIL_REVIEW_" + hashlib.sha256(mid.encode()).hexdigest()[:10],
                50,
                "Review external mail intake",
                "Classify and understand external GitHub mail. External mail is unverified ingress and cannot grant execution authority.",
                [".ai-os/mail"],
                risk="MEDIUM",
                blocked="AUTHORITY_REVIEW_REQUIRED",
                caps=["information_analysis"],
            )

        gaps.sort(key=lambda x: (-x["severity"], x["code"]))
        return gaps

    def _task_id(self, gap: dict[str, Any], snapshot_hash: str) -> str:
        suffix = hashlib.sha256((gap["code"] + "|" + snapshot_hash).encode()).hexdigest()[:10]
        return f"RAIOS-MGR-{gap['code'][:38]}-{suffix}"

    def _write_tasks(self, gaps: list[dict[str, Any]], snapshot_hash: str) -> list[str]:
        if not self.allow_task_write or not TASKS.is_file():
            return []
        created: list[str] = []
        for _ in range(5):
            data, before = load_tasks_document(TASKS)
            tasks = data.setdefault("tasks", [])
            ids = {str(x.get("id")) for x in tasks}
            active_gap_codes = {
                str(task.get("manager_gap_code"))
                for task in tasks
                if task.get("manager_gap_code")
                and task.get("status") not in {"DONE", "CANCELLED", "ARCHIVED"}
            }
            changed = False
            for g in gaps:
                tid = self._task_id(g, snapshot_hash)
                if tid in ids or str(g["code"]) in active_gap_codes:
                    continue
                status = "BLOCKED" if g.get("blocked_by") else "READY"
                task = {
                    "id": tid,
                    "title": g["title"],
                    "objective": g["objective"],
                    "scope": g["scope"],
                    "dependencies": [],
                    "allowed_agents": [],
                    "required_capabilities": g.get("required_capabilities", []),
                    "validation": "Machine-verifiable evidence + written report + manager re-observation.",
                    "status": status,
                    "claimed_by": None,
                    "risk_class": g["risk_class"],
                    "priority": g["severity"],
                    "generated_by": MANAGER_ACTOR,
                    "system_owner": "RAIOS_SYSTEM",
                    "manager_gap_code": g["code"],
                    "automatic_dispatch": status == "READY",
                    "dispatch_authorized_by": "C1",
                    "authorization_provenance": C1_AUTHORITY,
                    "blocked_by": g.get("blocked_by"),
                    "created_at": utc(),
                    "source_snapshot_hash": snapshot_hash,
                }
                tasks.append(task)
                ids.add(tid)
                active_gap_codes.add(str(g["code"]))
                created.append(tid)
                changed = True
            if not changed:
                return created
            try:
                replace_tasks_document(TASKS, data, before, actor=MANAGER_ACTOR)
            except StaleTasksWriteError:
                created.clear()
                time.sleep(0.05)
                continue
            return created
        raise RuntimeError("TASKS_CONCURRENT_WRITE_RETRY_EXHAUSTED")

    def _reason_with_c5(
        self,
        gaps: list[dict[str, Any]],
        context: list[dict[str, Any]],
        snapshot_hash: str,
    ) -> dict[str, Any]:
        payload = {
            "gaps": gaps[:20],
            "retrieved_context": context[:12],
            "rules": [
                "RAIOS is the executive manager.",
                "C1 remains final authority.",
                "RAIOS-WORKER distributes; it is not the manager and not a council seat.",
                "Prefer evidence, reuse and low-cost local capability.",
                "Never invent source liveness, authority or evidence.",
                "No paid or irreversible action without explicit C1 gate.",
            ],
        }
        prompt = (
            "You are the RAIOS executive-manager reasoning layer. Analyze the following live grounded state. "
            "Return a concise priority assessment, contradictions, dependencies and the best execution order. "
            "Do not claim execution. Data:\n"
            + json.dumps(payload, ensure_ascii=False)[:16000]
        )
        body = json.dumps({"text": prompt, "language": "en", "training_mode": False}).encode("utf-8")
        req = urllib.request.Request(
            C5_CHAT,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=25) as resp:
                obj = json.loads(resp.read(50000).decode("utf-8", errors="replace"))
                response = str(obj.get("response") or "")[:12000]
                ok = resp.status == 200
        except Exception as exc:
            response = f"C5_REASONING_UNAVAILABLE:{type(exc).__name__}"
            ok = False
        latency = round((time.perf_counter() - started) * 1000, 3)
        event = build_event(
            event_type="MODEL_CALL",
            actor=MANAGER_ACTOR,
            intent="Prioritize grounded executive work",
            success=ok,
            tool="C5_CHAT",
            model="C5_ACTIVE_MODEL",
            input_ref={
                "snapshot_hash": snapshot_hash,
                "gap_count": len(gaps),
                "context_docs": len(context),
            },
            output_ref={"response": response},
            evidence_refs=[str(SOURCE_SNAPSHOT), str(INDEX_DB)],
            latency_ms=latency,
            confidence=0.75 if ok else 0.25,
        )
        emit_event(event)
        return {"ok": ok, "latency_ms": latency, "response": response}

    def _launch_reason(
        self,
        gaps: list[dict[str, Any]],
        context: list[dict[str, Any]],
        snapshot_hash: str,
    ) -> bool:
        with self._reason_lock:
            if self._reason_inflight:
                return False
            self._reason_inflight = True

        def runner() -> None:
            try:
                result = self._reason_with_c5(gaps, context, snapshot_hash)
                atomic_json(
                    ANALYSIS,
                    {
                        "schema": "raios.manager-analysis.v1",
                        "generated_at": utc(),
                        "snapshot_hash": snapshot_hash,
                        "gaps": gaps,
                        "retrieval_context": context,
                        "c5": result,
                    },
                )
            finally:
                with self._reason_lock:
                    self._reason_inflight = False

        threading.Thread(
            target=runner,
            name="RAIOS-C5-Manager-Reasoning",
            daemon=True,
        ).start()
        return True

    def _spawn_refreshes(self) -> None:
        now_s = time.time()
        last = self.state.setdefault("last_runs", {})
        child_env = {**os.environ, "PYTHONPATH": str(SRC)}

        def due(name: str, seconds: float) -> bool:
            return now_s - float(last.get(name, 0.0)) >= seconds

        def spawn_once(
            name: str,
            seconds: float,
            args: list[str],
            *,
            env: dict[str, str] | None = None,
        ) -> None:
            existing = self._refresh_processes.get(name)
            if not due(name, seconds) or (
                existing is not None and existing.poll() is None
            ):
                return
            process = subprocess.Popen(
                args,
                cwd=REPO,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=CREATE_NO_WINDOW,
                startupinfo=windowless_startupinfo(),
            )
            self._refresh_processes[name] = process
            if name == "search_index":
                self._search_refresh_process = process
            last[name] = now_s

        spawn_once(
            "mail",
            MAIL_REFRESH_SECONDS,
            [sys.executable, str(REPO / "scripts" / "ai-os" / "raios-mail.py"), "collect"],
        )
        spawn_once(
            "search_index",
            SEARCH_REFRESH_SECONDS,
            [sys.executable, "-m", "raios.search_cortex.engine", "--refresh-index"],
            env=child_env,
        )
        spawn_once(
            "resources",
            RESOURCE_REFRESH_SECONDS,
            [sys.executable, "-m", "raios.manager.live_manager", "--refresh-resources"],
            env=child_env,
        )
        spawn_once(
            "official",
            OFFICIAL_REFRESH_SECONDS,
            [sys.executable, "-m", "raios.factory_fabric.official_source", "--limit", "2000"],
            env=child_env,
        )
        spawn_once(
            "factory",
            FACTORY_REFRESH_SECONDS,
            [sys.executable, "-m", "raios.manager.live_manager", "--refresh-factory"],
            env=child_env,
        )

    def tick(self) -> dict[str, Any]:
        started = time.perf_counter()
        phase_started = started
        phase_latency_ms: dict[str, float] = {}

        def mark_phase(name: str) -> None:
            nonlocal phase_started
            current = time.perf_counter()
            phase_latency_ms[name] = round((current - phase_started) * 1000, 3)
            phase_started = current

        if self.enable_refreshes:
            self._spawn_refreshes()
        mark_phase("refresh_spawn")
        sources = self.gather()
        mark_phase("gather")
        snapshot = {
            "schema": "raios.manager-source-snapshot.v1",
            "generated_at": utc(),
            "sources": [s.as_dict() for s in sources],
        }
        snapshot_hash = sha([source.semantic_dict() for source in sources])
        snapshot["snapshot_hash"] = snapshot_hash
        atomic_json(SOURCE_SNAPSHOT, snapshot)
        mark_phase("snapshot_write")

        # Keep the live-source cache current without blocking on embeddings.
        index_result = self.memory.upsert(self._docs(sources), embed_limit=0)
        mark_phase("retrieval_index")
        emitted = self._emit_changes(sources)
        mark_phase("source_events")
        gaps = self._gaps(sources)
        query = (
            "current blockers failures resources tasks sources health "
            "capability manager execution priorities"
        )
        search_result = self.search_cortex.search(
            query,
            public_allowed=False,
            official_allowed=False,
            limit=12,
            deep=False,
            trace=False,
        )
        context = list(search_result.get("results") or [])
        mark_phase("search")

        last_reason_at = float(
            self.state.setdefault("last_runs", {}).get("reason", 0.0)
        )
        reason_age = time.time() - last_reason_at
        reason_due = reason_age >= REASON_SECONDS
        retry_due = reason_age >= REASON_RETRY_SECONDS
        reasoning_hash = sha(gaps)
        prior_reasoning_hash = self.state.get("last_reason_input_hash")
        c5_analysis = load_json(ANALYSIS, {})
        analysis_payload = (
            c5_analysis.get("c5", c5_analysis)
            if isinstance(c5_analysis, dict)
            else {}
        )
        analysis_ok = bool(analysis_payload.get("ok"))
        reason_started = False
        should_reason = reasoning_hash != prior_reasoning_hash or (not analysis_ok and retry_due)
        if self.enable_reasoning and reason_due and should_reason:
            reason_started = self._launch_reason(gaps, context, snapshot_hash)
            if reason_started:
                self.state["last_runs"]["reason"] = time.time()
                self.state["last_reason_snapshot_hash"] = snapshot_hash
                self.state["last_reason_input_hash"] = reasoning_hash

        created = self._write_tasks(gaps, snapshot_hash)
        mark_phase("reason_and_tasks")

        if created:
            event = build_event(
                event_type="DECISION",
                actor=MANAGER_ACTOR,
                intent="Create canonical execution work from grounded gaps",
                success=True,
                tool="CANONICAL_TASK_LEDGER_ADAPTER",
                input_ref={
                    "snapshot_hash": snapshot_hash,
                    "gap_codes": [g["code"] for g in gaps],
                },
                output_ref={"created_task_ids": created},
                evidence_refs=[str(TASKS), str(SOURCE_SNAPSHOT), str(ANALYSIS)],
                confidence=0.97,
                metadata={
                    "worker_role": "DISTRIBUTION_ONLY",
                    "manager_role": "RAIOS",
                },
            )
            emit_event(event)

        evolution_hb = load_json(EVOLUTION_HEARTBEAT, {})
        evolution = {
            "state": evolution_hb.get("state", "UNAVAILABLE"),
            "timestamp": evolution_hb.get("timestamp"),
            "continuous_background_cognition": bool(
                evolution_hb.get("continuous_background_cognition", False)
            ),
            "search_cortex": evolution_hb.get("search_cortex") or {},
            "last_result": evolution_hb.get("last_result") or {},
        }

        c5_payload = analysis_payload
        elapsed = round((time.perf_counter() - started) * 1000, 3)
        result = {
            "schema": "raios.live-manager-tick.v2",
            "state": "RUNNING",
            "generated_at": utc(),
            "manager_pid": os.getpid(),
            "snapshot_hash": snapshot_hash,
            "source_count": len(sources),
            "live_source_count": sum(1 for s in sources if s.live),
            "private_source_count": sum(
                1 for s in sources if s.access_class.startswith("PRIVATE")
            ),
            "public_source_count": sum(
                1 for s in sources if s.access_class.startswith("PUBLIC")
            ),
            "index": index_result,
            "source_change_events": emitted,
            "gap_count": len(gaps),
            "gaps": gaps,
            "created_tasks": created,
            "retrieval_hits": len(context),
            "search_cortex": {
                "count": search_result.get("count", 0),
                "sources": search_result.get("sources", []),
                "latency_ms": search_result.get("latency_ms"),
                "verification": search_result.get("verification") or {},
                "contradictions": search_result.get("contradictions") or [],
                "plan": search_result.get("plan") or {},
                "private_query_sent_to_web": search_result.get(
                    "private_query_sent_to_web", False
                ),
            },
            "c5_reasoning_ok": bool(c5_payload.get("ok")),
            "c5_reasoning_started": reason_started,
            "c5_reasoning_inflight": self._reason_inflight,
            "evolution": evolution,
            "latency_ms": elapsed,
            "phase_latency_ms": phase_latency_ms,
            "single_task_ledger": str(TASKS),
            "single_cognitive_wal": str(WAL_FILE),
            "second_bus": False,
            "second_task_store": False,
            "second_wal": False,
        }
        write_heartbeat(result)
        self.state["last_tick"] = result["generated_at"]
        self.state["last_snapshot_hash"] = snapshot_hash
        atomic_json(STATE, self.state)
        return result

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        if int(pid or 0) <= 4:
            return False
        if os.name != "nt":
            try:
                os.kill(int(pid), 0)
                return True
            except OSError:
                return False
        try:
            import ctypes

            process_query_limited_information = 0x1000
            still_active = 259
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(
                process_query_limited_information, False, int(pid)
            )
            if not handle:
                return False
            try:
                exit_code = ctypes.c_ulong()
                if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                    return False
                return int(exit_code.value) == still_active
            finally:
                kernel32.CloseHandle(handle)
        except Exception:
            return False

    def _evolution_heartbeat_live(self, max_age_seconds: float = 120.0) -> tuple[bool, dict[str, Any]]:
        hb = load_json(EVOLUTION_HEARTBEAT, {})
        if not isinstance(hb, dict):
            return False, {}
        try:
            stamp = datetime.fromisoformat(str(hb.get("timestamp", "")).replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - stamp).total_seconds()
        except Exception:
            return False, hb
        wal = str(hb.get("wal") or "")
        state = str(hb.get("state") or "").upper()
        same_wal = False
        try:
            same_wal = Path(wal).resolve() == Path(WAL_FILE).resolve()
        except Exception:
            same_wal = wal == str(WAL_FILE)
        pid_alive = self._pid_alive(int(hb.get("pid") or 0))
        return bool(
            pid_alive
            and 0 <= age <= max_age_seconds
            and state in {"STARTING", "ACTIVE", "IDLE_COGNITION", "RUNNING", "ONLINE"}
            and same_wal
        ), hb

    def _supervise_evolution_once(self) -> None:
        with self._evolution_recovery_lock:
            live, hb = self._evolution_heartbeat_live()
            now_mono = time.monotonic()
            if live:
                state = str(hb.get("state") or "").upper()
                if state == "STARTING":
                    return
                if self._evolution_was_down:
                    self._evolution_was_down = False
                    self._evolution_recovery_attempt = 0
                    self._evolution_recovery_next_at = 0.0
                    log(
                        "Evolution self-heal recovered "
                        f"pid={hb.get('pid')} wal={hb.get('wal')}"
                    )
                    try:
                        event = build_event(
                            event_type="RECOVERY",
                            actor=MANAGER_ACTOR,
                            intent="Recover Evolution daemon and resume canonical Cognitive WAL processing",
                            success=True,
                            tool="RAIOS_MANAGER_EVOLUTION_SELF_HEAL",
                            output_ref={
                                "pid": hb.get("pid"),
                                "state": hb.get("state"),
                                "wal": hb.get("wal"),
                                "evolution_status": hb.get("evolution_status"),
                            },
                            evidence_refs=[str(EVOLUTION_HEARTBEAT), str(LOG_FILE)],
                            confidence=1.0,
                        )
                        emit_event(event)
                    except Exception as exc:
                        log(f"Evolution recovery evidence emit FAIL {type(exc).__name__}: {exc}")
                return

            self._evolution_was_down = True
            running = self._evolution_recovery_process
            if running is not None and running.poll() is None:
                return
            if now_mono < self._evolution_recovery_next_at:
                return

            ensure = REPO / "scripts" / "runtime" / "Ensure-RAIOS-Cognitive-Loop.ps1"
            if not ensure.is_file():
                self._evolution_recovery_attempt += 1
                self._evolution_recovery_next_at = now_mono + min(
                    300.0, 15.0 * (2 ** min(self._evolution_recovery_attempt, 4))
                )
                log(f"Evolution self-heal blocked: missing {ensure}")
                return

            powershell = (
                Path(os.environ.get("SystemRoot", r"C:\Windows"))
                / "System32"
                / "WindowsPowerShell"
                / "v1.0"
                / "powershell.exe"
            )
            args = [
                str(powershell),
                "-NoLogo",
                "-NoProfile",
                "-NonInteractive",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ensure),
                "-Repo",
                str(REPO),
            ]
            env = os.environ.copy()
            env["RAIOS_COGNITIVE_RECOVERY_OWNER"] = "RAIOS-MANAGER"
            env["RAIOS_CANONICAL_REPO"] = str(REPO)
            out_path = MANAGER_ROOT / "evolution-recovery.out.log"
            err_path = MANAGER_ROOT / "evolution-recovery.err.log"
            try:
                with out_path.open("ab") as out_handle, err_path.open("ab") as err_handle:
                    proc = subprocess.Popen(
                        args,
                        cwd=str(REPO),
                        env=env,
                        stdin=subprocess.DEVNULL,
                        stdout=out_handle,
                        stderr=err_handle,
                        startupinfo=windowless_startupinfo(),
                        creationflags=CREATE_NO_WINDOW,
                    )
                self._evolution_recovery_process = proc
                self._evolution_recovery_attempt += 1
                backoff = min(
                    300.0, 15.0 * (2 ** min(self._evolution_recovery_attempt - 1, 4))
                )
                self._evolution_recovery_next_at = now_mono + backoff
                log(
                    "Evolution self-heal started "
                    f"pid={proc.pid} attempt={self._evolution_recovery_attempt} "
                    f"backoff_seconds={int(backoff)}"
                )
            except Exception as exc:
                self._evolution_recovery_attempt += 1
                self._evolution_recovery_next_at = now_mono + min(
                    300.0, 15.0 * (2 ** min(self._evolution_recovery_attempt, 4))
                )
                log(f"Evolution self-heal start FAIL {type(exc).__name__}: {exc}")

    def _start_evolution_supervisor(self) -> None:
        def loop() -> None:
            while True:
                try:
                    self._supervise_evolution_once()
                except BaseException as exc:
                    log(f"Evolution supervisor FAIL {type(exc).__name__}: {exc}")
                time.sleep(5)

        threading.Thread(
            target=loop,
            name="RAIOS-Manager-Evolution-Self-Heal",
            daemon=True,
        ).start()

    def daemon(self) -> None:
        MANAGER_ROOT.mkdir(parents=True, exist_ok=True)
        lock_handle = INSTANCE_LOCK.open("a+b")
        try:
            import msvcrt

            # Do not read the lock byte on Windows. Some inherited ACL/file
            # states allow append/lock but reject read(), which previously
            # crashed the manager before singleton acquisition.
            lock_handle.seek(0, os.SEEK_END)
            if lock_handle.tell() == 0:
                lock_handle.write(b"0")
                lock_handle.flush()
            lock_handle.seek(0)
            try:
                msvcrt.locking(lock_handle.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                raise SystemExit("RAIOS_MANAGER_ALREADY_RUNNING")
        except ImportError:
            pass

        log("RAIOS live manager started")
        # Publish process liveness immediately after the single-instance lock is
        # acquired. The first evidence scan may be slow on a CPU-only laptop;
        # STARTING is truthful liveness, not a completed diagnostic claim.
        write_heartbeat(
            {
                "schema": "raios.live-manager-tick.v2",
                "generated_at": utc(),
                "manager_pid": os.getpid(),
                "state": "STARTING",
                "source_count": 0,
                "live_source_count": 0,
                "gap_count": 0,
                "gaps": [],
                "c5_reasoning_ok": False,
                "c5_reasoning_inflight": False,
                "latency_ms": 0.0,
                "single_task_ledger": str(TASKS),
                "single_cognitive_wal": str(WAL_FILE),
                "second_bus": False,
                "second_task_store": False,
                "second_wal": False,
            },
        )
        pulse_state = {"tick_inflight": False}

        def publish_liveness_pulse() -> None:
            while True:
                time.sleep(15)
                try:
                    write_heartbeat(
                        {
                            "schema": "raios.live-manager-tick.v2",
                            "generated_at": utc(),
                            "manager_pid": os.getpid(),
                            "state": "RUNNING",
                            "tick_inflight": pulse_state["tick_inflight"],
                            "last_completed_at": self.state.get("last_tick"),
                            "single_task_ledger": str(TASKS),
                            "single_cognitive_wal": str(WAL_FILE),
                            "second_bus": False,
                            "second_task_store": False,
                            "second_wal": False,
                        },
                    )
                except BaseException as exc:
                    log(f"liveness pulse FAIL {type(exc).__name__}: {exc}")

        threading.Thread(
            target=publish_liveness_pulse,
            name="RAIOS-Manager-Liveness-Pulse",
            daemon=True,
        ).start()
        self._start_evolution_supervisor()

        while True:
            try:
                pulse_state["tick_inflight"] = True
                result = self.tick()
                pulse_state["tick_inflight"] = False
                log(
                    "tick PASS "
                    f"sources={result['source_count']} "
                    f"live={result['live_source_count']} "
                    f"gaps={result['gap_count']} "
                    f"tasks={len(result['created_tasks'])} "
                    f"latency_ms={result['latency_ms']}"
                )
            except KeyboardInterrupt:
                pulse_state["tick_inflight"] = False
                log("RAIOS live manager stopped")
                return
            except BaseException as exc:
                pulse_state["tick_inflight"] = False
                log(f"tick FAIL {type(exc).__name__}: {exc}")
                try:
                    event = build_event(
                        event_type="FAILURE",
                        actor=MANAGER_ACTOR,
                        intent="Maintain continuous executive manager loop",
                        success=False,
                        tool="RAIOS_LIVE_MANAGER",
                        output_ref={
                            "exception_type": type(exc).__name__,
                            "message": str(exc),
                        },
                        evidence_refs=[str(LOG_FILE)],
                        confidence=0.99,
                    )
                    emit_event(event)
                    # Evolution Brain daemon is the sole Cognitive WAL consumer.
                except Exception:
                    pass
            time.sleep(LOCAL_TICK_SECONDS)




    def _register_factory_fabric_engines(self) -> None:
        """Register Factory Fabric engines with health checks."""
        if not self._mw_integration_enabled:
            return
        
        # Resource Factory
        self.message_worker.register_engine(EngineDescriptor(
            engine_id="resource_factory",
            engine_type="resource_factory",
            health_check=lambda: self._check_resource_factory(),
            metadata={"critical": True, "factory": "RESOURCE_FACTORY"}
        ))
        
        # Training Factory
        self.message_worker.register_engine(EngineDescriptor(
            engine_id="training_factory",
            engine_type="training_factory",
            health_check=lambda: self._check_training_factory(),
            metadata={"critical": True, "factory": "TRAINING_FACTORY"}
        ))
        
        # Expert Foundry
        self.message_worker.register_engine(EngineDescriptor(
            engine_id="expert_foundry",
            engine_type="expert_foundry",
            health_check=lambda: self._check_expert_foundry(),
            metadata={"critical": True, "factory": "C5_EXPERT_FOUNDRY"}
        ))
        
        # Model Ecology
        self.message_worker.register_engine(EngineDescriptor(
            engine_id="model_ecology",
            engine_type="model_ecology",
            health_check=lambda: self._check_model_ecology(),
            metadata={"critical": True, "factory": "MODEL_ECOLOGY"}
        ))
        
        # Assimilation Factory
        self.message_worker.register_engine(EngineDescriptor(
            engine_id="assimilation_factory",
            engine_type="assimilation_factory",
            health_check=lambda: self._check_assimilation_factory(),
            metadata={"critical": True, "factory": "ASSIMILATION_FACTORY"}
        ))
        
        # Cognitive Factory
        self.message_worker.register_engine(EngineDescriptor(
            engine_id="cognitive_factory",
            engine_type="cognitive_factory",
            health_check=lambda: self._check_cognitive_factory(),
            metadata={"critical": True, "factory": "COGNITIVE_FACTORY"}
        ))
    
    def _check_resource_factory(self) -> bool:
        """Check Resource Factory health."""
        try:
            from raios.factory_fabric.orchestrator import resource_factory_probe
            result = resource_factory_probe(live=True)
            return str(result.get("status", "")).startswith("PASS")
        except Exception as exc:
            StructuredLogger.warning(f"Resource Factory health check failed: {exc}")
            return False
    
    def _check_training_factory(self) -> bool:
        """Check Training Factory health."""
        try:
            from raios.factory_fabric.orchestrator import training_factory_probe
            result = training_factory_probe()
            return str(result.get("status", "")).startswith("PASS")
        except Exception as exc:
            StructuredLogger.warning(f"Training Factory health check failed: {exc}")
            return False
    
    def _check_expert_foundry(self) -> bool:
        """Check Expert Foundry health."""
        try:
            from raios.factory_fabric.orchestrator import foundry_probe
            result = foundry_probe(max_files=10, case_limit=10)
            return str(result.get("status", "")).startswith("PASS")
        except Exception as exc:
            StructuredLogger.warning(f"Expert Foundry health check failed: {exc}")
            return False
    
    def _check_model_ecology(self) -> bool:
        """Check Model Ecology health."""
        try:
            from raios.factory_fabric.orchestrator import model_ecology_probe
            result = model_ecology_probe(live_accounts=False)
            return str(result.get("status", "")).startswith("PASS")
        except Exception as exc:
            StructuredLogger.warning(f"Model Ecology health check failed: {exc}")
            return False
    
    def _check_assimilation_factory(self) -> bool:
        """Check Assimilation Factory health."""
        try:
            from raios.factory_fabric.orchestrator import assimilation_probe
            result = assimilation_probe()
            return str(result.get("status", "")).startswith("PASS")
        except Exception as exc:
            StructuredLogger.warning(f"Assimilation Factory health check failed: {exc}")
            return False
    
    def _check_cognitive_factory(self) -> bool:
        """Check Cognitive Factory health."""
        try:
            from raios.factory_fabric.orchestrator import cognitive_factory_probe
            result = cognitive_factory_probe()
            return str(result.get("status", "")).startswith("PASS")
        except Exception as exc:
            StructuredLogger.warning(f"Cognitive Factory health check failed: {exc}")
            return False




    def _register_manager_circuit_breakers(self) -> None:
        """Register circuit breakers for external dependencies."""
        if not self._mw_integration_enabled:
            return
        
        self.message_worker.register_circuit_breaker("c5_chat", failure_threshold=3, recovery_timeout=30.0)
        self.message_worker.register_circuit_breaker("command_center", failure_threshold=3, recovery_timeout=30.0)
        self.message_worker.register_circuit_breaker("ollama", failure_threshold=5, recovery_timeout=60.0)
        self.message_worker.register_circuit_breaker("github_api", failure_threshold=5, recovery_timeout=120.0)
        self.message_worker.register_circuit_breaker("ollama_embed", failure_threshold=3, recovery_timeout=60.0)
        self.message_worker.register_circuit_breaker("subprocess_spawn", failure_threshold=3, recovery_timeout=30.0)




    def _subscribe_engine_signals(self) -> None:
        """Subscribe to engine health signals from MessageWorker."""
        if not self._mw_integration_enabled:
            return
        
        def on_engine_health(payload: dict):
            engine_id = payload.get("engine_id")
            healthy = payload.get("healthy")
            if engine_id and healthy is not None:
                engine = self.message_worker.get_engine(engine_id)
                if engine:
                    old_state = engine.state
                    engine.state = EngineState.ACTIVE if healthy else EngineState.UNAVAILABLE
                    engine.last_health_check = time.time()
                    if old_state != engine.state:
                        StructuredLogger.info(f"Engine {engine_id} state changed: {old_state.value} -> {engine.state.value}")
                        metrics.inc("engine.state_changed", labels={"engine": engine_id, "new_state": engine.state.value})
        
        def on_circuit_breaker(payload: dict):
            cb_name = payload.get("circuit")
            state = payload.get("state")
            if cb_name and state:
                metrics.inc("circuit_breaker.state_changed", labels={"circuit": cb_name, "state": state})
                StructuredLogger.warning(f"Circuit breaker {cb_name} -> {state}")
        
        self.message_worker.subscribe("ENGINE.HEALTH", on_engine_health)
        self.message_worker.subscribe("CIRCUIT_BREAKER", on_circuit_breaker)
        metrics.inc("engine.signals_subscribed", labels={"count": "2"})
    
    def _start_capability_activation_loop(self) -> None:
        """Start the background capability activation loop."""
        if not self._mw_integration_enabled:
            return
        
        self._capability_loop_stop = threading.Event()
        self._capability_loop_thread = threading.Thread(
            target=self._capability_activation_loop,
            name="RAIOS-Capability-Activation-Loop",
            daemon=True,
        )
        self._capability_loop_thread.start()
        StructuredLogger.info("Capability activation loop started")
    
    def _capability_activation_loop(self) -> None:
        """Background loop that periodically checks engine health and activates capabilities."""
        check_interval = 30.0  # Check every 30 seconds
        activation_interval = 60.0  # Try activation every 60 seconds
        last_activation = 0.0
        
        while not self._capability_loop_stop.is_set():
            try:
                # Periodic health checks
                self._check_all_engine_health()
                
                # Periodic activation attempts
                now = time.time()
                if now - last_activation >= 60.0:
                    self._attempt_engine_activation()
                    last_activation = time.time()
                
                # Also check circuit breakers and try recovery
                self._check_circuit_breakers_recovery()
                
            except Exception as exc:
                StructuredLogger.error(f"Capability loop error: {exc}")
                metrics.inc("capability_loop.error")
            
            self._capability_loop_stop.wait(30.0)
    
    def _check_all_engine_health(self) -> None:
        """Check health of all registered engines and update their states."""
        if not self._mw_integration_enabled:
            return
        
        with self.message_worker._engine_lock:
            for engine_id, engine in self.message_worker._engine_registry.items():
                if engine.health_check:
                    try:
                        start = time.perf_counter()
                        healthy = engine.health_check()
                        latency = round((time.perf_counter() - start) * 1000, 3)
                        
                        old_state = engine.state
                        engine.state = EngineState.ACTIVE if healthy else EngineState.UNAVAILABLE
                        engine.last_health_check = time.time()
                        engine.last_health_latency = latency
                        
                        if old_state != engine.state:
                            StructuredLogger.info(f"Engine {engine_id} state changed: {old_state.value} -> {engine.state.value}")
                            metrics.inc("engine.state_changed", labels={"engine": engine_id, "new_state": engine.state.value})
                        
                        metrics.observe("engine.health_check.latency_ms", latency, labels={"engine": engine_id})
                        metrics.inc("engine.health_check", labels={"engine": engine_id, "result": "healthy" if healthy else "unhealthy"})
                        
                    except Exception as exc:
                        StructuredLogger.error(f"Engine {engine_id} health check failed: {exc}")
                        engine.state = EngineState.UNAVAILABLE
                        metrics.inc("engine.health_check.error", labels={"engine": engine_id, "error": type(exc).__name__})
    
    def _attempt_engine_activation(self) -> None:
        """Attempt to activate engines that are UNAVAILABLE but have dependencies met."""
        if not self._mw_integration_enabled:
            return
        
        with self.message_worker._engine_lock:
            for engine_id, engine in self.message_worker._engine_registry.items():
                if engine.state == EngineState.UNAVAILABLE and engine.activation_cmd:
                    # Check if dependencies are met
                    deps_met = True
                    for dep_id in engine.dependencies:
                        dep_engine = self.message_worker._engine_registry.get(dep_id)
                        if not dep_engine or dep_engine.state not in (EngineState.ACTIVE, EngineState.AVAILABLE):
                            deps_met = False
                            break
                    
                    if deps_met:
                        StructuredLogger.info(f"Attempting activation of engine {engine_id}")
                        try:
                            import subprocess
                            result = subprocess.run(
                                engine.activation_cmd,
                                shell=True,
                                check=True,
                                timeout=60,
                                capture_output=True,
                                text=True,
                                creationflags=CREATE_NO_WINDOW,
                            )
                            engine.state = EngineState.ACTIVATING
                            StructuredLogger.info(f"Engine {engine_id} activation started")
                            metrics.inc("engine.activation.started", labels={"engine": engine_id})
                        except Exception as exc:
                            StructuredLogger.warning(f"Engine {engine_id} activation failed: {exc}")
                            metrics.inc("engine.activation.failed", labels={"engine": engine_id, "error": type(exc).__name__})
    
    def _check_circuit_breakers_recovery(self) -> None:
        """Check if any OPEN circuit breakers can transition to HALF_OPEN."""
        if not self._mw_integration_enabled:
            return
        
        for name, cb in self.message_worker._circuit_breakers.items():
            if cb.state == CircuitState.OPEN:
                if time.time() - cb._last_failure_time >= cb.timeout:
                    cb._state = CircuitState.HALF_OPEN
                    cb._success_count = 0
                    StructuredLogger.info(f"Circuit breaker {name} transitioned to HALF_OPEN")
                    metrics.inc("circuit_breaker.half_open", labels={"circuit": name})
                    self.emit_health_signal(f"CIRCUIT_BREAKER_HALF_OPEN", {"circuit": name})
    

    def enqueue_alert(self, targets: list[str], text: str, msg_type: str = "CONTROL", priority: MessagePriority = MessagePriority.HIGH, **kwargs) -> dict | None:
        """Enqueue an alert via MessageWorker."""
        if not self._mw_integration_enabled:
            return None
        try:
            return self.message_worker.enqueue(
                sender=MANAGER_ACTOR,
                targets=targets,
                text=text,
                msg_type=msg_type,
                priority=priority,
                **kwargs
            )
        except Exception as exc:
            StructuredLogger.warning(f"enqueue_alert FAIL: {exc}")
            return None

    def emit_health_signal(self, event: str, payload: dict) -> int:
        """Emit a health signal via MessageWorker signal bus."""
        if not self._mw_integration_enabled:
            return 0
        try:
            return self.message_worker.emit_signal(f"HEALTH.{event}", payload)
        except Exception as exc:
            StructuredLogger.warning(f"emit_health_signal FAIL: {exc}")
            return 0

    def call_with_circuit_breaker(self, name: str, func: callable, fallback = None):
        """Execute function with circuit breaker protection via MessageWorker."""
        if not self._mw_integration_enabled:
            return func()
        try:
            return self.message_worker.call_with_circuit_breaker(name, func, fallback)
        except Exception as exc:
            if fallback:
                try:
                    return fallback()
                except Exception:
                    pass
            raise

    def emit_failure_event(self, intent: str, tool: str, exception: Exception, metadata = None):
        """Emit a FAILURE event via Cognitive Event Bus and MessageWorker signal."""
        if not self._mw_integration_enabled:
            return
        try:
            self.message_worker.emit_signal("FAILURE", {
                "actor": MANAGER_ACTOR,
                "intent": intent,
                "tool": tool,
                "exception_type": type(exception).__name__,
                "message": str(exception),
                "metadata": metadata or {},
            })
        except Exception as exc:
            StructuredLogger.warning(f"emit_failure_event FAIL: {exc}")

    def schedule_dead_letter_retry(self, mid: str, attempt: int):
        """Schedule dead letter retry via MessageWorker."""
        if not self._mw_integration_enabled:
            return
        try:
            self.message_worker.schedule_dead_letter_retry(mid, attempt)
        except Exception as exc:
            StructuredLogger.warning(f"schedule_dead_letter_retry FAIL: {exc}")

    def _emit_c5_reasoning_event(self, gaps: list, context: list, snapshot_hash: str, result: dict):
        """Emit C5 reasoning event via MessageWorker."""
        if not self._mw_integration_enabled:
            return
        try:
            self.message_worker.emit_signal("C5_REASONING", {
                "snapshot_hash": snapshot_hash,
                "gap_count": len(gaps),
                "context_count": len(context),
                "ok": result.get("ok", False),
                "latency_ms": result.get("latency_ms", 0),
            })
        except Exception:
            pass


    def stop(self) -> None:
        """Stop the manager and all background loops."""
        if hasattr(self, '_capability_loop_stop'):
            self._capability_loop_stop.set()
        if hasattr(self, '_capability_loop_thread') and self._capability_loop_thread.is_alive():
            self._capability_loop_thread.join(timeout=5.0)
        if self._mw_integration_enabled:
            self.message_worker.stop()





def refresh_resources() -> dict[str, Any]:
    from raios.resource_fabric.census import collect_world
    from raios.resource_fabric.live import apply_live_overlay, run_live_probes

    live = run_live_probes(live=True)
    world = collect_world()
    apply_live_overlay(world, live)
    payload = {
        "schema": "raios.manager-resource-live.v1",
        "generated_at": utc(),
        "live_state": sanitize(live),
        "world": sanitize(world),
    }
    atomic_json(RESOURCE_LIVE, payload)
    return {
        "status": "PASS",
        "path": str(RESOURCE_LIVE),
        "accounts": len(world.get("accounts", [])),
    }


def refresh_factory() -> dict[str, Any]:
    from raios.factory_fabric.orchestrator import run_all

    report = run_all(
        max_files=120,
        case_limit=120,
        live_resource=True,
    )
    return {
        "status": report.get("status"),
        "path": report.get("report_path"),
    }


def run_once(allow_task_write: bool = True) -> dict[str, Any]:
    return LiveManager(allow_task_write=allow_task_write).tick()


def main() -> int:
    parser = argparse.ArgumentParser(prog="RAIOS-LIVE-MANAGER")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--no-task-write", action="store_true")
    parser.add_argument("--no-refresh-spawn", action="store_true")
    parser.add_argument("--no-reasoning", action="store_true")
    parser.add_argument("--refresh-resources", action="store_true")
    parser.add_argument("--refresh-factory", action="store_true")
    args = parser.parse_args()

    if args.refresh_resources:
        print(json.dumps(refresh_resources(), ensure_ascii=False, indent=2))
        return 0
    if args.refresh_factory:
        print(json.dumps(refresh_factory(), ensure_ascii=False, indent=2))
        return 0

    manager = LiveManager(
        allow_task_write=not args.no_task_write,
        enable_refreshes=not args.no_refresh_spawn,
        enable_reasoning=not args.no_reasoning,
    )
    if args.daemon:
        manager.daemon()
        return 0

    print(json.dumps(manager.tick(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())