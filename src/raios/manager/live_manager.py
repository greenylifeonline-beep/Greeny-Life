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

REPO = Path(__file__).resolve().parents[3]
SRC = REPO / "src"
V9_RUNTIME = REPO / "RAIOS" / "V9" / "runtime"
if str(V9_RUNTIME) not in sys.path:
    sys.path.insert(0, str(V9_RUNTIME))

from cognitive_event_bus import build_event, emit_event
from raios.search_cortex import SearchCortex

TASKS = REPO / ".ai-os" / "state" / "TASKS.json"
LOCKS = REPO / ".ai-os" / "state" / "LOCKS.json"
MAIL_INBOX = REPO / ".ai-os" / "mail" / "INBOX.jsonl"
MAIL_RECEIPT = REPO / ".ai-os" / "mail" / "COLLECT-RECEIPT.json"
FACTORY_LATEST = Path.home() / ".raios" / "runtime" / "factory-fabric" / "FACTORY-FABRIC-LATEST.json"
COUNCIL_PRESENCE = Path.home() / ".raios" / "runtime" / "council-ops" / "presence.json"
MANAGER_ROOT = Path.home() / ".raios" / "runtime" / "manager"
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
EVOLUTION_HEARTBEAT = Path.home() / ".raios" / "runtime" / "evolution-brain" / "heartbeat.json"
OLLAMA_TAGS = "http://127.0.0.1:11434/api/tags"
OLLAMA_EMBED = "http://127.0.0.1:11434/api/embed"
EMBED_MODEL = "qwen3-embedding:0.6b"

LOCAL_TICK_SECONDS = 2.0
MAIL_REFRESH_SECONDS = 20.0
GITHUB_REFRESH_SECONDS = 30.0
RESOURCE_REFRESH_SECONDS = 90.0
SEARCH_REFRESH_SECONDS = 10.0
EMBED_REFRESH_SECONDS = 60.0
OFFICIAL_REFRESH_SECONDS = 900.0
FACTORY_REFRESH_SECONDS = 1800.0
REASON_SECONDS = 15.0
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
        proc = subprocess.run(args, cwd=cwd or REPO, text=True, capture_output=True, timeout=timeout, check=False)
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
    def __init__(self, allow_task_write: bool = True):
        MANAGER_ROOT.mkdir(parents=True, exist_ok=True)
        self.allow_task_write = allow_task_write
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
            Path.home() / ".raios" / "runtime" / "factory-fabric" / "foundry" / "data" / "official-source-snapshot.json",
            {},
        )
        model_ecology = load_json(
            Path.home() / ".raios" / "runtime" / "factory-fabric" / "model-ecology" / "MODEL-ECOLOGY.json",
            {},
        )

        active_tasks = [x for x in tasks.get("tasks", []) if x.get("status") not in {"DONE", "CANCELLED", "ARCHIVED"}]
        active_locks = [x for x in locks.get("locks", []) if x.get("status") == "ACTIVE"]
        seats = presence.get("seats", {})
        present = [k for k, v in seats.items() if v.get("presence") == "PRESENT"]

        return [
            self._source("CANONICAL_TASKS", "PRIVATE_INTERNAL", "CANONICAL", "HIGH", TASKS.is_file(),
                         {"active": active_tasks, "total": len(tasks.get("tasks", []))}, [str(TASKS)]),
            self._source("CANONICAL_LOCKS", "PRIVATE_INTERNAL", "CANONICAL", "HIGH", LOCKS.is_file(),
                         {"active": active_locks, "count": len(active_locks)}, [str(LOCKS)]),
            self._source("COUNCIL_PRESENCE", "PRIVATE_INTERNAL", "RUNTIME_AUTHENTICATED", "HIGH", bool(presence),
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
                         official_snapshot, [str(Path.home() / ".raios" / "runtime" / "factory-fabric" / "foundry" / "data" / "official-source-snapshot.json")]),
            self._source("MODEL_ECOLOGY", "PRIVATE_INTERNAL", "CANONICAL_CAPABILITY", "HIGH", bool(model_ecology), model_ecology,
                         [str(Path.home() / ".raios" / "runtime" / "factory-fabric" / "model-ecology" / "MODEL-ECOLOGY.json")]),
        ]

    def _docs(self, sources: list[Source]) -> list[dict[str, str]]:
        docs: list[dict[str, str]] = []
        for source in sources:
            payload = source.as_dict()
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
            current = sha(source.as_dict())
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
            raw = TASKS.read_bytes()
            before = hashlib.sha256(raw).hexdigest()
            data = json.loads(raw.decode("utf-8-sig"))
            tasks = data.setdefault("tasks", [])
            ids = {str(x.get("id")) for x in tasks}
            changed = False
            for g in gaps:
                tid = self._task_id(g, snapshot_hash)
                if tid in ids:
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
                created.append(tid)
                changed = True
            if not changed:
                return created
            if hashlib.sha256(TASKS.read_bytes()).hexdigest() != before:
                created.clear()
                time.sleep(0.05)
                continue
            atomic_json(TASKS, data)
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

        def due(name: str, seconds: float) -> bool:
            return now_s - float(last.get(name, 0.0)) >= seconds

        if due("mail", MAIL_REFRESH_SECONDS):
            subprocess.Popen(
                [sys.executable, str(REPO / "scripts" / "ai-os" / "raios-mail.py"), "collect"],
                cwd=REPO,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            last["mail"] = now_s
        if due("search_index", SEARCH_REFRESH_SECONDS):
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "raios.search_cortex.engine",
                    "--refresh-index",
                ],
                cwd=REPO,
                env={**os.environ, "PYTHONPATH": str(SRC)},
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            last["search_index"] = now_s
        if due("resources", RESOURCE_REFRESH_SECONDS):
            subprocess.Popen(
                [sys.executable, "-m", "raios.manager.live_manager", "--refresh-resources"],
                cwd=REPO,
                env={**os.environ, "PYTHONPATH": str(SRC)},
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            last["resources"] = now_s
        if due("official", OFFICIAL_REFRESH_SECONDS):
            subprocess.Popen(
                [sys.executable, "-m", "raios.factory_fabric.official_source", "--limit", "2000"],
                cwd=REPO,
                env={**os.environ, "PYTHONPATH": str(SRC)},
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            last["official"] = now_s
        if due("factory", FACTORY_REFRESH_SECONDS):
            subprocess.Popen(
                [sys.executable, "-m", "raios.manager.live_manager", "--refresh-factory"],
                cwd=REPO,
                env={**os.environ, "PYTHONPATH": str(SRC)},
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            last["factory"] = now_s

    def tick(self) -> dict[str, Any]:
        started = time.perf_counter()
        self._spawn_refreshes()
        sources = self.gather()
        snapshot = {
            "schema": "raios.manager-source-snapshot.v1",
            "generated_at": utc(),
            "sources": [s.as_dict() for s in sources],
        }
        snapshot_hash = sha(snapshot["sources"])
        snapshot["snapshot_hash"] = snapshot_hash
        atomic_json(SOURCE_SNAPSHOT, snapshot)

        # Keep the live-source cache current without blocking on embeddings.
        index_result = self.memory.upsert(self._docs(sources), embed_limit=0)
        emitted = self._emit_changes(sources)
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

        reason_due = (
            time.time()
            - float(self.state.setdefault("last_runs", {}).get("reason", 0.0))
            >= REASON_SECONDS
        )
        prior_hash = self.state.get("last_reason_snapshot_hash")
        c5_analysis = load_json(ANALYSIS, {})
        reason_started = False
        if reason_due and (snapshot_hash != prior_hash or gaps):
            reason_started = self._launch_reason(gaps, context, snapshot_hash)
            if reason_started:
                self.state["last_runs"]["reason"] = time.time()
                self.state["last_reason_snapshot_hash"] = snapshot_hash

        created = self._write_tasks(gaps, snapshot_hash)

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

        c5_payload = (
            c5_analysis.get("c5", c5_analysis)
            if isinstance(c5_analysis, dict)
            else {}
        )
        elapsed = round((time.perf_counter() - started) * 1000, 3)
        result = {
            "schema": "raios.live-manager-tick.v2",
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
            "single_task_ledger": str(TASKS),
            "single_cognitive_wal": str(
                REPO / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
            ),
            "second_bus": False,
            "second_task_store": False,
            "second_wal": False,
        }
        atomic_json(HEARTBEAT, result)
        self.state["last_tick"] = result["generated_at"]
        self.state["last_snapshot_hash"] = snapshot_hash
        atomic_json(STATE, self.state)
        return result

    def daemon(self) -> None:
        MANAGER_ROOT.mkdir(parents=True, exist_ok=True)
        lock_handle = INSTANCE_LOCK.open("a+b")
        try:
            import msvcrt

            lock_handle.seek(0)
            if lock_handle.read(1) == b"":
                lock_handle.seek(0)
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
        atomic_json(
            HEARTBEAT,
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
                "single_cognitive_wal": str(
                    REPO / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
                ),
                "second_bus": False,
                "second_task_store": False,
                "second_wal": False,
            },
        )
        while True:
            try:
                result = self.tick()
                log(
                    "tick PASS "
                    f"sources={result['source_count']} "
                    f"live={result['live_source_count']} "
                    f"gaps={result['gap_count']} "
                    f"tasks={len(result['created_tasks'])} "
                    f"latency_ms={result['latency_ms']}"
                )
            except KeyboardInterrupt:
                log("RAIOS live manager stopped")
                return
            except BaseException as exc:
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
    parser.add_argument("--refresh-resources", action="store_true")
    parser.add_argument("--refresh-factory", action="store_true")
    args = parser.parse_args()

    if args.refresh_resources:
        print(json.dumps(refresh_resources(), ensure_ascii=False, indent=2))
        return 0
    if args.refresh_factory:
        print(json.dumps(refresh_factory(), ensure_ascii=False, indent=2))
        return 0

    manager = LiveManager(allow_task_write=not args.no_task_write)
    if args.daemon:
        manager.daemon()
        return 0

    print(json.dumps(manager.tick(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
