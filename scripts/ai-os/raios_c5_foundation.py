#!/usr/bin/env python3
"""C1 foundation for every later result. CI pass is not assimilation. No source delete. No GL005 mint."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
STATE = ROOT / ".ai-os" / "state" / "FOUNDATION.json"
INDEX = ROOT / ".ai-os" / "learning" / "INDEX.json"
OUT = ROOT / ".ai-os" / "receipts" / "c5-foundation"
CI_COMMIT = "1e28f845b9530777b7378298885e986c01feaa0c"
LOCKED = {
    "CI_1e28f84": "PASS",
    "CI_68af867": "PASS",
    "EXTRACTED_QWEN_GRANITE": False,
    "SAFE_TO_REMOVE_SOURCE": False,
    "GL005_PROVEN": False,
    "AUTHENTICATED_ORCHESTRATION_TASK": False,
}
LAWS = [
    "CI_PASS_NE_ASSIMILATION",
    "CI_PASS_NE_GL005",
    "EXTRACT_CLAIM_NE_ASSIMILATION",
    "SAFE_TO_REMOVE_SOURCE_REQUIRES_INDEPENDENT_EXECUTION",
    "PRINTED_PASS_NE_EVIDENCE",
    "HOLD_NE_THROW",
    "MOCK_PATH_NE_ORCHESTRATION_TASK",
    "STUDENT_NE_EXTRACTION",
    "SOURCE_DELETION_FORBIDDEN_UNTIL_INDEPENDENT_EXECUTION",
    "AUTHENTICATED_ORCHESTRATION_TASK_NE_GL005",
]
P0_NEXT = [
    "AUTHENTICATED_ORCHESTRATION_TASK",
    "QWEN_GRANITE_SOURCE_INDEPENDENT_ASSIMILATION",
    "GL005",
]


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def wal_mtime():
    return WAL.stat().st_mtime if WAL.exists() else None


def load_foundation() -> dict:
    if STATE.exists():
        rec = json.loads(STATE.read_text(encoding="utf-8"))
    else:
        rec = {"schema": "raios.c1-foundation.v1", "facts": {}}
    facts = dict(rec.get("facts") or {})
    facts["CI_1e28f84"] = "PASS"
    facts["CI_68af867"] = "PASS"
    facts["EXTRACTED_QWEN_GRANITE"] = False
    facts["SAFE_TO_REMOVE_SOURCE"] = False
    facts["GL005_PROVEN"] = False
    facts["AUTHENTICATED_ORCHESTRATION_TASK"] = False
    rec["facts"] = facts
    rec["ci_commit"] = CI_COMMIT
    rec["law"] = list(LAWS)
    rec["next"] = list(P0_NEXT)
    rec["gl005_proven"] = False
    rec["wal_written"] = False
    return rec


def http(method: str, url: str, data: bytes | None = None) -> dict:
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json", "User-Agent": "raios-c5-foundation/1"},
    )
    try:
        with urllib.request.urlopen(req, timeout=4) as resp:
            body = resp.read()[:8000]
            return {"ok": True, "code": resp.status, "body": body.decode("utf-8", "replace")}
    except urllib.error.HTTPError as exc:
        body = exc.read()[:8000]
        return {"ok": False, "code": exc.code, "body": body.decode("utf-8", "replace")}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "code": None, "error": type(exc).__name__}


def probe_gl005() -> dict:
    base = "http://127.0.0.1:3000"
    session = http("GET", base + "/api/auth/session")
    get_t = http("GET", base + "/api/tasks")
    post = http("POST", base + "/api/tasks", b'{"title":"foundation-gate"}')
    status = "UNPROVEN"
    detail = "authenticated mutation not observed"
    if get_t.get("code") == 500:
        status = "BLOCKED"
        detail = "GET /api/tasks 500 DATABASE_URL missing"
    if post.get("code") == 401:
        status = "BLOCKED"
        detail = "POST /api/tasks 401 Authentication required; GET 500 DATABASE_URL missing"
    return {
        "status": status,
        "detail": detail,
        "session_code": session.get("code"),
        "get_tasks_code": get_t.get("code"),
        "post_tasks_code": post.get("code"),
        "post_body_head": (post.get("body") or "")[:180],
        "get_body_head": (get_t.get("body") or "")[:180],
        "gl005_proven": False,
    }


def probe_sources() -> dict:
    models: list[str] = []
    ollama = http("GET", "http://127.0.0.1:11434/api/tags")
    if ollama.get("ok"):
        try:
            payload = json.loads(ollama.get("body") or "{}")
            models = [str(row.get("name") or "") for row in (payload.get("models") or [])]
        except json.JSONDecodeError:
            models = []
    postings: dict = {}
    if INDEX.exists():
        try:
            postings = (json.loads(INDEX.read_text(encoding="utf-8")).get("postings") or {})
        except json.JSONDecodeError:
            postings = {}
    wanted = {
        "qwen3.6:35b-a3b": "qwen3.6:35b-a3b" in models,
        "qwen2.5:13b": any(n.startswith("qwen2.5:13b") for n in models),
        "qwq": any(n.startswith("qwq") for n in models),
        "granite": any("granite" in n for n in models),
        "qwen2.5:0.5b": "qwen2.5:0.5b" in models,
    }
    return {
        "ollama_models": models,
        "source_present": wanted,
        "index_granite": len(postings.get("granite") or []),
        "index_qwq": len(postings.get("qwq") or []),
        "index_13b": len(postings.get("13b") or []),
        "extracted_qwen_granite": False,
        "student_ne_extraction": True,
        "safe_to_remove_source": False,
    }


def render(facts: dict, gl005: dict, sources: dict) -> str:
    return "\n".join(
        [
            "############################################################",
            "# RAIOS C1 FOUNDATION — BASIS FOR LATER RESULTS",
            "############################################################",
            f"CI(1e28f84)={facts['CI_1e28f84']}",
            "CI(68af867)=PASS",
            "EXTRACTED_QWEN_GRANITE=false",
            "SAFE_TO_REMOVE_SOURCE=false",
            "GL005_PROVEN=false",
            "AUTHENTICATED_ORCHESTRATION_TASK=false",
            "CI_PASS_NE_ASSIMILATION=true",
            "CI_PASS_NE_GL005=true",
            f"GL005_STATUS={gl005['status']}",
            f"GL005_DETAIL={gl005['detail']}",
            f"OLLAMA_MODELS={','.join(sources['ollama_models']) or 'none'}",
            "QWEN_GRANITE_SOURCE_PRESENT=false",
            "NEXT=AUTHENTICATED_ORCHESTRATION_TASK;THEN_QWEN_GRANITE_ASSIMILATION;THEN_GL005",
            "############################################################",
            "",
        ]
    )


def stamp() -> dict:
    wal_before = wal_mtime()
    foundation = load_foundation()
    gl005 = probe_gl005()
    sources = probe_sources()
    rec = {
        "schema": "raios.c5-foundation-stamp.v1",
        "ts": utc(),
        "from": "C2",
        "parent": "C1",
        "decision": "D-059",
        "facts": foundation["facts"],
        "ci_commit": CI_COMMIT,
        "gl005": gl005,
        "sources": sources,
        "next": list(P0_NEXT),
        "p0_decision": "D-060",
        "law": LAWS,
        "gl005_proven": False,
        "extracted_qwen_granite": False,
        "safe_to_remove_source": False,
        "wal_written": False,
        "ok": True,
    }
    rec["text"] = render(foundation["facts"], gl005, sources)
    if wal_mtime() != wal_before:
        raise SystemExit("FOUNDATION_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "LAST.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "LAST.txt").write_text(rec["text"], encoding="utf-8")
    return rec


def main() -> int:
    rec = stamp()
    print(rec["text"], end="")
    return 0 if rec["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
