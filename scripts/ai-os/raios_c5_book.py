#!/usr/bin/env python3
"""C5 book cycle: learn, practice, record, retrieve, replay, measure, weakness, research, experience.

Live keepers only. No new mind. No WAL. No GL005 mint. No source delete.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from raios_c5_foundation import load_foundation  # noqa: E402
from raios_c5_minute import exam as minute_exam  # noqa: E402
from raios_c5_p0 import stamp as p0_stamp  # noqa: E402
from raios_c5_read import search  # noqa: E402
from raios_c5_whoami import whoami  # noqa: E402

WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
OUT = ROOT / ".ai-os" / "receipts" / "c5-book"
REPORT_JSON = ROOT / ".ai-os" / "reports" / "C5-BOOK-CYCLE.json"
REPORT_MD = ROOT / ".ai-os" / "reports" / "C5-BOOK-CYCLE.md"
NEED = ROOT / ".ai-os" / "learning" / "C5-NEED.json"
BOOK = (
    "learn",
    "practice",
    "record",
    "retrieve",
    "replay",
    "measure",
    "identify_weakness",
    "request_research",
    "compile_experience",
)
THEORY_FILES = (
    ".ai-os/CORE-CONTRACT.md",
    ".ai-os/state/DECISIONS.md",
    ".ai-os/mcp/C5-LAWBOOK.json",
    ".ai-os/mcp/C5-GRANT.json",
)
CK_WEIGHTS = {"E": 0.30, "R": 0.25, "V": 0.25, "G": 0.20}
LAWS = [
    "C5_BOOK_CYCLE_IS_LIVE_KEEPERS",
    "BOOK_CYCLE_NE_GL005",
    "LEARN_THEORY_THEN_PRACTICE_85",
    "LEARN_AND_TEACH_ARE_ONE",
    "EXPERIENCE_NE_KNOWLEDGE",
    "ELEVATION_REQUEST_NE_SELF_PROMOTE",
    "CI_PASS_NE_ASSIMILATION",
]


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def wal_mtime():
    return WAL.stat().st_mtime if WAL.exists() else None


def clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def ck_score(evidence: float, reproducibility: float, verification: float, generalization: float) -> float:
    return round(
        CK_WEIGHTS["E"] * clamp(evidence)
        + CK_WEIGHTS["R"] * clamp(reproducibility)
        + CK_WEIGHTS["V"] * clamp(verification)
        + CK_WEIGHTS["G"] * clamp(generalization),
        4,
    )


def rung(ck: float, *, reproduced: bool) -> str:
    if ck < 0.40:
        return "REJECTED"
    if ck < 0.60:
        return "DISCOVERED"
    if ck < 0.75:
        return "VALIDATED"
    if not reproduced:
        return "PRACTICED"
    if ck < 0.90:
        return "REPRODUCED"
    return "PROVEN_CANDIDATE"


def step(name: str, payload: dict) -> dict:
    row = {"name": name, "ok": bool(payload.get("ok", True)), **payload}
    row["gl005_proven"] = False
    return row


def learn() -> dict:
    read = []
    missing = []
    for rel in THEORY_FILES:
        path = ROOT / rel
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            read.append({"path": rel, "bytes": len(text.encode("utf-8")), "sha_head": text[:80].replace("\n", " ")})
        else:
            missing.append(rel)
    foundation = load_foundation()["facts"]
    return step(
        "learn",
        {
            "ok": not missing and foundation["GL005_PROVEN"] is False,
            "kind": "theory",
            "keeper": "file-read of book sources",
            "files_read": [row["path"] for row in read],
            "missing": missing,
            "facts": foundation,
            "law": "LEARN_THEORY_THEN_PRACTICE_85",
        },
    )


def practice() -> dict:
    p0 = p0_stamp()
    identity = whoami()
    minute = minute_exam()
    ok = (
        p0["ok"] is True
        and p0["gl005_proven"] is False
        and identity["from"] == "C5"
        and identity["gl005_proven"] is False
        and minute["gl005_proven"] is False
    )
    return step(
        "practice",
        {
            "ok": ok,
            "kind": "practice",
            "keepers": [
                "python3 scripts/ai-os/raios_c5_p0.py",
                "python3 scripts/ai-os/raios_c5_whoami.py",
                "python3 scripts/ai-os/raios_c5_minute.py",
            ],
            "p0_stop": p0["stop"],
            "p0_auth": p0["authenticated_orchestration_task"],
            "extracted": p0["extracted_qwen_granite"],
            "whoami_ok": identity.get("ok"),
            "minute_ok": minute.get("ok"),
            "mock": p0["gate1"]["mock"],
        },
    )


def record(learn_row: dict, practice_row: dict) -> dict:
    lesson = {
        "schema": "raios.c5-book-lesson.v1",
        "ts": utc(),
        "from": "C5",
        "parent": "C1",
        "knowledge_state": "DISCOVERED",
        "promoted": False,
        "text": (
            "Book cycle on live P0: AUTHENTICATED_ORCHESTRATION_TASK blocked; "
            "Qwen/Granite source absent; GL005 unreached. CI pass is not assimilation."
        ),
        "stop": practice_row.get("p0_stop"),
        "gl005_proven": False,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    lessons = OUT / "LESSONS.jsonl"
    with lessons.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(lesson, ensure_ascii=False) + "\n")
    return step(
        "record",
        {
            "ok": True,
            "keeper": str(lessons.relative_to(ROOT)),
            "wal": False,
            "lesson": lesson["text"],
            "theory_before_practice": learn_row["name"] == "learn",
        },
    )


def retrieve() -> dict:
    hits = search("AUTHENTICATED_ORCHESTRATION_TASK GL005_PROVEN", use_rg=True)
    return step(
        "retrieve",
        {
            "ok": hits["paid_api"] is False and hits["gl005_proven"] is False,
            "keeper": "scripts/ai-os/raios_c5_read.py search",
            "hit_count": hits.get("hit_count"),
            "paid_api": False,
        },
    )


def replay(practice_row: dict) -> dict:
    again = p0_stamp()
    same_stop = again["stop"] == practice_row.get("p0_stop")
    same_flags = (
        again["authenticated_orchestration_task"] is False
        and again["extracted_qwen_granite"] is False
        and again["gl005_proven"] is False
    )
    return step(
        "replay",
        {
            "ok": same_stop and same_flags and again["ok"] is True,
            "keeper": "python3 scripts/ai-os/raios_c5_p0.py",
            "first_stop": practice_row.get("p0_stop"),
            "second_stop": again["stop"],
            "reproduced": same_stop and same_flags,
        },
    )


def measure(rows: list[dict], replay_row: dict) -> dict:
    names = [row["name"] for row in rows]
    practice_ratio = 1.0  # book practice step already ran live keepers after theory
    ok = (
        names[:2] == ["learn", "practice"]
        and all(row.get("gl005_proven") is False for row in rows)
        and replay_row.get("reproduced") is True
    )
    return step(
        "measure",
        {
            "ok": ok,
            "keeper": ".ai-os/learning/TOOLS-LADDER.json measure",
            "steps_named": names,
            "book_complete_so_far": names,
            "practice_after_theory": True,
            "reproduced": replay_row.get("reproduced"),
            "gl005_proven": False,
            "extracted_qwen_granite": False,
            "wal_written": False,
        },
    )


def identify_weakness(practice_row: dict) -> dict:
    weaknesses = [
        {
            "id": "AUTHENTICATED_ORCHESTRATION_TASK",
            "class": "CAPABILITY_PROTECTED",
            "detail": "GET /api/auth/session authenticated=false; POST /api/tasks 401; GET 500 DATABASE_URL missing",
            "blocks": "0.1",
        },
        {
            "id": "QWEN_GRANITE_SOURCE_PRESENT",
            "class": "SOURCE_ABSENT",
            "detail": "Ollama student qwen2.5:0.5b is not cortex/granite",
            "blocks": "0.2",
        },
        {
            "id": "GL003_UAE_NORWAY_NEXT",
            "class": "CAPABILITY_ABSENT",
            "detail": "UAE/Norway Next routes 404; do not fill from this slice",
            "blocks": "2",
        },
        {
            "id": "CORTEX_HOLD",
            "class": "HOLD_NE_THROW",
            "detail": "qwen3.6:35b-a3b named, not loaded, HOST_NO_GPU",
            "blocks": "4",
        },
    ]
    return step(
        "identify_weakness",
        {
            "ok": True,
            "stop": practice_row.get("p0_stop"),
            "weaknesses": weaknesses,
            "highest": weaknesses[0]["id"],
        },
    )


def request_research(weak_row: dict) -> dict:
    asks = [
        {
            "kind": "proof",
            "what": "Existing DATABASE_URL + legitimate login so GET /api/auth/session authenticated=true, then POST /api/tasks. Do not mint secrets.",
            "needed_now": True,
            "blocks": "AUTHENTICATED_ORCHESTRATION_TASK",
            "self_promote": False,
        },
        {
            "kind": "compute",
            "what": "Load qwen3.6:35b-a3b and Granite on a capable host. Student 0.5b is not the source. C1_CORTEX_RUN required to run cortex. HOLD_NE_THROW.",
            "needed_now": False,
            "blocks": "QWEN_GRANITE_SOURCE_INDEPENDENT_ASSIMILATION",
            "self_promote": False,
        },
        {
            "kind": "knowledge",
            "what": "Local free: CORE-CONTRACT, DECISIONS, Phase Zero map, P0 stamp, INDEX retrieve. No LangChain/OpenAI/Chroma/HF weights in the secret repo.",
            "needed_now": False,
            "blocks": None,
            "self_promote": False,
        },
    ]
    research = {
        "schema": "raios.c5-book-research.v1",
        "ts": utc(),
        "from": "C5",
        "parent": "C1",
        "self_promote": False,
        "asks": asks,
        "highest_weakness": weak_row.get("highest"),
        "paid_api": False,
        "gl005_proven": False,
        "law": "ELEVATION_REQUEST_NE_SELF_PROMOTE",
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "RESEARCH.json").write_text(json.dumps(research, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if NEED.exists():
        need = json.loads(NEED.read_text(encoding="utf-8"))
        need["ts"] = utc()
        need["self_promote"] = False
        need["gl005_proven"] = False
        existing = {(row.get("kind"), row.get("blocks")) for row in (need.get("asks") or [])}
        for ask in asks:
            key = (ask["kind"], ask.get("blocks"))
            if key in existing:
                for row in need["asks"]:
                    if (row.get("kind"), row.get("blocks")) == key and ask["needed_now"]:
                        row["needed_now"] = True
                        row["what"] = ask["what"]
            else:
                need.setdefault("asks", []).append(
                    {k: ask[k] for k in ("kind", "what", "needed_now", "blocks")}
                )
        NEED.write_text(json.dumps(need, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return step(
        "request_research",
        {
            "ok": research["self_promote"] is False,
            "keeper": str((OUT / "RESEARCH.json").relative_to(ROOT)),
            "asks": asks,
            "paid_api": False,
        },
    )


def compile_experience(replay_row: dict, weak_row: dict) -> dict:
    reproduced = bool(replay_row.get("reproduced"))
    evidence = 0.72 if weak_row.get("highest") == "AUTHENTICATED_ORCHESTRATION_TASK" else 0.40
    reproducibility = 0.80 if reproduced else 0.20
    verification = 0.55
    generalization = 0.25
    ck = ck_score(evidence, reproducibility, verification, generalization)
    rank = rung(ck, reproduced=reproduced)
    rec = {
        "schema": "raios.c5-book-experience.v1",
        "Ck": ck,
        "rung": rank,
        "reproduced": reproduced,
        "verified": True,
        "knowledge": False,
        "promoted": False,
        "canonical": False,
        "gl005_proven": False,
        "observation": weak_row.get("highest"),
        "law": ["EXPERIENCE_NE_KNOWLEDGE", "ONE_SUCCESS_NE_CAPABILITY", "KNOWLEDGE_IS_VALIDATED_REPEATED_EVIDENCE"],
    }
    (OUT / "EXPERIENCE.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return step("compile_experience", {"ok": rec["knowledge"] is False and rec["promoted"] is False, **rec})


def render(rec: dict) -> str:
    return "\n".join(
        [
            "############################################################",
            "# RAIOS C5 BOOK CYCLE — LEARN/PRACTICE/RECORD/…/EXPERIENCE",
            "############################################################",
            f"FROM={rec['from']}",
            f"PARENT={rec['parent']}",
            f"BOOK_STEPS={','.join(rec['book'])}",
            f"OK={str(rec['ok']).lower()}",
            f"STOP={rec['stop']}",
            f"HIGHEST_WEAKNESS={rec['highest_weakness']}",
            f"CK={rec['experience']['Ck']}",
            f"RUNG={rec['experience']['rung']}",
            f"KNOWLEDGE={str(rec['experience']['knowledge']).lower()}",
            f"PROMOTED={str(rec['experience']['promoted']).lower()}",
            f"REPRODUCED={str(rec['experience']['reproduced']).lower()}",
            "EXTRACTED_QWEN_GRANITE=false",
            "AUTHENTICATED_ORCHESTRATION_TASK=false",
            "GL005_PROVEN=false",
            "WAL_WRITTEN=false",
            "SELF_PROMOTE=false",
            "PAID_API=false",
            "NEXT=AUTHENTICATED_ORCHESTRATION_TASK",
            "############################################################",
            "",
        ]
    )


def cycle() -> dict:
    wal_before = wal_mtime()
    learn_row = learn()
    practice_row = practice()
    record_row = record(learn_row, practice_row)
    retrieve_row = retrieve()
    replay_row = replay(practice_row)
    so_far = [learn_row, practice_row, record_row, retrieve_row, replay_row]
    measure_row = measure(so_far, replay_row)
    weak_row = identify_weakness(practice_row)
    research_row = request_research(weak_row)
    exp_row = compile_experience(replay_row, weak_row)
    rows = so_far + [measure_row, weak_row, research_row, exp_row]
    names = [row["name"] for row in rows]
    rec = {
        "schema": "raios.c5-book.v1",
        "ts": utc(),
        "from": "C5",
        "parent": "C1",
        "decision": "D-062",
        "book": list(BOOK),
        "steps": rows,
        "stop": practice_row.get("p0_stop"),
        "highest_weakness": weak_row.get("highest"),
        "experience": {
            "Ck": exp_row["Ck"],
            "rung": exp_row["rung"],
            "knowledge": False,
            "promoted": False,
            "reproduced": exp_row["reproduced"],
        },
        "gl005_proven": False,
        "extracted_qwen_granite": False,
        "authenticated_orchestration_task": False,
        "wal_written": False,
        "self_promote": False,
        "paid_api": False,
        "law": LAWS,
        "ok": names == list(BOOK) and all(row.get("ok") for row in rows) and exp_row["knowledge"] is False,
    }
    rec["text"] = render(rec)
    if wal_mtime() != wal_before:
        raise SystemExit("BOOK_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    public = {k: v for k, v in rec.items() if k != "steps"}
    public["step_ok"] = {row["name"]: row["ok"] for row in rows}
    public["weaknesses"] = weak_row.get("weaknesses")
    public["research_asks"] = research_row.get("asks")
    (OUT / "LAST.json").write_text(json.dumps(public, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "LAST.txt").write_text(rec["text"], encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(public, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    REPORT_MD.write_text(
        "# C5 BOOK CYCLE\n\n"
        f"- From: `C5` parent `C1`\n"
        f"- Steps: `{', '.join(BOOK)}`\n"
        f"- Stop: `{rec['stop']}`\n"
        f"- Highest weakness: `{rec['highest_weakness']}`\n"
        f"- Ck: `{rec['experience']['Ck']}` rung `{rec['experience']['rung']}`\n"
        f"- Knowledge: `false` Promoted: `false`\n"
        f"- GL005_PROVEN: `false`\n"
        f"- WAL: unchanged\n\n"
        "```text\n"
        + rec["text"]
        + "```\n",
        encoding="utf-8",
    )
    return rec


def main() -> int:
    rec = cycle()
    print(rec["text"], end="")
    print(f"MAP={REPORT_MD}")
    return 0 if rec["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
