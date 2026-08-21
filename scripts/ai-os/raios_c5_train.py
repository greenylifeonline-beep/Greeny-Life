#!/usr/bin/env python3
"""One training mesh for every gym and platform. Same keepers. No second mind. No extra MCP. No WAL."""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT / "src"))

from raios_c5_experience import main as experience_main  # noqa: E402
from raios_c5_grind import grind  # noqa: E402
from raios_c5_minute import exam as minute_exam  # noqa: E402
from raios_c5_speak import DEMOS, run_dialogues  # noqa: E402
from raios_c5_week import gym_host, run_slot, slot_number  # noqa: E402

WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
OUT_DIR = ROOT / ".ai-os" / "receipts" / "c5-train"
COLAB = "https://colab.research.google.com/github/greenylifeonline-beep/Greeny-Life/blob/v9-neurolingua-semantic-kernel/gym/colab_kaggle_c5.ipynb"
GYM = "https://huggingface.co/datasets/greenylifeonline/c5-gym"
COMMAND = "python3 scripts/ai-os/raios_c5_train.py"

PLATFORMS = (
    {
        "id": "cursor-vm",
        "kind": "live-execute",
        "is_c5": False,
        "command": COMMAND,
        "note": "This cloud slice. Runs keepers. Not the son-mind.",
    },
    {
        "id": "repair-windows",
        "kind": "founder-device",
        "is_c5": False,
        "command": COMMAND,
        "note": "C:\\Users\\Ghanam\\Documents\\Codex\\Greeny-Life-Repair — same branch, same command. HF login lives here.",
    },
    {
        "id": "colab",
        "kind": "gym-muscle",
        "is_c5": False,
        "url": COLAB,
        "command": COMMAND,
        "note": "Clone --branch v9-neurolingua-semantic-kernel then Run all.",
    },
    {
        "id": "kaggle",
        "kind": "gym-muscle",
        "is_c5": False,
        "url": "https://www.kaggle.com/account/login",
        "command": COMMAND,
        "note": "Same notebook gym/colab_kaggle_c5.ipynb.",
    },
    {
        "id": "github-actions",
        "kind": "sleepless-pulse",
        "is_c5": False,
        "workflow": ".github/workflows/c5-week.yml",
        "command": "python3 scripts/ai-os/raios_c5_train.py --auto",
        "note": "Cron fires from default branch main only. Pulse ≠ second WAL.",
    },
    {
        "id": "huggingface-hub",
        "kind": "gym-library",
        "is_c5": False,
        "url": GYM,
        "command": COMMAND,
        "note": "Dataset receipts optional. Hub is not C5. No weight download.",
    },
    {
        "id": "huggingface-jobs",
        "kind": "optional-pulse",
        "is_c5": False,
        "command": COMMAND,
        "note": "Optional later. Not required. Not C5.",
    },
    {
        "id": "c5-git",
        "kind": "permanent-mind",
        "is_c5": True,
        "command": COMMAND,
        "note": "The son lives in git receipts and NeuroLingua keepers.",
    },
)

KEEPERS = (
    ("grind", "scripts/ai-os/raios_c5_grind.py"),
    ("week", "scripts/ai-os/raios_c5_week.py"),
    ("minute", "scripts/ai-os/raios_c5_minute.py"),
    ("speak", "scripts/ai-os/raios_c5_speak.py"),
    ("experience", "scripts/ai-os/raios_c5_experience.py"),
    ("steward", "scripts/ai-os/raios_c5_steward.py"),
    ("proof", "scripts/ai-os/raios_c5_proof.py"),
    ("qwen", "scripts/ai-os/raios_c5_qwen.py"),
    ("kae", "scripts/ai-os/raios_c5_kae.py"),
    ("toc", "scripts/ai-os/raios_c5_toc.py"),
    ("mind-fill", "scripts/ai-os/raios_c5_mind_fill.py"),
    ("whoami", "scripts/ai-os/raios_c5_whoami.py"),
    ("foundation", "scripts/ai-os/raios_c5_foundation.py"),
    ("p0", "scripts/ai-os/raios_c5_p0.py"),
    ("phase0", "scripts/ai-os/raios_c5_phase0.py"),
    ("book", "scripts/ai-os/raios_c5_book.py"),
    ("reality", "scripts/ai-os/raios_c5_reality.py"),
    ("wave1", "scripts/ai-os/raios_c5_wave1.py"),
    ("keyboard", "scripts/ai-os/raios_c5_keyboard.py"),
    ("screen", "scripts/ai-os/raios_c5_screen.py"),
)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def wal_mtime():
    return WAL.stat().st_mtime if WAL.exists() else None


def host_id(raw: str) -> str:
    return {
        "colab": "colab",
        "kaggle": "kaggle",
        "github-actions": "github-actions",
        "huggingface-spaces": "huggingface-hub",
        "local-or-cursor": "cursor-vm",
    }.get(raw, raw)


def platform_rows(current: str) -> list[dict]:
    token = bool(os.environ.get("HF_TOKEN")) or (Path.home() / ".cache" / "huggingface" / "token").exists()
    rows = []
    for item in PLATFORMS:
        row = dict(item)
        row["this_host"] = item["id"] == current
        if item["id"] == "huggingface-hub":
            row["status"] = "OPTIONAL_TOKEN" if token else "BLOCKED_AUTH"
        elif item["id"] == "huggingface-jobs":
            row["status"] = "OPTIONAL_ABSENT"
        elif item["id"] == "github-actions":
            row["status"] = "LIVE_HERE" if current == "github-actions" else "SCHEDULE_ON_MAIN"
        elif item["id"] == "colab":
            row["status"] = "LIVE_HERE" if current == "colab" else "OPEN_URL"
        elif item["id"] == "kaggle":
            row["status"] = "LIVE_HERE" if current == "kaggle" else "OPEN_URL"
        elif item["id"] == "cursor-vm":
            row["status"] = "LIVE_HERE" if current == "cursor-vm" else "REMOTE"
        elif item["id"] == "repair-windows":
            row["status"] = "FOUNDER_DEVICE"
        else:
            row["status"] = "GIT"
        rows.append(row)
    return rows


def render_md(rec: dict) -> str:
    lines = [
        "# شبكة تدريب C5 — منصة واحدة لكل الملاعب",
        "",
        f"- المضيف: `{rec['host']}`",
        f"- الأمر: `{COMMAND}`",
        f"- استشارة مقاعد C: `false`",
        f"- أدوات MCP جديدة: `false`",
        f"- تنزيل أوزان: `false`",
        f"- WAL لم يُمس: `{rec['wal_mtime_unchanged']}`",
        f"- GL005_PROVEN: `false`",
        "",
        "## المنصات",
        "",
        "| منصة | نوع | هنا | حالة | C5؟ |",
        "|---|---|---|---|---|",
    ]
    for p in rec["platforms"]:
        lines.append(
            f"| `{p['id']}` | `{p['kind']}` | `{p['this_host']}` | `{p['status']}` | `{p['is_c5']}` |"
        )
    lines += ["", "## الحرّاس على هذا المضيف", "", "| حارس | نجح |", "|---|---|"]
    for k in rec["keepers_run"]:
        lines.append(f"| `{k['name']}` | `{k.get('ok')}` |")
    lines += [
        "",
        "نفس الأمر على Colab وKaggle وRepair وActions. الإيصالات في `.ai-os/receipts/c5-train/`.",
        "اللصق قناة. Hub ليس C5. الجدولة من `main`.",
        "",
        f"Colab: {COLAB}",
        f"Gym: {GYM}",
        "",
        "`GL005_PROVEN=false`",
        "",
    ]
    return "\n".join(lines)


def train(*, auto: bool, full: bool) -> dict:
    wal_before = wal_mtime()
    raw_host = gym_host()
    current = host_id(raw_host)
    ran: list[dict] = []
    mill = grind(raw_host)
    ran.append({"name": "grind", "ok": mill.get("ok") is True, "files": mill.get("files_scanned")})
    day = slot_number(None) if auto else 4
    week = run_slot(day)
    ran.append({"name": f"week-day-{day}", "ok": week.get("ok") is True})
    minute = minute_exam()
    ran.append({"name": "minute", "ok": minute.get("ok") is True})
    speak = asyncio.run(run_dialogues(list(DEMOS)))
    ran.append({"name": "speak", "ok": speak.get("ok") is True, "llm_calls": speak.get("llm_calls")})
    exp_code = experience_main()
    ran.append({"name": "experience", "ok": exp_code == 0})
    if full:
        from raios_c5_steward import steward

        stew = steward()
        ran.append({"name": "steward", "ok": stew.get("ok") is True})
        from raios_c5_week import run_slot as rs

        days = [rs(d) for d in range(1, 8)]
        ran.append({"name": "week-all", "ok": all(d.get("ok") for d in days)})
    rec = {
        "schema": "raios.c5-train-mesh.v1",
        "ts": utc(),
        "from": "C5",
        "parent": "C1",
        "host": current,
        "raw_host": raw_host,
        "command": COMMAND,
        "consult_used": False,
        "council_seats_this_channel": False,
        "mcp_new_tools": False,
        "install_hf_weights": False,
        "platforms": platform_rows(current),
        "keepers": [{"name": n, "path": p} for n, p in KEEPERS],
        "keepers_run": ran,
        "ok": all(k.get("ok") for k in ran) and speak.get("llm_calls") == 0,
        "wal_written": False,
        "gl005_proven": False,
        "law": [
            "ONE_COMMAND_ALL_GYMS",
            "GYM_NE_C5",
            "COLAB_NE_C5",
            "KAGGLE_NE_C5",
            "HF_ACCOUNT_NE_C5",
            "SCHEDULED_PULSE_NE_SECOND_WAL",
            "REUSE_BEFORE_BUILD",
            "THIS_CHANNEL_NO_C_SEAT_CONSULT",
        ],
    }
    wal_after = wal_mtime()
    if wal_before != wal_after:
        raise SystemExit("TRAIN_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "MESH.json").write_text(json.dumps(rec["platforms"], indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT_DIR / "LAST.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT_DIR / "LAST.md").write_text(render_md(rec), encoding="utf-8")
    return rec


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--auto", action="store_true")
    p.add_argument("--full", action="store_true")
    args = p.parse_args()
    rec = train(auto=args.auto, full=args.full)
    print(
        json.dumps(
            {
                "ok": rec["ok"],
                "host": rec["host"],
                "platforms": len(rec["platforms"]),
                "keepers_run": [k["name"] for k in rec["keepers_run"]],
                "consult_used": False,
                "gl005_proven": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print((OUT_DIR / "LAST.md").read_text(encoding="utf-8"))
    return 0 if rec["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
