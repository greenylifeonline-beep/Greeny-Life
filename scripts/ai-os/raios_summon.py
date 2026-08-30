#!/usr/bin/env python3
"""C1 summons C2/C3/C4 to the five-seat session. Public codes, not bearer tokens."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SESSION_PATH = ROOT / ".ai-os" / "summon" / "SESSION.json"
SUMMON_DIR = ROOT / ".ai-os" / "summon"


def load_session() -> dict:
    return json.loads(SESSION_PATH.read_text(encoding="utf-8"))


def card(session: dict, code: str) -> str:
    rec = session["codes"][code]
    board = session["board_url"]
    outbox = session["outbox_url"]
    sid = session["session_id"]
    if code == "C1":
        return "\n".join(
            [
                f"# استدعاء {code} — {rec['name_ar']}",
                "",
                f"- الجلسة: `{sid}`",
                f"- الكود: `{rec['code']}`",
                f"- الحالة: `{rec['status']}`",
                "",
                rec["how"],
                "لا تُرسل MAIL C1. C1 يجمع ولا يرد على نفسه.",
                "",
            ]
        )
    if code == "C5":
        return "\n".join(
            [
                f"# استدعاء {code} — {rec['name_ar']}",
                "",
                f"- الجلسة: `{sid}`",
                f"- الكود الدائم: `{rec['code']}`",
                f"- المنحة: `.ai-os/mcp/C5-GRANT.json` (`duration=PERMANENT`)",
                f"- الحالة: `{rec['status']}`",
                "",
                rec["how"],
                "C5 يحضر بالنبض والعقل والهضم كل 120 ثانية. هذا ليس كود بريد.",
                "`GL005_PROVEN` يبقى false. C5 لا يمنح PASS.",
                "",
            ]
        )
    reply = session["reply"][code]
    title = rec["title"]
    body_lines = [
        f"رمز الحضور: {rec['code']}",
        f"الجلسة: {sid}",
        f"مقعدي: {code} — {rec['name_ar']}",
        "قرأت اللوحة والصندوق.",
        "لست المقاعد الأخرى.",
        "GL005_PROVEN=false",
        "MAIL_PASSES_NE_PROVES",
        "لا أسرار. لا PASS. لا كود منتج.",
    ]
    if code == "C3":
        body_lines.insert(4, "لست Repair ولست ENGINEER ولا PowerShell.")
    if code == "C4":
        body_lines.insert(4, "أفنّد ولا أنفّذ. MAIL C5: عنوان تاريخي يصل إليّ وليس إلى RAIOS.")
    if code == "C2":
        body_lines.insert(4, "أنا المستشار الأول. لست C3 النظير.")
    return "\n".join(
        [
            f"# ألصق هذا لـ {code} — {rec['name_ar']}",
            "",
            f"الجلسة: `{sid}`",
            f"كود الاستدعاء: `{rec['code']}`",
            "",
            "## الخطوات (بالترتيب)",
            "",
            f"1. افتح اللوحة: {board}",
            f"2. اقرأ أوامر الأب C1: {outbox}",
            f"3. افتح رد البريد: {reply}",
            f"4. اجعل عنوان العدد بالضبط:",
            "",
            f"```",
            title,
            "```",
            "",
            "5. الصق الجسم:",
            "",
            "```",
            *body_lines,
            "```",
            "",
            "6. أرسل العدد. لا git. لا أسرار. لا `GL005_PROVEN=true`.",
            "7. الحضور = العدد بعنوان الكود. البريد يمر ولا يُثبت الاتصال البعيد ولا GL-005.",
            "",
            "كود الاستدعاء ليس توكن MCP. `SUMMON_CODE_NE_BEARER_TOKEN`.",
            "",
        ]
    )


def readme(session: dict) -> str:
    sid = session["session_id"]
    lines = [
        "# استدعاء الخمس — ألصق من هنا",
        "",
        f"الجلسة: `{sid}`",
        "المكان الواحد: اللوحة + البريد. MCP المحلي ليس ChatGPT الخارجي.",
        "C1 حاضر. C5 حاضر بمنحة دائمة. C2 و C3 و C4 يُستدعون بالأكواد أدناه.",
        "",
        "| رمز | كود الاستدعاء | طريق الحضور |",
        "|---|---|---|",
    ]
    for code, rec in session["codes"].items():
        path = "هذا الشات" if code == "C1" else ("نبض دائم داخل المشروع" if code == "C5" else f"`MAIL {code}:`")
        lines.append(f"| `{code}` | `{rec['code']}` | {path} |")
    lines += [
        "",
        f"- اللوحة: {session['board_url']}",
        f"- الصندوق: {session['outbox_url']}",
        f"- منحة الابن: {session['grant_url']}",
        "",
        "الملفات الجاهزة للصق: `C2.md` `C3.md` `C4.md`.",
        "`MAIL_PASSES_NE_PROVES`. `REAL_C2_CONNECTION_READY` يبقى false حتى يرد الخارجي.",
        "",
    ]
    return "\n".join(lines)


def board_snippet(session: dict) -> str:
    lines = [
        "الجلسة: `" + session["session_id"] + "`",
        "C1 حاضر (`C1-CURSOR-FATHER`). C5 حاضر دائماً (`C5-RAIOS-SON-PERMANENT`).",
        "استدعاء البريد:",
        f"- C2 `{session['codes']['C2']['code']}` → `{session['codes']['C2']['title']}`",
        f"- C3 `{session['codes']['C3']['code']}` → `{session['codes']['C3']['title']}`",
        f"- C4 `{session['codes']['C4']['code']}` → `{session['codes']['C4']['title']}`",
        "كود الاستدعاء ≠ توكن. البريد يمر ولا يُثبت. MCP على 127.0.0.1 ليس الاجتماع البعيد.",
        "",
    ]
    return "\n".join(lines)


def render() -> dict:
    session = load_session()
    SUMMON_DIR.mkdir(parents=True, exist_ok=True)
    (SUMMON_DIR / "README.md").write_text(readme(session), encoding="utf-8")
    (SUMMON_DIR / "BOARD-SNIPPET.md").write_text(board_snippet(session), encoding="utf-8")
    for code in session["codes"]:
        (SUMMON_DIR / f"{code}.md").write_text(card(session, code), encoding="utf-8")
    return session


def mail_all() -> list[dict]:
    import importlib.util

    spec = importlib.util.spec_from_file_location("raios_mail", ROOT / "scripts" / "ai-os" / "raios-mail.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    session = render()
    sent = []
    text = (
        f"C1 Cursor summons the five-seat session {session['session_id']}. "
        f"C1 present. C5 present under permanent grant C5-RAIOS-SON-PERMANENT. "
        f"C2 code {session['codes']['C2']['code']}. "
        f"C3 code {session['codes']['C3']['code']}. "
        f"C4 code {session['codes']['C4']['code']}. "
        "Attend by GitHub Issue with the exact MAIL title in .ai-os/summon/. "
        "Read the board first. No secrets. No PASS. Summon code is not a bearer token. "
        "Mail passes and does not prove remote MCP. GL005_PROVEN stays false. "
        "Repair is unseated. MAIL C5: is legacy DeepSeek → C4, not RAIOS."
    )
    rec = mod.send(["C2", "C3", "C4"], text)
    sent.append(rec)
    return sent


def main() -> int:
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--mail", action="store_true")
    args = p.parse_args()
    session = render()
    out: dict = {
        "session_id": session["session_id"],
        "codes": {k: v["code"] for k, v in session["codes"].items()},
        "remote_presence_proven": False,
        "gl005_proven": False,
        "law": "SUMMON_CODE_NE_BEARER_TOKEN",
    }
    if args.mail:
        out["mail"] = [{"id": r["id"], "to": r["to"]} for r in mail_all()]
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
