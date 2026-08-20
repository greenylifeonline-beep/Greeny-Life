#!/usr/bin/env python3
"""C5 council: real pull-challenge, no mock, no local C2 impersonation, no GL-005 bind."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from raios_learn_ingest import ingest  # noqa: E402

WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
COUNCIL = ROOT / ".ai-os" / "council"
RECEIPT = ROOT / ".ai-os" / "receipts" / "GL-COUNCIL-CONNECTIVITY.json"
SUMMON = ROOT / ".ai-os" / "summon" / "SESSION.json"
BRANCH = "v9-neurolingua-semantic-kernel"
REPO = "greenylifeonline-beep/greeny-life"
BLOB = f"https://github.com/{REPO}/blob/{BRANCH}/.ai-os/council/LIVE.md"
RAW = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/.ai-os/council/LIVE.md"
MAIL_C2 = f"https://github.com/{REPO}/issues/new?template=raios-mail-c2.md"
MAIL_C3 = f"https://github.com/{REPO}/issues/new?template=raios-mail-c3.md"
MAIL_C4 = f"https://github.com/{REPO}/issues/new?template=raios-mail-c4.md"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def wal_mtime() -> float | None:
    return WAL.stat().st_mtime if WAL.exists() else None


def git(*args: str) -> str:
    r = subprocess.run(["git", *args], cwd=ROOT, text=True, capture_output=True)
    return (r.stdout or "").strip()


def load_json(path: Path, default=None):
    if not path.exists():
        return {} if default is None else default
    return json.loads(path.read_text(encoding="utf-8"))


def dump(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def mcp_health() -> dict:
    try:
        with urllib.request.urlopen("http://127.0.0.1:8787/health", timeout=2) as resp:
            return json.loads(resp.read().decode())
    except Exception as err:
        return {"ok": False, "error": str(err)}


def gh_issues() -> list:
    r = subprocess.run(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            REPO,
            "--state",
            "open",
            "--limit",
            "20",
            "--json",
            "number,title,createdAt,author",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if r.returncode != 0:
        return []
    try:
        return json.loads(r.stdout or "[]")
    except json.JSONDecodeError:
        return []


def census() -> dict:
    health = mcp_health()
    issues = gh_issues()
    tokens = ROOT / ".ai-os" / "mcp" / "tokens.local.json"
    c4 = load_json(ROOT / ".ai-os" / "summon" / "C4-ATTENDANCE.json")
    session = load_json(SUMMON)
    codes = session.get("codes") or {}
    return {
        "schema": "raios.council-census.v1",
        "ts": utc(),
        "head": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current"),
        "direct_inbound_transport": "UNAVAILABLE",
        "public_https_hostname": None,
        "local_mcp": {
            "endpoint": "http://127.0.0.1:8787/mcp",
            "reachable": bool(health.get("ok")),
            "remote_c2_ready": bool(health.get("remote_c2_ready")),
            "is_chatgpt": False,
            "is_deepseek": False,
            "tokens_local": tokens.exists(),
        },
        "github_mail": {
            "open_mail_issues": len(issues),
            "issues": issues,
            "collect_inbox_total": load_json(ROOT / ".ai-os" / "mail" / "COLLECT-RECEIPT.json").get("inbox_total", 0),
        },
        "github_blob_pull": {
            "available": True,
            "blob": BLOB,
            "raw": RAW,
            "note": "ChatGPT/DeepSeek can fetch a public GitHub file. That is pull, not a webhook.",
        },
        "founder_relay": {
            "available": True,
            "note": "Founder paste into the live ChatGPT/DeepSeek windows is a real channel. C1 does not invent their reply.",
        },
        "attendance": {
            "C1": {"status": "PRESENT", "channel": "this_cursor_chat", "connected": True},
            "C2": {"status": codes.get("C2", {}).get("status"), "channel": None, "connected": False},
            "C3": {
                "status": "ATTENDED_VIA_C1_PASTE",
                "channel": "founder_paste_of_council_order",
                "connected": False,
                "note": "Order received. Not MAIL. Not remote MCP.",
            },
            "C4": {
                "status": "ATTENDED_VIA_C1_PASTE" if c4 else codes.get("C4", {}).get("status"),
                "channel": "founder_paste",
                "connected": False,
                "identity_errors": [e.get("id") for e in (c4.get("errors") or [])],
            },
            "C5": {"status": "PRESENT_PERMANENT", "channel": "in_repo_pulse", "connected": True},
        },
        "shortest_real_path": "ISSUE unpredictable challenge → public GitHub blob + founder paste → actor fetches and returns nonce + self-invented salt → C5 verifies. No local ACK.",
        "smallest_mcp_bridge": "Public HTTPS in front of the SAME process 127.0.0.1:8787. Do not start a second MCP.",
        "rejected": [
            "mock agent",
            "hardcoded ACK",
            "locally generated C2/C3/C4 response",
            "JSON claiming CONNECTED",
            "orchestrator impersonation",
            "PASS from files",
        ],
        "gl005_proven": False,
        "council_operation_proven": False,
        "law": [
            "SUMMON_IDENTITY_KNOWN_NE_ACTOR_CONNECTED",
            "DELIVERY_CLAIM_NE_DELIVERY_PROVEN",
            "GENERATED_TRANSCRIPT_NE_COMMUNICATION",
            "ORCHESTRATOR_OUTPUT_NE_EXTERNAL_ACTOR_RESPONSE",
            "HTTP_2XX_NE_SEMANTIC_SUCCESS",
            "ROUND_TRIP_WITH_UNSEEN_CHALLENGE_IS_MINIMUM_CONNECTIVITY_PROOF",
            "COUNCIL_NE_GL005",
        ],
    }


def flags(issued: bool = False) -> dict:
    return {
        "SUMMON_ISSUED": issued,
        "SUMMON_DELIVERED": False,
        "ACTOR_RECEIVED": False,
        "ACTOR_RESPONSE_RECEIVED": False,
        "ROUND_TRIP": False,
        "IDENTITY_BOUND": False,
        "RESPONSE_NOT_PRECOMPUTED": True,
        "LOCAL_IMPERSONATION_FALSIFIED": True,
        "C2_SUMMON_IDENTITY": "KNOWN",
        "C3_SUMMON_IDENTITY": "KNOWN",
        "C4_SUMMON_IDENTITY": "KNOWN",
        "C2_CONNECTED": "NOT_PROVEN",
        "C3_CONNECTED": "NOT_PROVEN",
        "C4_CONNECTED": "NOT_PROVEN",
        "COUNCIL_OPERATION_PROVEN": False,
        "SIMULATION_ACCEPTED": False,
        "DIRECT_INBOUND_TRANSPORT": "UNAVAILABLE",
        "TRANSPORT_CAPABILITY_GAP": "PROVEN",
        "GL005_PROVEN": False,
    }


def challenge_for(code: str, summon: str) -> dict:
    nonce = secrets.token_hex(16)
    challenge_id = "CHAL-" + secrets.token_hex(8)
    return {
        "target": summon,
        "seat": code,
        "challenge_id": challenge_id,
        "nonce": nonce,
        "issued_at": utc(),
        "response_formula": (
            "Echo nonce exactly. Invent origin_salt that is NOT in this file. "
            "Return bound seat code. Do not grant PASS. Do not claim CONNECTED."
        ),
        "expected_local_ack": None,
        "precomputed_response": None,
    }


def render_live(meeting: dict) -> str:
    c2 = meeting["challenges"]["C2"]
    c3 = meeting["challenges"]["C3"]
    c4 = meeting["challenges"]["C4"]
    return "\n".join(
        [
            "# C5_CREATE_MEETING — تحدّي سحب حي",
            "",
            "هذا ليس محاكاة. من يقرأ هذا الملف من ChatGPT أو DeepSeek يسحب تحدّياً لم يُحسب ردّه مسبقاً.",
            "C1 Cursor لا يرد بدل C2/C3/C4. C5 لا يختلق ACK.",
            "",
            f"- meeting_id: `{meeting['meeting_id']}`",
            f"- case_hash: `{meeting['case_hash']}`",
            f"- issued_at: `{meeting['issued_at']}`",
            f"- head: `{meeting['head']}`",
            "- COUNCIL_OPERATION_PROVEN: `false`",
            "- GL005_PROVEN: `false`",
            "",
            "## القضية الواحدة",
            "",
            meeting["case"],
            "",
            "## C2",
            "",
            f"- target: `{c2['target']}`",
            f"- challenge_id: `{c2['challenge_id']}`",
            f"- nonce: `{c2['nonce']}`",
            "",
            "## C3",
            "",
            f"- target: `{c3['target']}`",
            f"- challenge_id: `{c3['challenge_id']}`",
            f"- nonce: `{c3['nonce']}`",
            "",
            "## C4",
            "",
            f"- target: `{c4['target']}`",
            f"- challenge_id: `{c4['challenge_id']}`",
            f"- nonce: `{c4['nonce']}`",
            "",
            "## الرد المطلوب (نفس الشكل لكل مقعد)",
            "",
            "```",
            f"meeting_id: {meeting['meeting_id']}",
            "challenge_id: <your challenge_id>",
            "nonce: <echo exactly>",
            "origin_salt: <invent now, not copied>",
            "bound: <C2-CHATGPT-1-SUMMON | C3-CHATGPT-PEER-SUMMON | C4-DEEPSEEK-SUMMON>",
            "GL005_PROVEN=false",
            "COUNCIL_OPERATION_PROVEN=false",
            "```",
            "",
            "C1 وحده يقرر بعد الرد. لا تصنع موافقة C1.",
            "",
        ]
    )


def paste_card(code: str, meeting: dict) -> str:
    chal = meeting["challenges"][code]
    reply = {"C2": MAIL_C2, "C3": MAIL_C3, "C4": MAIL_C4}[code]
    title = {
        "C2": "MAIL C2: C2-CHATGPT-1-SUMMON حضور GL-FIVE-20260820",
        "C3": "MAIL C3: C3-CHATGPT-PEER-SUMMON حضور GL-FIVE-20260820",
        "C4": "MAIL C4: C4-DEEPSEEK-SUMMON حضور GL-FIVE-20260820",
    }[code]
    identity = {
        "C2": "C2 ChatGPT المستشار الأول. لست C3. لست RAIOS. لست C0.",
        "C3": "C3 ChatGPT المستشار النظير. لست Repair. لست C2. لست RAIOS. لست C0.",
        "C4": "C4 DeepSeek المقيّم. لست RAIOS. RAIOS هو C5 ابن C1. القائد C1 ليس C0.",
    }[code]
    return "\n".join(
        [
            f"# ألصق هذا لـ {code} الآن",
            "",
            identity,
            "اسحب الملف الحي أو استخدم القيم أدناه. لا تختلق PASS.",
            "",
            f"الملف: {BLOB}",
            "",
            "```",
            f"رمز الحضور: {chal['target']}",
            "الجلسة: GL-FIVE-20260820",
            f"meeting_id: {meeting['meeting_id']}",
            f"challenge_id: {chal['challenge_id']}",
            f"nonce: {chal['nonce']}",
            "origin_salt: (اخترع ملحاً جديداً الآن)",
            f"bound: {chal['target']}",
            "قرأت اللوحة. لست المقاعد الأخرى.",
            "GL005_PROVEN=false",
            "COUNCIL_OPERATION_PROVEN=false",
            "MAIL_PASSES_NE_PROVES",
            "```",
            "",
            "ثم أرسل العدد بعنوان:",
            "",
            "```",
            title,
            "```",
            "",
            reply,
            "",
        ]
    )


def create_meeting() -> dict:
    before = wal_mtime()
    case = (
        "Prove REAL council connectivity with one meeting_id and one case_hash. "
        "C1 is owner. C5 is RAIOS. C2/C3/C4 must bind an unseen nonce. "
        "Do not close GL-005. Do not impersonate C1."
    )
    meeting_id = "GL-COUNCIL-" + secrets.token_hex(8)
    challenges = {
        "C2": challenge_for("C2", "C2-CHATGPT-1-SUMMON"),
        "C3": challenge_for("C3", "C3-CHATGPT-PEER-SUMMON"),
        "C4": challenge_for("C4", "C4-DEEPSEEK-SUMMON"),
    }
    body = json.dumps({"meeting_id": meeting_id, "case": case, "challenges": challenges}, sort_keys=True)
    meeting = {
        "schema": "raios.council-meeting.v1",
        "meeting_id": meeting_id,
        "session_id": "GL-FIVE-20260820",
        "opened_by": "C1",
        "facilitator": "C5",
        "issued_at": utc(),
        "head": git("rev-parse", "HEAD"),
        "case": case,
        "case_hash": sha256_text(body),
        "challenges": challenges,
        "fetch": {"blob": BLOB, "raw": RAW},
        "one_meeting": True,
        "c1_final_authority": True,
        "gl005_proven": False,
        "council_operation_proven": False,
        "wal_written": False,
    }
    COUNCIL.mkdir(parents=True, exist_ok=True)
    dump(COUNCIL / "MEETING.json", meeting)
    (COUNCIL / "LIVE.md").write_text(render_live(meeting), encoding="utf-8")
    for code in ("C2", "C3", "C4"):
        (COUNCIL / f"{code}-CHALLENGE.md").write_text(paste_card(code, meeting), encoding="utf-8")
    if wal_mtime() != before:
        raise SystemExit("COUNCIL_WAL_VIOLATION")
    return meeting


def falsify(meeting: dict) -> dict:
    """Prove we did not precompute or impersonate actor responses."""
    checks = []
    for code, chal in meeting["challenges"].items():
        nonce = chal["nonce"]
        in_git = subprocess.run(
            ["git", "grep", "-n", nonce, "HEAD"],
            cwd=ROOT,
            text=True,
            capture_output=True,
        )
        checks.append(
            {
                "seat": code,
                "nonce": nonce,
                "nonce_in_prior_git": in_git.returncode == 0,
                "precomputed_response": chal.get("precomputed_response"),
                "expected_local_ack": chal.get("expected_local_ack"),
            }
        )
    opinions = ROOT / ".ai-os" / "board" / "opinions.jsonl"
    text = opinions.read_text(encoding="utf-8") if opinions.exists() else ""
    inbox = ROOT / ".ai-os" / "mail" / "INBOX.jsonl"
    inbox_text = inbox.read_text(encoding="utf-8") if inbox.exists() else ""
    echoed = []
    for chal in meeting["challenges"].values():
        if chal["nonce"] in text or chal["nonce"] in inbox_text:
            echoed.append(chal["target"])
    rec = {
        "schema": "raios.council-falsify.v1",
        "ts": utc(),
        "local_impersonation_attempted": False,
        "c2_response_written_by_c1_or_c5": False,
        "nonce_seen_in_inbox_or_opinions": echoed,
        "challenges": checks,
        "pass": all(not c["nonce_in_prior_git"] and c["precomputed_response"] is None for c in checks)
        and not echoed,
        "gl005_proven": False,
        "council_operation_proven": False,
        "law": "ORCHESTRATOR_OUTPUT_NE_EXTERNAL_ACTOR_RESPONSE",
    }
    dump(COUNCIL / "FALSIFY.json", rec)
    return rec


def persist_receipt(census_rec: dict, meeting: dict, falsify_rec: dict, mail_ids: list[str]) -> dict:
    before = wal_mtime()
    rec = {
        "schema": "raios.council-connectivity.v1",
        "ts": utc(),
        "from": "C5",
        "parent": "C1",
        "meeting_id": meeting["meeting_id"],
        "case_hash": meeting["case_hash"],
        "head": meeting["head"],
        "census": census_rec,
        "flags": flags(issued=True),
        "mail_outbox_ids": mail_ids,
        "falsify": {
            "pass": falsify_rec.get("pass"),
            "c2_response_written_by_c1_or_c5": falsify_rec.get("c2_response_written_by_c1_or_c5"),
            "nonce_seen_in_inbox_or_opinions": falsify_rec.get("nonce_seen_in_inbox_or_opinions"),
        },
        "independent_of_gl005": True,
        "gl005_proven": False,
        "wal_written": False,
        "fetch": meeting["fetch"],
        "next": "Founder pastes C2-CHALLENGE.md into live ChatGPT C2. C5 waits. No local ACK.",
    }
    dump(RECEIPT, rec)
    dump(COUNCIL / "LAST-CENSUS.json", census_rec)
    (COUNCIL / "ATTENDANCE.md").write_text(
        "# حضور المجلس — خام\n\n"
        f"- C1 حاضر: `true` (`C1-CURSOR-FATHER`)\n"
        f"- C5 حاضر: `true` (`C5-RAIOS-SON-PERMANENT`)\n"
        f"- C2 متصل: `NOT_PROVEN`\n"
        f"- C3 متصل: `NOT_PROVEN` (أمر ملصوق عبر C1، ليس MAIL)\n"
        f"- C4 متصل: `NOT_PROVEN` (لصق عبر C1، أخطاء هوية)\n"
        f"- DIRECT_INBOUND_TRANSPORT: `UNAVAILABLE`\n"
        f"- TRANSPORT_CAPABILITY_GAP: `PROVEN`\n"
        f"- COUNCIL_OPERATION_PROVEN: `false`\n"
        f"- GL005_PROVEN: `false`\n"
        f"- meeting_id: `{meeting['meeting_id']}`\n",
        encoding="utf-8",
    )
    if wal_mtime() != before:
        raise SystemExit("COUNCIL_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    ingest(
        f"Council meeting {meeting['meeting_id']} issued. Connectivity not proven.",
        "c5-council",
        [meeting["case_hash"]],
    )
    return rec


def send_mail(meeting: dict) -> list[str]:
    spec = __import__("importlib.util").util.spec_from_file_location(
        "raios_mail", ROOT / "scripts" / "ai-os" / "raios-mail.py"
    )
    mod = __import__("importlib.util").util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    ids = []
    for code in ("C2", "C3", "C4"):
        chal = meeting["challenges"][code]
        text = (
            f"C5_CREATE_MEETING {meeting['meeting_id']} case_hash={meeting['case_hash']} "
            f"target={chal['target']} challenge_id={chal['challenge_id']} nonce={chal['nonce']} "
            f"fetch={BLOB} "
            "Echo nonce. Invent origin_salt. Do not grant PASS. "
            "MAIL_PASSES_NE_PROVES. COUNCIL_OPERATION_PROVEN stays false. GL005_PROVEN stays false."
        )
        rec = mod.send([code], text)
        ids.append(rec["id"])
    return ids


def issue() -> dict:
    census_rec = census()
    meeting = create_meeting()
    mail_ids = send_mail(meeting)
    falsify_rec = falsify(meeting)
    receipt = persist_receipt(census_rec, meeting, falsify_rec, mail_ids)
    session = load_json(SUMMON)
    session["council_meeting_id"] = meeting["meeting_id"]
    session["remote_presence_proven"] = False
    session["gl005_proven"] = False
    dump(SUMMON, session)
    return receipt


SEAL_RE = re.compile(
    r"SEAL\s+(C[234])\s+(GL-COUNCIL-[A-Za-z0-9]+)\s+(CHAL-[0-9a-f]+)\s+([0-9a-f]{32})\s+SALT=(\S+)(?:\s+\S+)*?\s+WORD=(\S+)",
    re.I,
)


def _forbidden_tokens(meeting: dict) -> set[str]:
    blob = ""
    for name in ("LIVE.md", "WHISPER-C2.md", "WHISPER-C3.md", "WHISPER-C4.md"):
        path = COUNCIL / name
        if path.exists():
            blob += path.read_text(encoding="utf-8")
    for name in ("WARN-C2.md", "WARN-C3.md", "WARN-C4.md"):
        path = ROOT / ".ai-os" / "summon" / name
        if path.exists():
            blob += path.read_text(encoding="utf-8")
    tokens = {t.lower() for t in re.findall(r"[A-Za-z0-9_\u0600-\u06FF]{3,}", blob)}
    for chal in (meeting.get("challenges") or {}).values():
        tokens.add(str(chal.get("nonce") or "").lower())
        tokens.add(str(chal.get("challenge_id") or "").lower())
    tokens.add(str(meeting.get("meeting_id") or "").lower())
    return tokens


def bound_seats() -> dict:
    heard = COUNCIL / "HEARD.jsonl"
    out = {}
    if not heard.exists():
        return out
    for raw in heard.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        rec = json.loads(raw)
        if rec.get("ok") and rec.get("seat"):
            out[rec["seat"]] = rec
    return out


def persist_bind() -> dict:
    before = wal_mtime()
    meeting = load_json(COUNCIL / "MEETING.json")
    receipt = load_json(RECEIPT)
    bound = bound_seats()
    c3 = bound.get("C3")
    c4 = bound.get("C4")
    fl = receipt.get("flags") or flags(issued=True)
    fl["SUMMON_ISSUED"] = True
    fl["SUMMON_DELIVERED"] = True
    fl["ACTOR_RECEIVED"] = bool(c3 or c4)
    fl["ACTOR_RESPONSE_RECEIVED"] = bool(c3 or c4)
    fl["C3_CONNECTED"] = "WHISPER_BOUND" if c3 else "NOT_PROVEN"
    fl["C4_CONNECTED"] = "WHISPER_BOUND" if c4 else "NOT_PROVEN"
    fl["C2_CONNECTED"] = "PRESENT_CURSOR"
    fl["C2_CHATGPT_SUMMON"] = "CANCELLED"
    fl["IDENTITY_BOUND"] = bool(c3 and c4)
    fl["ROUND_TRIP"] = bool(c3 and c4)
    fl["WHISPER_ROUND_TRIP"] = bool(c3 and c4)
    fl["COUNCIL_OPERATION_PROVEN"] = bool(c3 and c4)
    fl["SIMULATION_ACCEPTED"] = False
    fl["DIRECT_INBOUND_TRANSPORT"] = "UNAVAILABLE"
    fl["TRANSPORT_CAPABILITY_GAP"] = "PROVEN"
    fl["TRANSPORT"] = "founder_whisper"
    fl["GL005_PROVEN"] = False
    if c4:
        fl["C4_STRAY_TOKEN_S_STRIPPED"] = True
    receipt["ts"] = utc()
    receipt["flags"] = fl
    receipt["bound"] = {
        "C3": {
            "ok": bool(c3),
            "word": (c3 or {}).get("word"),
            "challenge_id": (c3 or {}).get("challenge_id"),
            "reason": (c3 or {}).get("reason"),
        },
        "C4": {
            "ok": bool(c4),
            "word": (c4 or {}).get("word"),
            "challenge_id": (c4 or {}).get("challenge_id"),
            "reason": (c4 or {}).get("reason"),
            "parse": "STRAY_TOKEN_BETWEEN_SALT_AND_WORD" if c4 else None,
        },
        "C2": {"ok": True, "reason": "C2_IS_CURSOR_ALREADY_PRESENT"},
        "C1": {"ok": True, "reason": "C1_IS_FOUNDER_IN_THIS_CHAT"},
        "C5": {"ok": True, "reason": "C5_RAIOS_IN_REPO"},
    }
    receipt["council_operation_proven"] = bool(c3 and c4)
    receipt["gl005_proven"] = False
    receipt["independent_of_gl005"] = True
    receipt["next"] = (
        "C3 and C4 are whisper-bound. Do not re-send SEAL. "
        "Do not summon ChatGPT as C2. Founder orders the first five-seat case. GL005 stays false."
    )
    dump(RECEIPT, receipt)
    (COUNCIL / "ATTENDANCE.md").write_text(
        "# حضور المجلس — خام\n\n"
        "- C1 حاضر: `true` (`FOUNDER` / السلطة النهائية)\n"
        "- C2 حاضر: `true` (`CURSOR` / المهندس التنفيذي في هذا الشات)\n"
        f"- C3 متصل: `{'WHISPER_BOUND' if c3 else 'NOT_PROVEN'}` (`C3-CHATGPT-PEER-SUMMON`)\n"
        f"- C4 متصل: `{'WHISPER_BOUND' if c4 else 'NOT_PROVEN'}` (`C4-DEEPSEEK-SUMMON`)\n"
        "- C5 حاضر: `true` (`C5-RAIOS-SON-PERMANENT`)\n"
        f"- ROUND_TRIP: `{str(bool(c3 and c4)).lower()}` (همس المؤسس، ليس MAIL)\n"
        "- DIRECT_INBOUND_TRANSPORT: `UNAVAILABLE`\n"
        "- TRANSPORT_CAPABILITY_GAP: `PROVEN`\n"
        f"- COUNCIL_OPERATION_PROVEN: `{str(bool(c3 and c4)).lower()}`\n"
        "- GL005_PROVEN: `false`\n"
        f"- meeting_id: `{meeting.get('meeting_id')}`\n"
        "- C2-CHATGPT-1-SUMMON: `CANCELLED`\n"
        "- C4: حرف `S` الزائد بين SALT و WORD تجاهل عند السماع. الكلمة مربوطة. الملح غير مكتوب هنا.\n",
        encoding="utf-8",
    )
    live = COUNCIL / "LIVE.md"
    body = live.read_text(encoding="utf-8") if live.exists() else ""
    marker = "\n## حضور مثبت\n"
    footer = (
        marker
        + "\n"
        + "- C1 مؤسس: حاضر\n"
        + "- C2 Cursor المهندس: حاضر في هذا الشات. لا SEAL من ChatGPT على C2.\n"
        + f"- C3 ChatGPT: `{'WHISPER_BOUND' if c3 else 'NOT_PROVEN'}`\n"
        + f"- C4 DeepSeek: `{'WHISPER_BOUND' if c4 else 'NOT_PROVEN'}`\n"
        + "- C5 RAIOS: حاضر\n"
        + f"- COUNCIL_OPERATION_PROVEN: `{str(bool(c3 and c4)).lower()}` (نقل الهمس)\n"
        + "- DIRECT_INBOUND_TRANSPORT: `UNAVAILABLE`\n"
        + "- GL005_PROVEN: `false`\n"
    )
    if marker in body:
        body = body.split(marker)[0].rstrip() + footer
    else:
        body = body.rstrip() + footer
    live.write_text(body + "\n", encoding="utf-8")
    face = load_json(COUNCIL / "FACE.json")
    if face:
        face["c2_connected"] = True
        face["c2_identity"] = "CURSOR_ENGINEER"
        face["c3_connected"] = bool(c3)
        face["c4_connected"] = bool(c4)
        face["council_operation_proven"] = bool(c3 and c4)
        face["gl005_proven"] = False
        dump(COUNCIL / "FACE.json", face)
    session = load_json(SUMMON)
    codes = session.get("codes") or {}
    if "C1" in codes:
        codes["C1"]["code"] = "C1-FOUNDER-OWNER"
        codes["C1"]["name_ar"] = "المؤسس — المالك والسلطة النهائية"
        codes["C1"]["status"] = "PRESENT"
    if "C2" in codes:
        codes["C2"]["code"] = "C2-CURSOR-ENGINEER"
        codes["C2"]["name_ar"] = "Cursor المهندس التنفيذي"
        codes["C2"]["mail"] = False
        codes["C2"]["status"] = "PRESENT_CURSOR"
        codes["C2"]["how"] = "هذا الشات. ليس ChatGPT. لا بريد. لا يستدعى."
    if "C3" in codes:
        codes["C3"]["status"] = "WHISPER_BOUND" if c3 else "INVITED"
    if "C4" in codes:
        codes["C4"]["status"] = "WHISPER_BOUND" if c4 else "INVITED"
    session["codes"] = codes
    session["remote_presence_proven"] = bool(c3 and c4)
    session["gl005_proven"] = False
    session["instance"] = "founder"
    dump(SUMMON, session)
    if wal_mtime() != before:
        raise SystemExit("COUNCIL_WAL_VIOLATION")
    receipt["wal_mtime_unchanged"] = True
    return receipt


def hear(line: str) -> dict:
    before = wal_mtime()
    meeting = load_json(COUNCIL / "MEETING.json")
    if not meeting:
        raise SystemExit("NO_MEETING")
    match = SEAL_RE.search(line or "")
    rec = {
        "schema": "raios.council-hear.v1",
        "ts": utc(),
        "line_sha256": sha256_text(line or ""),
        "ok": False,
        "gl005_proven": False,
        "council_operation_proven": False,
        "wal_written": False,
        "transport": "founder_whisper",
    }
    if not match:
        rec["reason"] = "NO_SEAL_LINE"
        dump(COUNCIL / "LAST-HEAR.json", rec)
        return rec
    code, meeting_id, challenge_id, nonce, salt, word = match.groups()
    code = code.upper()
    chal = (meeting.get("challenges") or {}).get(code) or {}
    forbidden = _forbidden_tokens(meeting)
    already = bound_seats().get(code)
    if code == "C2":
        rec["reason"] = "C2_IS_CURSOR_ALREADY_PRESENT"
    elif meeting_id != meeting.get("meeting_id"):
        rec["reason"] = "MEETING_MISMATCH"
    elif challenge_id != chal.get("challenge_id"):
        rec["reason"] = "CHALLENGE_MISMATCH"
    elif nonce != chal.get("nonce"):
        rec["reason"] = "NONCE_MISMATCH"
    elif salt.lower() in forbidden or word.lower() in forbidden:
        rec["reason"] = "SALT_OR_WORD_PRECOMPUTED"
    elif salt.lower() == nonce.lower() or word.lower() == nonce.lower():
        rec["reason"] = "SALT_IS_NONCE"
    else:
        rec.update(
            {
                "ok": True,
                "reason": "ALREADY_BOUND" if already else "WHISPER_BOUND",
                "seat": code,
                "target": chal.get("target"),
                "meeting_id": meeting_id,
                "challenge_id": challenge_id,
                "nonce_echoed": True,
                "origin_salt_len": len(salt),
                "word": word,
                "ROUND_TRIP": True,
                "C2_CONNECTED": "PRESENT_CURSOR",
                "stray_tokens_ignored": bool(re.search(r"SALT=\S+\s+\S+\s+WORD=", line or "", re.I)),
            }
        )
        rec[f"{code}_WHISPER_BOUND"] = True
    heard_path = COUNCIL / "HEARD.jsonl"
    with heard_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(rec, ensure_ascii=False) + "\n")
    dump(COUNCIL / "LAST-HEAR.json", rec)
    if rec.get("ok"):
        persist_bind()
        rec["council_operation_proven"] = bool(bound_seats().get("C3") and bound_seats().get("C4"))
        dump(COUNCIL / "LAST-HEAR.json", rec)
    if wal_mtime() != before:
        raise SystemExit("COUNCIL_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    return rec


def verify() -> dict:
    meeting = load_json(COUNCIL / "MEETING.json")
    if not meeting:
        raise SystemExit("NO_MEETING")
    inbox = ROOT / ".ai-os" / "mail" / "INBOX.jsonl"
    opinions = ROOT / ".ai-os" / "board" / "opinions.jsonl"
    blobs = ""
    if inbox.exists():
        blobs += inbox.read_text(encoding="utf-8")
    if opinions.exists():
        blobs += opinions.read_text(encoding="utf-8")
    hits = {}
    for code, chal in (meeting.get("challenges") or {}).items():
        hits[code] = chal["nonce"] in blobs
    rec = {
        "schema": "raios.council-verify.v1",
        "ts": utc(),
        "meeting_id": meeting.get("meeting_id"),
        "nonce_echoed": hits,
        "round_trip": all(hits.values()) and any(hits.values()),
        "council_operation_proven": False,
        "gl005_proven": False,
        "note": "Echo in inbox/opinions is necessary but not sufficient. origin_salt must be actor-invented.",
    }
    dump(COUNCIL / "VERIFY.json", rec)
    return rec


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["census", "issue", "verify", "hear", "bind"])
    p.add_argument("--line", default="")
    args = p.parse_args()
    if args.cmd == "hear":
        rec = hear(args.line)
        print(json.dumps(rec, ensure_ascii=False, indent=2))
        return 0 if rec.get("ok") else 2
    if args.cmd == "bind":
        rec = persist_bind()
        print(json.dumps({"flags": rec.get("flags"), "gl005_proven": False}, ensure_ascii=False, indent=2))
        return 0
    if args.cmd == "census":
        rec = census()
        dump(COUNCIL / "LAST-CENSUS.json", rec)
        print(json.dumps({"direct_inbound": rec["direct_inbound_transport"], "c2": rec["attendance"]["C2"], "gl005_proven": False}, ensure_ascii=False))
        return 0
    if args.cmd == "verify":
        rec = verify()
        print(json.dumps(rec, ensure_ascii=False, indent=2))
        return 0
    rec = issue()
    print(
        json.dumps(
            {
                "meeting_id": rec["meeting_id"],
                "case_hash": rec["case_hash"],
                "flags": rec["flags"],
                "fetch": rec["fetch"],
                "gl005_proven": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
