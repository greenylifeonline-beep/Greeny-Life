#!/usr/bin/env python3
"""C5 evidence-grounded answer. Retrieval then read then reason. Zero LLM. No WAL."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from raios_c5_read import search  # noqa: E402

WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
DIGESTS = ROOT / ".ai-os" / "learning" / "DIGESTS.jsonl"
SEAT_MAP = ROOT / ".ai-os" / "mcp" / "SEAT-MAP.json"
SKIP_PARTS = ("/wal/", ".env", "tokens.local", "node_modules", ".git/")
TERM_RE = re.compile(r"[A-Za-z][A-Za-z0-9_]{2,}|[\u0600-\u06FF]{2,}")
BOOST = (
    ".ai-os/mcp/SEAT-MAP.json",
    ".ai-os/mcp/C5-GRANT.json",
    ".ai-os/council/METHOD.md",
    ".ai-os/council/ATTENDANCE.md",
    ".ai-os/council/",
    ".ai-os/summon/",
    ".ai-os/learning/C5-MIND.md",
)
DEMOTE = (
    "C1-GIT-MEMORY.md",
    ".ai-os/board/",
    ".ai-os/mail/",
    ".ai-os/channel/",
    ".ai-os/reports/",
    ".ai-os/receipts/",
)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def _canon(query: str) -> list[str]:
    extra: list[str] = []
    if re.search(r"\bC[0-5]\b", query or "", re.I):
        extra.append(".ai-os/mcp/SEAT-MAP.json")
    if "مجلس" in (query or "") or "council" in (query or "").lower():
        extra.extend([".ai-os/council/METHOD.md", ".ai-os/council/ATTENDANCE.md"])
    return extra


def _score(path: str) -> int:
    score = 0
    for i, boost in enumerate(BOOST):
        if boost in path:
            score += 80 - i
            break
    for demote in DEMOTE:
        if demote in path:
            score -= 50
    return score


def _rank(paths: list[str]) -> list[str]:
    indexed = list(enumerate(paths))
    indexed.sort(key=lambda row: (-_score(row[1]), row[0]))
    return [path for _, path in indexed]


def _noisy(text: str) -> bool:
    compact = " ".join(text.split())
    if compact.count('"') >= 6:
        return True
    if compact.count("{") + compact.count("}") >= 2:
        return True
    if compact.startswith("{") or compact.startswith("[") or compact.startswith('"'):
        return True
    return False


def _extract(text: str, terms: list[str], *, limit: int = 4) -> list[str]:
    lines = [" ".join(ln.split()) for ln in text.splitlines()]
    scored: list[tuple[int, str]] = []
    for i, line in enumerate(lines):
        if not line:
            continue
        lower = line.lower()
        score = sum(1 for t in terms if t in lower)
        if not score:
            continue
        lo = max(0, i - 1)
        hi = min(len(lines), i + 3)
        window = " ".join(x for x in lines[lo:hi] if x)[:360]
        if len(window) < 24 or _noisy(window):
            continue
        scored.append((score, window))
    scored.sort(key=lambda row: (-row[0], -len(row[1])))
    seen: list[str] = []
    for _, line in scored:
        if line not in seen:
            seen.append(line)
        if len(seen) >= limit:
            break
    return seen


def _seat_evidence(query: str) -> list[dict]:
    if not SEAT_MAP.is_file():
        return []
    try:
        seats = (json.loads(SEAT_MAP.read_text(encoding="utf-8")).get("seats") or {})
    except json.JSONDecodeError:
        return []
    out: list[dict] = []
    for seat in re.findall(r"\bC[0-5]\b", query or "", re.I):
        row = seats.get(seat.upper()) or {}
        if not row:
            continue
        text = (
            f"{seat.upper()} actor_role={row.get('actor_role')} "
            f"instance={row.get('instance_role')} "
            f"{row.get('name_ar') or ''} — {str(row.get('notes') or '')[:180]}"
        )
        out.append({"path": ".ai-os/mcp/SEAT-MAP.json", "text": " ".join(text.split())})
    return out


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
        if len(files_found) >= 8:
            break
    for extra in _canon(query):
        if extra not in files_found:
            files_found.insert(0, extra)
    files_found = _rank(files_found)
    files_opened: list[str] = []
    evidence: list[dict] = _seat_evidence(query)
    seat_read = {row["path"] for row in evidence}
    for rel in files_found[:6]:
        path = _safe_path(rel)
        if path is None:
            continue
        if rel not in files_opened:
            files_opened.append(rel)
        if rel in seat_read and rel.endswith(".json"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")[:12000]
        for snippet in _extract(text, terms):
            evidence.append({"path": rel, "text": snippet})
        if len(files_opened) >= 4:
            break
    # de-dupe evidence text
    uniq: list[dict] = []
    for row in evidence:
        text = row["text"]
        replaced = False
        drop = False
        for i, other in enumerate(uniq):
            if text == other["text"]:
                drop = True
                break
            if text in other["text"]:
                drop = True
                break
            if other["text"] in text:
                uniq[i] = row
                replaced = True
                break
        if drop or replaced:
            continue
        uniq.append(row)
    evidence = uniq
    content_read = bool(files_opened)
    reasoning_entered = bool(evidence)
    if not files_found and not evidence:
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
            "إجابة مبنية على قراءة المحتوى لا على أسماء الملفات:\n"
            f"{bullets}\n\n"
            f"المراجع: {refs}\n"
            "الثقة: medium · model_call=0 · ollama_used=false · GL005_PROVEN=false"
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


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    query = " ".join(args).strip() or "ما دور C4 في المجلس"
    rec = ground(query)
    print(rec["answer"])
    return 0 if rec["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
