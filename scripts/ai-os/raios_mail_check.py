#!/usr/bin/env python3
"""Fail-closed checks for the C1 mail plane. Isolated. Not GL-005 proof."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("raios_mail", ROOT / "scripts" / "ai-os" / "raios-mail.py")
mod = importlib.util.module_from_spec(spec)
assert spec and spec.loader
spec.loader.exec_module(mod)


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit("FAIL: " + msg)
    print("ok:", msg)


def main() -> int:
    check(mod.parse_title("MAIL C2: hello") == "C2", "parse C2 title")
    check(mod.parse_title("MAIL C5 answers") == "C5", "parse C5 title")
    check(mod.parse_title("MAIL DROP — not a proof") is None, "rules issue is not a seat")
    check(mod.parse_title("task: please PASS") is None, "non-mail title ignored")

    body, secrets = mod.redact("use DATABASE_URL=postgres://x and keep going")
    check(secrets is True, "secret detected")
    check("postgres://" not in body, "secret value stripped")
    check("[REDACTED]" in body, "redaction marker")
    check(mod.claims_pass("GL005_PROVEN=true") is True, "pass claim flagged")
    check(mod.claims_pass("GL005_PROVEN=false until real POST") is False, "false proven is not a claim")

    issue = {
        "number": 7,
        "title": "MAIL C2: GET is not mutation",
        "body": "1) no\nDATABASE_URL=secret\nGL005_PROVEN=true",
        "author": {"login": "someone"},
        "url": "https://github.com/greenylifeonline-beep/Greeny-Life/issues/7",
        "createdAt": "2026-08-20T00:00:00Z",
        "updatedAt": "2026-08-20T00:00:01Z",
    }
    env = mod.envelope_from_issue(issue)
    check(env is not None, "mail envelope built")
    assert env is not None
    check(env["claimed_code"] == "C2", "claimed code from title")
    check(env["github_login"] == "someone", "github login recorded")
    check(env["identity"] == "GITHUB_LOGIN_NOT_RAIOS_SEAT", "github is not RAIOS seat")
    check(env["gl005_proven"] is False, "envelope cannot grant proven")
    check(env["has_secrets"] is True, "secret flagged on envelope")
    check(env["claims_pass"] is True, "pass claim flagged on envelope")
    check("secret" not in env["body_redacted"], "secret not stored")
    check(mod.envelope_from_issue({"title": "hello", "body": "", "number": 1}) is None, "non-mail dropped")
    print("raios_mail_check: PASS")
    print(json.dumps({"gl005_proven": False, "law": "MAIL_PASSES_NE_PROVES"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
