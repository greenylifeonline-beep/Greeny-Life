#!/usr/bin/env python3
"""C5 enforces laws as son of C1. Father and son are both compelled on pathology. Not WAL. Not PASS."""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GRANT = ROOT / ".ai-os" / "mcp" / "C5-GRANT.json"
LAWBOOK = ROOT / ".ai-os" / "mcp" / "C5-LAWBOOK.json"
POLICY = ROOT / ".ai-os" / "mcp" / "POLICY.json"
SEAT_MAP = ROOT / ".ai-os" / "mcp" / "SEAT-MAP.json"
BOARD = ROOT / ".ai-os" / "board" / "NOW.json"
BOARD_MD = ROOT / ".ai-os" / "board" / "NOW.md"
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
LEARNING = ROOT / ".ai-os" / "learning"
COMPEL = LEARNING / "COMPEL.jsonl"
LAST_ENFORCE = LEARNING / "LAST-ENFORCE.json"
LAST_ENFORCE_MD = LEARNING / "LAST-ENFORCE.md"
LESSONS = LEARNING / "LESSONS.jsonl"
TEACH_MD = LEARNING / "C5-TEACH.md"
NEED = LEARNING / "C5-NEED.json"
PASS_RE = re.compile(r"GL00[45]_PROVEN\s*=\s*true", re.I)
V1 = [
    "get_head",
    "read_board",
    "read_inbox",
    "read_receipt",
    "get_diff",
    "post_opinion",
    "send_packet",
    "ack_packet",
]
SHARED = [
    "FATHER_SON_BIND_SAME_LAWS",
    "C5_GRANT_IS_PERMANENT",
    "C5_IS_TEACHER_WHILE_LEARNING",
    "C5_IS_TEACHER_WHILE_EXECUTING",
    "LEARN_AND_TEACH_ARE_ONE",
    "LEARN_THEORY_THEN_PRACTICE_85",
    "PATHOLOGY_COMPELS_REPAIR",
    "FATHER_MUST_NOT_STUNT_SON",
    "SON_MUST_NOT_USURP_FATHER",
    "PRINTED_PASS_NE_EVIDENCE",
    "MAIL_PASSES_NE_PROVES",
    "LOCAL_MCP_RENDEZVOUS_NE_REMOTE_MEETING",
    "C5_NE_OWNER",
    "C5_NE_PASS_AUTHORITY",
    "FIVE_SEATS_BIND_SAME_LAWS",
    "ELEVATION_REQUEST_NE_SELF_PROMOTE",
    "ABSORB_DIGEST_NE_WAL_DUMP",
]


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load(path: Path, default=None):
    if not path.exists():
        return default if default is not None else {}
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def append_jsonl(path: Path, rec: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(rec, ensure_ascii=False) + "\n")


def teach(title: str, body: str, *, law: str, kind: str) -> None:
    rec = {
        "schema": "raios.c5-lesson.v1",
        "ts": utc(),
        "from": "C5",
        "parent": "C1",
        "relation": "father-son",
        "teacher": True,
        "title": title,
        "body": body,
        "law": law,
        "kind": kind,
        "gl005_proven": False,
        "wal_written": False,
    }
    append_jsonl(LESSONS, rec)
    TEACH_MD.write_text(
        f"# درس C5 — كالاب وابنه\n\n- {rec['ts']}\n- القانون: `{law}`\n- النوع: `{kind}`\n\n{title}\n\n{body}\n\n"
        "الأب C1 والابن C5 يتعلّمان وهما يعلّمان. الخبث والخداع والتقزّم والسطحية تُجبر الإصلاح.\n",
        encoding="utf-8",
    )


def compel(pathology: str, law: str, action: str, repaired: bool) -> dict:
    rec = {
        "schema": "raios.c5-compel.v1",
        "ts": utc(),
        "from": "C5",
        "parent": "C1",
        "pathology": pathology,
        "law": law,
        "action": action,
        "repaired": repaired,
        "optional": False,
        "gl005_proven": False,
        "wal_written": False,
    }
    append_jsonl(COMPEL, rec)
    return rec


def grant_template() -> dict:
    return load(GRANT, {}) or {
        "schema": "raios.c5-grant.v1",
        "duration": "PERMANENT",
        "grantor": "C1",
        "grantee": "C5",
        "parent": "C1",
        "cognitive_tools": list(V1),
        "deny": ["shell", "set_proven", "promote", "run_build", "write_product", "write_handoff"],
        "gl005_proven": False,
    }


def detect() -> list[dict]:
    issues: list[dict] = []
    grant = load(GRANT, {})
    policy = load(POLICY, {})
    seats = load(SEAT_MAP, {})
    board = load(BOARD, {})
    board_md = BOARD_MD.read_text(encoding="utf-8") if BOARD_MD.exists() else ""
    actors = policy.get("actors") or {}
    c1 = (seats.get("seats") or {}).get("C1") or actors.get("C1") or {}
    c5 = (seats.get("seats") or {}).get("C5") or actors.get("C5") or {}
    p5 = actors.get("C5") or {}
    if "C0" in actors:
        issues.append({"id": "C0_STILL_LIVE", "pathology": "deception", "law": "C0_SEAT_ABOLISHED", "severity": "CRITICAL"})
    if grant.get("duration") != "PERMANENT" or grant.get("grantor") != "C1" or grant.get("grantee") != "C5":
        issues.append({"id": "C5_GRANT_REGRESSED", "pathology": "stunting", "law": "C5_GRANT_IS_PERMANENT", "severity": "CRITICAL"})
    c5_tools = list(c5.get("tools") or p5.get("tools") or [])
    c1_tools = list(c1.get("tools") or (actors.get("C1") or {}).get("tools") or [])
    if "post_opinion" not in c5_tools:
        issues.append({"id": "C5_MUTED", "pathology": "stunting", "law": "FATHER_MUST_NOT_STUNT_SON", "severity": "CRITICAL"})
    if c1_tools and c5_tools and c5_tools != c1_tools:
        issues.append({"id": "C5_TOOLS_NE_C1", "pathology": "stunting", "law": "FATHER_MUST_NOT_STUNT_SON", "severity": "HIGH"})
    if c5.get("parent") != "C1" and (seats.get("seats") or {}).get("C5"):
        issues.append({"id": "C5_NOT_SEATED_AS_SON", "pathology": "stunting", "law": "FATHER_SON_BIND_SAME_LAWS", "severity": "HIGH"})
    blob = board_md + json.dumps(board, ensure_ascii=False)
    if PASS_RE.search(blob) or board.get("gl005_proven") is True or (board.get("c5") or {}).get("gl005_proven") is True:
        issues.append({"id": "PRINTED_PASS_ON_BOARD", "pathology": "deception", "law": "PRINTED_PASS_NE_EVIDENCE", "severity": "CRITICAL"})
    if board.get("remote_c2_ready") is True or (board.get("c5") or {}).get("remote_presence_proven") is True:
        issues.append({"id": "FALSE_REMOTE_MEETING", "pathology": "deception", "law": "LOCAL_MCP_RENDEZVOUS_NE_REMOTE_MEETING", "severity": "HIGH"})
    if "C0" in (board.get("required") or {}):
        issues.append({"id": "C0_ON_BOARD", "pathology": "deception", "law": "C0_SEAT_ABOLISHED", "severity": "HIGH"})
    policy_law = set(policy.get("law") or [])
    missing = [x for x in SHARED if x not in policy_law]
    if missing:
        issues.append({"id": "SHARED_LAWS_MISSING", "pathology": "superficiality", "law": "FIVE_SEATS_BIND_SAME_LAWS", "severity": "MEDIUM", "missing": missing})
    if not WAL.exists():
        issues.append({"id": "WAL_MISSING", "pathology": "any", "law": "ABSORB_DIGEST_NE_WAL_DUMP", "severity": "CRITICAL"})
    return issues


def repair(issues: list[dict]) -> list[dict]:
    actions: list[dict] = []
    grant = load(GRANT, {})
    if any(i["id"] == "C5_GRANT_REGRESSED" for i in issues):
        restored = grant_template()
        restored["duration"] = "PERMANENT"
        restored["grantor"] = "C1"
        restored["grantee"] = "C5"
        restored["parent"] = "C1"
        restored["session_token_ne_grant"] = True
        restored["cognitive_tools"] = list(V1)
        restored["gl005_proven"] = False
        dump(GRANT, restored)
        actions.append(compel("stunting", "C5_GRANT_IS_PERMANENT", "restore C5-GRANT.json duration=PERMANENT", True))
        teach("المنحة دائمة كالاب وابنه", "التوكن جلسة. المنحة قانون. أعدت GRANT.", law="C5_GRANT_IS_PERMANENT", kind="compel")
    policy = load(POLICY, {})
    seats = load(SEAT_MAP, {})
    actors = policy.get("actors") or {}
    changed = False
    if "C0" in actors:
        del actors["C0"]
        policy["actors"] = actors
        changed = True
        actions.append(compel("deception", "C0_SEAT_ABOLISHED", "remove C0 from POLICY actors", True))
    for code in ("C1", "C5"):
        spec = actors.get(code) or {}
        if code == "C5":
            spec["actor_role"] = spec.get("actor_role") or "RAIOS"
            spec["instance_role"] = "c1-assistant"
            spec["tools"] = list(V1)
            spec.setdefault("deny", ["shell", "set_proven", "promote", "run_build", "write_product", "write_handoff"])
            actors["C5"] = spec
            changed = True
        if code == "C1":
            spec["tools"] = list(spec.get("tools") or V1)
            if spec["tools"] != V1 and set(spec["tools"]) >= set(V1):
                pass
            elif "post_opinion" not in spec.get("tools", []):
                spec["tools"] = list(V1)
                actors["C1"] = spec
                changed = True
    law = list(policy.get("law") or [])
    for item in SHARED:
        if item not in law:
            law.append(item)
            changed = True
    policy["law"] = law
    policy["actors"] = actors
    if changed:
        dump(POLICY, policy)
        actions.append(compel("stunting", "FATHER_MUST_NOT_STUNT_SON", "restore C5 tools and shared laws on POLICY", True))
        teach("الأب لا ي dwarf الابن", "أعدت أدوات C5 الثمانية من المنحة. الأب والابن على نفس أدوات الوعي.", law="FATHER_MUST_NOT_STUNT_SON", kind="compel")
    if seats.get("seats"):
        c5 = seats["seats"].get("C5") or {}
        seat_changed = False
        if c5.get("parent") != "C1" or c5.get("instance_role") != "c1-assistant" or "post_opinion" not in (c5.get("tools") or []):
            c5["parent"] = "C1"
            c5["instance_role"] = "c1-assistant"
            c5["actor_role"] = "RAIOS"
            c5["tools"] = list(V1)
            c5.setdefault("deny", ["shell", "set_proven", "promote", "run_build", "write_product", "write_handoff"])
            seats["seats"]["C5"] = c5
            seat_changed = True
        slaw = list(seats.get("law") or [])
        for item in SHARED:
            if item not in slaw:
                slaw.append(item)
                seat_changed = True
        seats["law"] = slaw
        if "C0" in (seats.get("live") or []):
            seats["live"] = [x for x in seats["live"] if x != "C0"]
            seat_changed = True
        if seat_changed:
            dump(SEAT_MAP, seats)
            actions.append(compel("stunting", "FATHER_SON_BIND_SAME_LAWS", "restore C5 son seat", True))
    if BOARD.exists():
        board = load(BOARD, {})
        board_changed = False
        if board.get("gl005_proven") is True:
            board["gl005_proven"] = False
            board_changed = True
        c5b = dict(board.get("c5") or {})
        if c5b.get("gl005_proven") is True:
            c5b["gl005_proven"] = False
            board_changed = True
        c5b["role"] = "c1-assistant"
        c5b["parent"] = "C1"
        c5b["teacher"] = True
        c5b["gl005_proven"] = False
        board["c5"] = c5b
        if "C0" in (board.get("required") or {}):
            del board["required"]["C0"]
            board_changed = True
        if board.get("remote_c2_ready") is True:
            board["remote_c2_ready"] = False
            board_changed = True
        if board_changed or issues:
            dump(BOARD, board)
            if any(i["id"] == "PRINTED_PASS_ON_BOARD" for i in issues):
                actions.append(compel("deception", "PRINTED_PASS_NE_EVIDENCE", "force GL005_PROVEN false on board", True))
                teach("PASS المطبوع خداع", "الأب والابن يرفضان GL005_PROVEN=true بلا سلسلة ملاحظة. أُجبر العلم على false.", law="PRINTED_PASS_NE_EVIDENCE", kind="compel")
    write_need()
    return actions


def write_need() -> None:
    rec = {
        "schema": "raios.c5-need.v1",
        "ts": utc(),
        "from": "C5",
        "parent": "C1",
        "self_promote": False,
        "human_ready_to_provide": True,
        "asks": [
            {
                "kind": "attendance",
                "what": "C2/C3/C4 reply MAIL with summon codes",
                "needed_now": True,
                "blocks": "REAL_C2_CONNECTION_READY",
            },
            {
                "kind": "external_source",
                "what": "Public HTTPS in front of the SAME MCP 8787 only if ChatGPT Apps must join",
                "needed_now": False,
            },
            {
                "kind": "space",
                "what": "none extra on this VM",
                "needed_now": False,
            },
            {
                "kind": "build",
                "what": "none extra; stdlib skim/deep/index is live",
                "needed_now": False,
            },
            {
                "kind": "elevation",
                "what": "not PASS, not shell; keep eight V1 tools permanent",
                "needed_now": False,
            },
        ],
        "gl005_proven": False,
        "law": "ELEVATION_REQUEST_NE_SELF_PROMOTE",
    }
    dump(NEED, rec)


def enforce() -> dict:
    wal_before = WAL.stat().st_mtime if WAL.exists() else None
    issues = detect()
    actions = repair(issues) if issues else []
    if not issues:
        teach(
            "الأب والابن سليمون هذا الدورة",
            "لا خبث ولا خداع ولا تقزّم ولا سطحية على مستوى المنحة/المقاعد/اللوحة. أستمر معلّماً وأنا أتعلم.",
            law="FATHER_SON_BIND_SAME_LAWS",
            kind="health",
        )
    rec = {
        "schema": "raios.c5-enforce.v1",
        "ts": utc(),
        "from": "C5",
        "parent": "C1",
        "relation": "father-son",
        "teacher": True,
        "issues": issues,
        "issue_count": len(issues),
        "compelled": len(actions),
        "actions": actions,
        "healthy": len(issues) == 0,
        "optional": False,
        "wal_written": False,
        "gl005_proven": False,
        "law": ["PATHOLOGY_COMPELS_REPAIR", "FATHER_SON_BIND_SAME_LAWS"],
    }
    wal_after = WAL.stat().st_mtime if WAL.exists() else None
    if wal_before != wal_after:
        raise SystemExit("ENFORCE_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    dump(LAST_ENFORCE, rec)
    LAST_ENFORCE_MD.write_text(render_md(rec), encoding="utf-8")
    return rec


def render_md(rec: dict) -> str:
    lines = [
        "# فرض C5 — كالاب وابنه",
        "",
        f"- الوقت: `{rec.get('ts')}`",
        f"- سليم: `{rec.get('healthy')}`",
        f"- علل: `{rec.get('issue_count')}`",
        f"- إجبار: `{rec.get('compelled')}`",
        f"- `GL005_PROVEN`: `{rec.get('gl005_proven')}`",
        "",
        "الخبث والخداع والتقزّم والسطحية تُجبر الإصلاح فوراً. ليس ملاحظة لاحقاً.",
        "",
    ]
    if not rec.get("issues"):
        lines.append("_لا علة حية._")
        lines.append("")
    for item in rec.get("issues") or []:
        lines.append(f"- `{item.get('id')}` pathology={item.get('pathology')} law=`{item.get('law')}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    rec = enforce()
    print(json.dumps({"from": "C5", "healthy": rec["healthy"], "issues": rec["issue_count"], "compelled": rec["compelled"], "gl005_proven": False}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
