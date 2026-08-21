#!/usr/bin/env python3
"""C5 evidence-grounded answer. Retrieval then read then reason. Zero LLM. No WAL."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from raios_c5_read import search  # noqa: E402

WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
DIGESTS = ROOT / ".ai-os" / "learning" / "DIGESTS.jsonl"
SKIP_PARTS = ("/wal/", ".env", "tokens.local", "node_modules", ".git/")
TERM_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{2,}|[\u0600-\u06FF]{2,}")


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def git_head() -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True)
    return (r.stdout or "").strip()


def wal_mtime():
    return WAL.stat().st_mtime if WAL.exists() else None


def _digest_paths() -> dict[str, str]:
    out: dict[str, str] = {}
    if not DIGESTS.exists():
        return out
    for line in DIGESTS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        sha = rec.get("sha256")
        path = str(rec.get("path") or "")
        if sha and path and not path.startswith("/tmp/"):
            out[str(sha)] = path.replace("\\", "/")
    return out


def _safe_path(rel: str) -> Path | None:
    raw = rel.replace("\\", "/")
    if raw.startswith("/") or ".." in Path(raw).parts:
        return None
    if any(part in f"/{raw}/" for part in SKIP_PARTS):
        return None
    path = (ROOT / raw).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError:
        return None
    if not path.is_file():
        return None
    return path


def _terms(query: str) -> list[str]:
    terms = [t.lower() for t in TERM_RE.findall(query or "")]
    for seat in re.findall(r"\bC[0-5]\b", query or "", re.I):
        if seat.lower() not in terms:
            terms.append(seat.lower())
    return terms


def _extract(text: str, terms: list[str], *, limit: int = 4) -> list[str]:
    chunks = re.split(r"[\n.؟!]+", text)
    scored: list[tuple[int, str]] = []
    for chunk in chunks:
        line = " ".join(chunk.split())
        if len(line) < 24:
            continue
        lower = line.lower()
        score = sum(1 for t in terms if t in lower)
        if score:
            scored.append((score, line[:280]))
    scored.sort(key=lambda row: (-row[0], -len(row[1])))
    seen: list[str] = []
    for _, line in scored:
        if line not in seen:
            seen.append(line)
        if len(seen) >= limit:
            break
    return seen


def ground(query: str) -> dict:
    wal_before = wal_mtime()
    terms = _terms(query)
    found_rec = search(query, use_rg=False)
    lookup = _digest_paths()
    files_found: list[str] = []
    for hit in found_rec.get("hits") or []:
        path = str(hit.get("path") or lookup.get(str(hit.get("doc") or "")) or "")
        path = path.replace("\\", "/")
        if path and path not in files_found:
            files_found.append(path)
        if len(files_found) >= 6:
            break
    files_opened: list[str] = []
    evidence: list[dict] = []
    for rel in files_found[:4]:
        path = _safe_path(rel)
        if path is None:
            continue
        files_opened.append(rel)
        text = path.read_text(encoding="utf-8", errors="ignore")[:8000]
        for snippet in _extract(text, terms):
            evidence.append({"path": rel, "text": snippet})
        if len(evidence) >= 6:
            break
    content_read = bool(files_opened)
    reasoning_entered = bool(evidence)
    if not files_found:
        stop = "RETRIEVAL_EMPTY"
        answer = "لا دليل كافٍ في الفهرس المحلي. أمتنع. GL005_PROVEN=false"
        synthesized = False
        confidence = "abstain"
    elif not evidence:
        stop = "OPENED_NO_EVIDENCE"
        refs = "، ".join(f"`{p}`" for p in files_opened[:4]) or "لا ملفات مقروءة"
        answer = (
            f"وجدت ملفات لكن لم أستخرج جملة مطابقة للسؤال. فتحت: {refs}. "
            "هذا اكتشاف ملفات وليس إجابة معرفية. GL005_PROVEN=false"
        )
        synthesized = False
        confidence = "low"
    else:
        stop = "ANSWER"
        bullets = "\n".join(f"- {row['text']} ({row['path']})" for row in evidence[:5])
        refs = "، ".join(sorted({row["path"] for row in evidence}))
        answer = (
            f"إجابة مبنية على قراءة الملفات لا على قائمة أسمائها:\n{bullets}\n\n"
            f"المراجع: {refs}\nالثقة: medium · model_call=0 · GL005_PROVEN=false"
        )
        synthesized = True
        confidence = "medium"
    rec = {
        "schema": "raios.c5-ground.v1",
        "ts": utc(),
        "from": "C5",
        "query": query,
        "answer": answer,
        "files_found": files_found,
        "files_opened": files_opened,
        "content_read": content_read,
        "evidence_n": len(evidence),
        "reasoning_entered": reasoning_entered,
        "answer_synthesized": synthesized,
        "stop_stage": stop,
        "confidence": confidence,
        "retriever": "scripts/ai-os/raios_c5_read.py:search INDEX.json",
        "ollama_used": False,
        "model_call_count": 0,
        "paid_api": False,
        "wal_written": False,
        "gl005_proven": False,
        "law": [
            "ROLE_IDENTITY_NE_MODEL_IDENTITY",
            "LOCAL_SOURCE_NE_LOCAL_MODEL_EXECUTION",
            "INDEX_HIT_NE_REASONING",
            "FILE_DISCOVERY_NE_FILE_ASSIMILATION",
            "RETRIEVAL_RESULT_NE_COGNITIVE_ANSWER",
        ],
    }
    if wal_mtime() != wal_before:
        raise SystemExit("GROUND_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    rec["ok"] = True
    return rec
