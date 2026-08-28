#!/usr/bin/env python3
"""C1 public mail plane. Outbox = C1 sends. GitHub Issues = C2/C5 send. Mail does not prove."""
from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from raios_seats import LEGACY_MAIL, MAIL_CODES, resolve_mail_title_code  # noqa: E402

MAIL = ROOT / ".ai-os" / "mail"
OUTBOX_JSONL = MAIL / "OUTBOX.jsonl"
INBOX_JSONL = MAIL / "INBOX.jsonl"
OUTBOX_MD = MAIL / "OUTBOX.md"
COLLECT_RECEIPT = MAIL / "COLLECT-RECEIPT.json"
BOARD_PY = ROOT / "scripts" / "ai-os" / "raios-board.py"

REPO = "greenylifeonline-beep/Greeny-Life"
BRANCH = "v9-neurolingua-semantic-kernel"
ISSUES_URL = f"https://github.com/{REPO}/issues"
OUTBOX_URL = f"https://github.com/{REPO}/blob/{BRANCH}/.ai-os/mail/OUTBOX.md"
NEW_C2 = f"https://github.com/{REPO}/issues/new?template=raios-mail-c2.md"
NEW_C3 = f"https://github.com/{REPO}/issues/new?template=raios-mail-c3.md"
NEW_C4 = f"https://github.com/{REPO}/issues/new?template=raios-mail-c4.md"
NEW_C5 = f"https://github.com/{REPO}/issues/new?template=raios-mail-c5.md"

TITLE_RE = re.compile(r"^MAIL\s+C([0-5])\b", re.I)
SECRET_RE = re.compile(
    r"DATABASE_URL\s*=\s*\S+|APP_SESSION_SECRET\s*=\s*\S+|gl_session\s*=\s*\S+|postgres(?:ql)?://\S+",
    re.I,
)
BEARER_TOKEN_RE = re.compile(r"(?:^|[^A-Za-z])Bearer [A-Za-z0-9\-._~+/]{16,}")
PASS_CLAIM_RE = re.compile(r"GL00[45]_PROVEN\s*=\s*true", re.I)
CODES = MAIL_CODES
REPLY_URLS = {"C2": NEW_C2, "C3": NEW_C3, "C4": NEW_C4}


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            rows.append(json.loads(raw))
    return rows


def append_jsonl(path: Path, rec: dict) -> None:
    MAIL.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(rec, ensure_ascii=False) + "\n")


def parse_title(title: str) -> str | None:
    match = TITLE_RE.match((title or "").strip())
    if not match:
        return None
    return resolve_mail_title_code("C" + match.group(1))


def redact(text: str) -> tuple[str, bool]:
    text = text or ""
    found = bool(SECRET_RE.search(text) or BEARER_TOKEN_RE.search(text))
    redacted = SECRET_RE.sub("[REDACTED]", text)
    redacted = BEARER_TOKEN_RE.sub(" Bearer [REDACTED]", redacted)
    return redacted, found


def claims_pass(text: str) -> bool:
    return bool(PASS_CLAIM_RE.search(text or ""))


def load_board():
    spec = importlib.util.spec_from_file_location("raios_board", BOARD_PY)
    if spec is None or spec.loader is None:
        raise SystemExit("BOARD_IMPORT_FAILED")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def git_head() -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True)
    return (r.stdout or "").strip()


def sync_board(*, last_collect: dict | None = None, last_send: dict | None = None) -> None:
    board = load_board()
    state = board.load_now()
    state["branch"] = BRANCH
    state["head"] = git_head()
    state["updated_at"] = utc()
    state["mission_status"] = "ONE_PLACE_MAP_ENCODED_REMOTE_UNPROVEN"
    state["mission"] = (
        "C0 abolished. C1 is Cursor (owner's hand). C2/C3 ChatGPT. C4 DeepSeek. C5 RAIOS. "
        "Repair is unseated. Local MCP meeting is not remote ChatGPT. "
        "MAIL_PASSES_NE_PROVES. GL005_PROVEN remains false."
    )
    state["schedule"] = {
        "now": "C5 RAIOS — ابن Cursor — يقيّم ويهضم ويتكلم. C2/C3/C4 عبر MCP أو MAIL. C1 يجمع.",
        "next": "Remote C2/C3/C4 connectivity remains unproven. Repair authenticated POST remains the only GL-005 mutation proof.",
        "forbidden": "C0 live seat, Repair as C3, MAIL C5 as RAIOS, Issue as proof, PASS from mail or C5 pulse, Team Relay hub, WAL dump, forged session",
    }
    state["required"] = {
        "C1": "Cursor — يد المالك وأب C5. بوابة MCP V1 + OUTBOX. يجمع. لا يمنح PASS.",
        "C2": "ChatGPT الأول. MCP أو MAIL C2. لا كود.",
        "C3": "ChatGPT النظير. MCP أو MAIL C3. ليس Repair.",
        "C4": "DeepSeek. MCP أو MAIL C4. MAIL C5 التاريخي يصل هنا.",
        "C5": "RAIOS الابن المساعد المخلص. يقيّم ويهضم ويتكلم. لا بريد GitHub. لا PASS.",
    }
    mail = {
        "dispatcher": "C1",
        "law": "MAIL_PASSES_NE_PROVES",
        "gl005_proven": False,
        "inbox": ISSUES_URL,
        "outbox": OUTBOX_URL,
        "new_c2": NEW_C2,
        "new_c3": NEW_C3,
        "new_c4": NEW_C4,
        "new_c5_legacy": NEW_C5,
        "identity": "GITHUB_LOGIN_NOT_RAIOS_SEAT",
        "c0_seat": "ABOLISHED",
        "repair_seat": "UNSEATED",
    }
    if last_collect is not None:
        mail["last_collect"] = last_collect
    elif isinstance(state.get("mail"), dict) and state["mail"].get("last_collect"):
        mail["last_collect"] = state["mail"]["last_collect"]
    if last_send is not None:
        mail["last_send"] = last_send
    elif isinstance(state.get("mail"), dict) and state["mail"].get("last_send"):
        mail["last_send"] = state["mail"]["last_send"]
    state["mail"] = mail
    board.save_now(state)


def render_outbox(rows: list[dict]) -> None:
    MAIL.mkdir(parents=True, exist_ok=True)
    lines = [
        "# صندوق الإرسال — C1",
        "",
        "C1 Cursor يرسل من هنا. C2 و C3 و C4 يردون بـ GitHub Issue.",
        "C0 ملغى. C5 RAIOS ليس مقعد بريد. `MAIL C5:` عنوان تاريخي → C4.",
        "`MAIL_PASSES_NE_PROVES`. هذا الملف ليس TASKS وليست LOCKS وليس `GL005_PROVEN`.",
        "",
        f"- القراءة: {OUTBOX_URL}",
        f"- الرد C2: {NEW_C2}",
        f"- الرد C3: {NEW_C3}",
        f"- الرد C4: {NEW_C4}",
        f"- الرد التاريخي C5→C4: {NEW_C5}",
        f"- الصندوق: {ISSUES_URL}",
        "",
        "لا git. لا اشتراك. لا أسرار. عنوان العدد يبدأ بـ `MAIL C2:` أو `MAIL C3:` أو `MAIL C4:`.",
        "",
        "## الرسائل",
        "",
    ]
    if not rows:
        lines.append("_لا رسائل صادرة بعد._")
        lines.append("")
    for rec in rows:
        to = ",".join(rec.get("to") or [])
        lines.append(f"### {rec.get('ts')} — to {to} — `{rec.get('id')}`")
        lines.append("")
        lines.append(str(rec.get("text") or "").strip())
        lines.append("")
        lines.append("`gl005_proven=false` `MAIL_PASSES_NE_PROVES`")
        lines.append("")
    OUTBOX_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def send(to: list[str], text: str) -> dict:
    dest = []
    for raw in to:
        code = raw.strip().upper()
        if code not in CODES:
            raise SystemExit(f"UNKNOWN_TO:{raw}")
        dest.append(code)
    text = (text or "").strip()
    if not text:
        raise SystemExit("EMPTY_TEXT")
    rec = {
        "schema": "raios.mail-envelope.v1",
        "id": str(uuid.uuid4()),
        "ts": utc(),
        "direction": "out",
        "from": "C1",
        "to": dest,
        "text": text,
        "identity": "C1_CURSOR_CLOUD",
        "gl005_proven": False,
        "law": "MAIL_PASSES_NE_PROVES",
        "reply": dict(REPLY_URLS),
    }
    append_jsonl(OUTBOX_JSONL, rec)
    render_outbox(load_jsonl(OUTBOX_JSONL))
    sync_board(last_send={"id": rec["id"], "ts": rec["ts"], "to": dest})
    return rec


def envelope_from_issue(issue: dict) -> dict | None:
    title = str(issue.get("title") or "")
    code = parse_title(title)
    if code is None:
        return None
    body = str(issue.get("body") or "")
    redacted, has_secrets = redact(body)
    author = issue.get("author") or {}
    login = author.get("login") if isinstance(author, dict) else None
    number = issue.get("number")
    return {
        "schema": "raios.mail-envelope.v1",
        "id": f"gh-issue-{number}-{issue.get('updatedAt') or issue.get('createdAt')}",
        "ts": utc(),
        "direction": "in",
        "source": "github-issue",
        "claimed_code": code,
        "legacy_title_mapped_from": "C5" if title.upper().startswith("MAIL C5") else None,
        "github_login": login,
        "identity": "GITHUB_LOGIN_NOT_RAIOS_SEAT",
        "issue": number,
        "url": issue.get("url"),
        "title": title,
        "body_redacted": redacted[:8000],
        "has_secrets": has_secrets,
        "claims_pass": claims_pass(title + "\n" + body),
        "gl005_proven": False,
        "law": "MAIL_PASSES_NE_PROVES",
        "issue_created_at": issue.get("createdAt"),
        "issue_updated_at": issue.get("updatedAt"),
    }


def list_issues(fixture: Path | None) -> list[dict]:
    if fixture is not None:
        return json.loads(fixture.read_text(encoding="utf-8"))
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
            "50",
            "--json",
            "number,title,author,body,url,createdAt,updatedAt",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    if r.returncode != 0:
        raise SystemExit((r.stderr or r.stdout or "GH_ISSUE_LIST_FAILED").strip())
    return json.loads(r.stdout or "[]")


def collect(fixture: Path | None = None) -> dict:
    existing = {row.get("id") for row in load_jsonl(INBOX_JSONL)}
    issues = list_issues(fixture)
    new_rows: list[dict] = []
    skipped = 0
    for issue in issues:
        env = envelope_from_issue(issue)
        if env is None:
            skipped += 1
            continue
        if env["id"] in existing:
            continue
        append_jsonl(INBOX_JSONL, env)
        new_rows.append(env)
    receipt = {
        "schema": "raios.mail-collect.v1",
        "collected_at": utc(),
        "open_issues_seen": len(issues),
        "non_mail_skipped": skipped,
        "new": len(new_rows),
        "inbox_total": len(load_jsonl(INBOX_JSONL)),
        "gl005_proven": False,
        "law": "MAIL_PASSES_NE_PROVES",
        "new_ids": [row["id"] for row in new_rows],
        "pass_claims": [row["id"] for row in new_rows if row.get("claims_pass")],
        "secret_flags": [row["id"] for row in new_rows if row.get("has_secrets")],
    }
    MAIL.mkdir(parents=True, exist_ok=True)
    COLLECT_RECEIPT.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    sync_board(
        last_collect={
            "at": receipt["collected_at"],
            "new": receipt["new"],
            "inbox_total": receipt["inbox_total"],
            "gl005_proven": False,
        }
    )
    return receipt


def show() -> dict:
    if OUTBOX_JSONL.exists() or OUTBOX_MD.exists():
        render_outbox(load_jsonl(OUTBOX_JSONL))
    return {
        "outbox": OUTBOX_URL,
        "inbox": ISSUES_URL,
        "new_c2": NEW_C2,
        "new_c3": NEW_C3,
        "new_c4": NEW_C4,
        "new_c5_legacy": NEW_C5,
        "out_count": len(load_jsonl(OUTBOX_JSONL)),
        "in_count": len(load_jsonl(INBOX_JSONL)),
        "gl005_proven": False,
        "outbox_md": OUTBOX_MD.read_text(encoding="utf-8") if OUTBOX_MD.exists() else "",
        "last_collect": json.loads(COLLECT_RECEIPT.read_text(encoding="utf-8")) if COLLECT_RECEIPT.exists() else None,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="c", required=True)
    s = sub.add_parser("send")
    s.add_argument("--to", required=True, help="C2,C3,C4")
    s.add_argument("--text", required=True)
    c = sub.add_parser("collect")
    c.add_argument("--fixture", type=Path)
    sub.add_parser("show")
    args = p.parse_args()
    if args.c == "send":
        rec = send([x for x in args.to.split(",") if x.strip()], args.text)
        print(json.dumps(rec, ensure_ascii=False, indent=2))
        return 0
    if args.c == "collect":
        rec = collect(args.fixture)
        print(json.dumps(rec, ensure_ascii=False, indent=2))
        return 0
    print(json.dumps(show(), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
