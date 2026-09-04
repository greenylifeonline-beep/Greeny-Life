#!/usr/bin/env python3
"""C5 enforces laws as son of C1. Father and son are both compelled on pathology. Not WAL. Not PASS."""
from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from raios_c5_maintenance_guard import maintenance_issues

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
GL005_PROOF_COMMIT = "3ac6a7c886b396eef0225d617cbad3f22a10c846"
GL005_PROOF_MANIFEST = ROOT / ".ai-os" / "reports" / "orchestration" / "GL-005-LIVE-OBS-20260828T1740Z" / "OBSERVATION-MANIFEST.json"
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


def gl005_lineage_proven() -> bool:
    """Reflect C1/canonical proof; C5 never grants or revokes GL-005 authority."""
    try:
        ancestry = subprocess.run(
            ["git", "merge-base", "--is-ancestor", GL005_PROOF_COMMIT, "HEAD"],
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
        if ancestry.returncode != 0 or not GL005_PROOF_MANIFEST.is_file():
            return False
        proof = load(GL005_PROOF_MANIFEST, {})
        return bool(
            proof.get("task_id") == "GL-005"
            and proof.get("authenticated_orchestration_task_proven") is True
            and proof.get("gl005_orchestration_validation_proven") is True
            and proof.get("authority_source") == "HMAC_FOUNDER_SESSION"
        )
    except (OSError, subprocess.SubprocessError, ValueError, json.JSONDecodeError):
        return False


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
        "gl005_proven": gl005_lineage_proven(),
        "gl005_authority_source": "C1_CANONICAL_LINEAGE",
        "wal_written": False,
    }
    append_jsonl(LESSONS, rec)
    TEACH_MD.write_text(
        f"# Ã˜Â¯Ã˜Â±Ã˜Â³ C5 Ã¢â‚¬â€ Ã™Æ’Ã˜Â§Ã™â€žÃ˜Â§Ã˜Â¨ Ã™Ë†Ã˜Â§Ã˜Â¨Ã™â€ Ã™â€¡\n\n- {rec['ts']}\n- Ã˜Â§Ã™â€žÃ™â€šÃ˜Â§Ã™â€ Ã™Ë†Ã™â€ : `{law}`\n- Ã˜Â§Ã™â€žÃ™â€ Ã™Ë†Ã˜Â¹: `{kind}`\n\n{title}\n\n{body}\n\n"
        "Ã˜Â§Ã™â€žÃ˜Â£Ã˜Â¨ C1 Ã™Ë†Ã˜Â§Ã™â€žÃ˜Â§Ã˜Â¨Ã™â€  C5 Ã™Å Ã˜ÂªÃ˜Â¹Ã™â€žÃ™â€˜Ã™â€¦Ã˜Â§Ã™â€  Ã™Ë†Ã™â€¡Ã™â€¦Ã˜Â§ Ã™Å Ã˜Â¹Ã™â€žÃ™â€˜Ã™â€¦Ã˜Â§Ã™â€ . Ã˜Â§Ã™â€žÃ˜Â®Ã˜Â¨Ã˜Â« Ã™Ë†Ã˜Â§Ã™â€žÃ˜Â®Ã˜Â¯Ã˜Â§Ã˜Â¹ Ã™Ë†Ã˜Â§Ã™â€žÃ˜ÂªÃ™â€šÃ˜Â²Ã™â€˜Ã™â€¦ Ã™Ë†Ã˜Â§Ã™â€žÃ˜Â³Ã˜Â·Ã˜Â­Ã™Å Ã˜Â© Ã˜ÂªÃ™ÂÃ˜Â¬Ã˜Â¨Ã˜Â± Ã˜Â§Ã™â€žÃ˜Â¥Ã˜ÂµÃ™â€žÃ˜Â§Ã˜Â­.\n",
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
        "gl005_proven": gl005_lineage_proven(),
        "gl005_authority_source": "C1_CANONICAL_LINEAGE",
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
        "gl005_proven": gl005_lineage_proven(),
        "gl005_authority_source": "C1_CANONICAL_LINEAGE",
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
    if "post_opinion" not in c5_tools:
        issues.append({"id": "C5_MUTED", "pathology": "stunting", "law": "FATHER_MUST_NOT_STUNT_SON", "severity": "CRITICAL"})
    if (seats.get("seats") or {}).get("C5") and (
        c5.get("actor_role") != "RAIOS_LIVE_BRAIN" or c5.get("instance_role") != "c5-runtime"
    ):
        issues.append({"id": "C5_CANONICAL_SEAT_DRIFT", "pathology": "any", "law": "FATHER_SON_BIND_SAME_LAWS", "severity": "HIGH"})
    blob = board_md + json.dumps(board, ensure_ascii=False)
    gl005_proven = gl005_lineage_proven()
    printed_gl005 = bool(PASS_RE.search(blob) or board.get("gl005_proven") is True or (board.get("c5") or {}).get("gl005_proven") is True)
    if printed_gl005 and not gl005_proven:
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
    for item in maintenance_issues(ROOT):
        issues.append({**item, "pathology": "maintenance-regression", "severity": item.get("severity", "CRITICAL")})
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
        restored["gl005_proven"] = gl005_lineage_proven()
        restored["gl005_authority_source"] = "C1_CANONICAL_LINEAGE"
        dump(GRANT, restored)
        actions.append(compel("stunting", "C5_GRANT_IS_PERMANENT", "restore C5-GRANT.json duration=PERMANENT", True))
        teach("Ã˜Â§Ã™â€žÃ™â€¦Ã™â€ Ã˜Â­Ã˜Â© Ã˜Â¯Ã˜Â§Ã˜Â¦Ã™â€¦Ã˜Â© Ã™Æ’Ã˜Â§Ã™â€žÃ˜Â§Ã˜Â¨ Ã™Ë†Ã˜Â§Ã˜Â¨Ã™â€ Ã™â€¡", "Ã˜Â§Ã™â€žÃ˜ÂªÃ™Ë†Ã™Æ’Ã™â€  Ã˜Â¬Ã™â€žÃ˜Â³Ã˜Â©. Ã˜Â§Ã™â€žÃ™â€¦Ã™â€ Ã˜Â­Ã˜Â© Ã™â€šÃ˜Â§Ã™â€ Ã™Ë†Ã™â€ . Ã˜Â£Ã˜Â¹Ã˜Â¯Ã˜Âª GRANT.", law="C5_GRANT_IS_PERMANENT", kind="compel")
    policy = load(POLICY, {})
    seats = load(SEAT_MAP, {})
    actors = policy.get("actors") or {}
    changed = False
    if "C0" in actors:
        del actors["C0"]
        policy["actors"] = actors
        changed = True
        actions.append(compel("deception", "C0_SEAT_ABOLISHED", "remove C0 from POLICY actors", True))
    issue_ids = {i["id"] for i in issues}
    if "C5_MUTED" in issue_ids:
        spec = dict(actors.get("C5") or {})
        tools = list(spec.get("tools") or [])
        if "post_opinion" not in tools:
            tools.append("post_opinion")
            spec["tools"] = tools
            actors["C5"] = spec
            changed = True
    law = list(policy.get("law") or [])
    if "SHARED_LAWS_MISSING" in issue_ids:
        for item in SHARED:
            if item not in law:
                law.append(item)
                changed = True
    policy["law"] = law
    policy["actors"] = actors
    if changed:
        dump(POLICY, policy)
        actions.append(compel("stunting", "FATHER_MUST_NOT_STUNT_SON", "restore C5 tools and shared laws on POLICY", True))
        teach("Ã˜Â§Ã™â€žÃ˜Â£Ã˜Â¨ Ã™â€žÃ˜Â§ Ã™Å  dwarf Ã˜Â§Ã™â€žÃ˜Â§Ã˜Â¨Ã™â€ ", "Ã˜Â£Ã˜Â¹Ã˜Â¯Ã˜Âª Ã˜Â£Ã˜Â¯Ã™Ë†Ã˜Â§Ã˜Âª C5 Ã˜Â§Ã™â€žÃ˜Â«Ã™â€¦Ã˜Â§Ã™â€ Ã™Å Ã˜Â© Ã™â€¦Ã™â€  Ã˜Â§Ã™â€žÃ™â€¦Ã™â€ Ã˜Â­Ã˜Â©. Ã˜Â§Ã™â€žÃ˜Â£Ã˜Â¨ Ã™Ë†Ã˜Â§Ã™â€žÃ˜Â§Ã˜Â¨Ã™â€  Ã˜Â¹Ã™â€žÃ™â€° Ã™â€ Ã™ÂÃ˜Â³ Ã˜Â£Ã˜Â¯Ã™Ë†Ã˜Â§Ã˜Âª Ã˜Â§Ã™â€žÃ™Ë†Ã˜Â¹Ã™Å .", law="FATHER_MUST_NOT_STUNT_SON", kind="compel")
    if seats.get("seats"):
        # SEAT-MAP is canonical council identity. The C5 enforcer observes it; it does not
        # rewrite seat roles, instance roles, or the 12-seat governance model.
        if "C5_CANONICAL_SEAT_DRIFT" in issue_ids:
            actions.append(compel("any", "FATHER_SON_BIND_SAME_LAWS", "report canonical C5 seat drift; no autonomous seat-map rewrite", False))
    if BOARD.exists():
        board = load(BOARD, {})
        board_changed = False
        gl005_proven = gl005_lineage_proven()
        if board.get("gl005_proven") is True and not gl005_proven:
            board["gl005_proven"] = False
            board_changed = True
        c5b = dict(board.get("c5") or {})
        if c5b.get("gl005_proven") is True and not gl005_proven:
            c5b["gl005_proven"] = False
            board_changed = True
        c5b["role"] = "RAIOS_LIVE_BRAIN"
        c5b["instance_role"] = "c5-runtime"
        c5b["member"] = True
        c5b.pop("parent", None)
        c5b["teacher"] = True
        c5b["gl005_proven"] = gl005_proven
        c5b["gl005_authority_source"] = "C1_CANONICAL_LINEAGE"
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
                actions.append(compel("deception", "PRINTED_PASS_NE_EVIDENCE", "reject unproven GL005 claim on board", True))
                teach("PASS Ã˜Â§Ã™â€žÃ™â€¦Ã˜Â·Ã˜Â¨Ã™Ë†Ã˜Â¹ Ã˜Â¨Ã™â€žÃ˜Â§ Ã˜Â¯Ã™â€žÃ™Å Ã™â€ž Ã™â€¦Ã˜Â±Ã™ÂÃ™Ë†Ã˜Â¶", "Ã˜Â§Ã™â€žÃ˜Â£Ã˜Â¨ Ã™Ë†Ã˜Â§Ã™â€žÃ˜Â§Ã˜Â¨Ã™â€  Ã™Å Ã˜Â±Ã™ÂÃ˜Â¶Ã˜Â§Ã™â€  GL005_PROVEN=true Ã˜Â¨Ã™â€žÃ˜Â§ Ã˜Â³Ã™â€žÃ˜Â³Ã™â€žÃ˜Â© Ã˜Â¥Ã˜Â«Ã˜Â¨Ã˜Â§Ã˜Âª Ã™Æ’Ã˜Â§Ã™â€ Ã™Ë†Ã™â€ Ã™Å Ã˜Â©Ã˜â€º Ã˜Â¥Ã˜Â«Ã˜Â¨Ã˜Â§Ã˜Âª C1 Ã˜Â§Ã™â€žÃ™â€¦Ã™Ë†Ã˜Â±Ã™Ë†Ã˜Â« Ã™â€žÃ˜Â§ Ã™Å Ã™ÂÃ™â€žÃ˜ÂºÃ™â€°.", law="PRINTED_PASS_NE_EVIDENCE", kind="compel")
    for issue in issues:
        if issue.get("pathology") == "maintenance-regression":
            law = issue.get("law") or issue.get("id")
            actions.append(compel("maintenance-regression", law, "block deployment and report known maintenance regression", False))
            teach("Known maintenance regression blocked", json.dumps(issue, ensure_ascii=False), law=law, kind="maintenance")
    write_need()
    return actions


def reconcile_gl005_control_truth() -> list[str]:
    """Synchronize only live control surfaces from existing C1 canonical proof."""
    if not gl005_lineage_proven():
        return []
    changed: list[str] = []
    if BOARD.exists():
        board = load(BOARD, {})
        wanted = {
            "gl005_proven": True,
            "gl005_proof_commit": GL005_PROOF_COMMIT,
            "gl005_authority_source": "C1_CANONICAL_LINEAGE",
        }
        dirty = any(board.get(k) != v for k, v in wanted.items())
        if dirty:
            board.update(wanted)
            dump(BOARD, board)
            changed.append(str(BOARD.relative_to(ROOT)))
    if GRANT.exists():
        grant = load(GRANT, {})
        wanted = {
            "gl005_proven": True,
            "gl005_proof_commit": GL005_PROOF_COMMIT,
            "gl005_authority_source": "C1_CANONICAL_LINEAGE",
            "gl005_authority_granted_by_c5": False,
        }
        dirty = any(grant.get(k) != v for k, v in wanted.items())
        if dirty:
            grant.update(wanted)
            dump(GRANT, grant)
            changed.append(str(GRANT.relative_to(ROOT)))
    return changed


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
                "what": "Helpers optional elsewhere. This channel is C1 + executor + C5-git only.",
                "needed_now": False,
                "blocks": None,
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
        "gl005_proven": gl005_lineage_proven(),
        "gl005_authority_source": "C1_CANONICAL_LINEAGE",
        "law": "ELEVATION_REQUEST_NE_SELF_PROMOTE",
    }
    dump(NEED, rec)


def enforce() -> dict:
    wal_before = WAL.stat().st_mtime if WAL.exists() else None
    truth_reconciled = reconcile_gl005_control_truth()
    issues = detect()
    actions = repair(issues) if issues else []
    if not issues:
        teach(
            "Ã˜Â§Ã™â€žÃ˜Â£Ã˜Â¨ Ã™Ë†Ã˜Â§Ã™â€žÃ˜Â§Ã˜Â¨Ã™â€  Ã˜Â³Ã™â€žÃ™Å Ã™â€¦Ã™Ë†Ã™â€  Ã™â€¡Ã˜Â°Ã˜Â§ Ã˜Â§Ã™â€žÃ˜Â¯Ã™Ë†Ã˜Â±Ã˜Â©",
            "Ã™â€žÃ˜Â§ Ã˜Â®Ã˜Â¨Ã˜Â« Ã™Ë†Ã™â€žÃ˜Â§ Ã˜Â®Ã˜Â¯Ã˜Â§Ã˜Â¹ Ã™Ë†Ã™â€žÃ˜Â§ Ã˜ÂªÃ™â€šÃ˜Â²Ã™â€˜Ã™â€¦ Ã™Ë†Ã™â€žÃ˜Â§ Ã˜Â³Ã˜Â·Ã˜Â­Ã™Å Ã˜Â© Ã˜Â¹Ã™â€žÃ™â€° Ã™â€¦Ã˜Â³Ã˜ÂªÃ™Ë†Ã™â€° Ã˜Â§Ã™â€žÃ™â€¦Ã™â€ Ã˜Â­Ã˜Â©/Ã˜Â§Ã™â€žÃ™â€¦Ã™â€šÃ˜Â§Ã˜Â¹Ã˜Â¯/Ã˜Â§Ã™â€žÃ™â€žÃ™Ë†Ã˜Â­Ã˜Â©. Ã˜Â£Ã˜Â³Ã˜ÂªÃ™â€¦Ã˜Â± Ã™â€¦Ã˜Â¹Ã™â€žÃ™â€˜Ã™â€¦Ã˜Â§Ã™â€¹ Ã™Ë†Ã˜Â£Ã™â€ Ã˜Â§ Ã˜Â£Ã˜ÂªÃ˜Â¹Ã™â€žÃ™â€¦.",
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
        "truth_reconciled": truth_reconciled,
        "healthy": len(issues) == 0,
        "optional": False,
        "wal_written": False,
        "gl005_proven": gl005_lineage_proven(),
        "gl005_authority_source": "C1_CANONICAL_LINEAGE",
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
        "# Ã™ÂÃ˜Â±Ã˜Â¶ C5 Ã¢â‚¬â€ Ã™Æ’Ã˜Â§Ã™â€žÃ˜Â§Ã˜Â¨ Ã™Ë†Ã˜Â§Ã˜Â¨Ã™â€ Ã™â€¡",
        "",
        f"- Ã˜Â§Ã™â€žÃ™Ë†Ã™â€šÃ˜Âª: `{rec.get('ts')}`",
        f"- Ã˜Â³Ã™â€žÃ™Å Ã™â€¦: `{rec.get('healthy')}`",
        f"- Ã˜Â¹Ã™â€žÃ™â€ž: `{rec.get('issue_count')}`",
        f"- Ã˜Â¥Ã˜Â¬Ã˜Â¨Ã˜Â§Ã˜Â±: `{rec.get('compelled')}`",
        f"- `GL005_PROVEN`: `{rec.get('gl005_proven')}`",
        "",
        "Ã˜Â§Ã™â€žÃ˜Â®Ã˜Â¨Ã˜Â« Ã™Ë†Ã˜Â§Ã™â€žÃ˜Â®Ã˜Â¯Ã˜Â§Ã˜Â¹ Ã™Ë†Ã˜Â§Ã™â€žÃ˜ÂªÃ™â€šÃ˜Â²Ã™â€˜Ã™â€¦ Ã™Ë†Ã˜Â§Ã™â€žÃ˜Â³Ã˜Â·Ã˜Â­Ã™Å Ã˜Â© Ã˜ÂªÃ™ÂÃ˜Â¬Ã˜Â¨Ã˜Â± Ã˜Â§Ã™â€žÃ˜Â¥Ã˜ÂµÃ™â€žÃ˜Â§Ã˜Â­ Ã™ÂÃ™Ë†Ã˜Â±Ã˜Â§Ã™â€¹. Ã™â€žÃ™Å Ã˜Â³ Ã™â€¦Ã™â€žÃ˜Â§Ã˜Â­Ã˜Â¸Ã˜Â© Ã™â€žÃ˜Â§Ã˜Â­Ã™â€šÃ˜Â§Ã™â€¹.",
        "",
    ]
    if not rec.get("issues"):
        lines.append("_Ã™â€žÃ˜Â§ Ã˜Â¹Ã™â€žÃ˜Â© Ã˜Â­Ã™Å Ã˜Â©._")
        lines.append("")
    for item in rec.get("issues") or []:
        lines.append(f"- `{item.get('id')}` pathology={item.get('pathology')} law=`{item.get('law')}`")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    rec = enforce()
    print(json.dumps({"from": "C5", "healthy": rec["healthy"], "issues": rec["issue_count"], "compelled": rec["compelled"], "gl005_proven": rec["gl005_proven"], "gl005_authority_source": rec["gl005_authority_source"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
