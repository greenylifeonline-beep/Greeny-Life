#!/usr/bin/env python3
"""C5 professional customer language. NeuroLingua keepers. No LLM. No WAL. No C-seat consult."""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from raios.neuro_lingua.customer import COMPANIES  # noqa: E402
from raios.neuro_lingua.kernel import NeuroLingua  # noqa: E402
from raios.neuro_lingua.customer import speak as customer_speak  # noqa: E402

WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
OUT_DIR = ROOT / ".ai-os" / "receipts" / "c5-speak"

DEMOS = (
    ("GREENY_LIFE_EGYPT", "لو سمحت عندكم عسل البرسيم؟"),
    ("GREENS_NATURE_UAE", "إذا ما عليك أمر نبي حالة الشحنة H002"),
    ("GREEN_LINES_NORWAY_EU", "Har dere shipment status for H001?"),
    ("GREENY_LIFE_EGYPT", "الـ SKU H001 موجود في المخزون؟"),
    ("GREENS_NATURE_UAE", "نبيه عرض سعر للعسل"),
    ("GREEN_LINES_NORWAY_EU", "God dag. Invoice for SHIP-ORD-CUS-GCC-001 please."),
)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def wal_mtime():
    return WAL.stat().st_mtime if WAL.exists() else None


def render_md(rec: dict) -> str:
    lines = [
        "# لغة C5 المهنية — العملاء",
        "",
        f"- الوقت: `{rec['ts']}`",
        f"- نموذج اللغة: `NeuroLingua` (حتمي، بلا أوزان)",
        f"- استدعاء LLM: `{rec['llm_calls']}`",
        f"- أعضاء المجلس في هذه القناة: `false`",
        f"- WAL: لم يُمس `{rec['wal_mtime_unchanged']}`",
        f"- GL005_PROVEN: `false`",
        "",
        "اللغات الحية: مصري `ar-EG`، خليجي `ar-GULF`، إنجليزي تجاري `en`، نرويجي `nb-NO`.",
        "السعر غير المثبت لا يُخترع. الإمارات/النرويج ظل مسار Next.",
        "",
        "| شركة | فعل | رد العميل | رد التجارة |",
        "|---|---|---|---|",
    ]
    for row in rec["dialogues"]:
        cust = (row.get("customer_text") or "").replace("|", "/")
        trade = (row.get("trade_text") or "").replace("|", "/")
        lines.append(f"| `{row['company']}` | `{row.get('action')}` | {cust} | {trade} |")
    lines += ["", "`GL005_PROVEN=false`", ""]
    return "\n".join(lines)


async def run_dialogues(items: list[tuple[str, str]]) -> dict:
    wal_before = wal_mtime()
    nl = NeuroLingua()
    rows = []
    for company, text in items:
        row = await customer_speak(nl, text, company)
        row["input"] = text
        rows.append(row)
    rec = {
        "schema": "raios.c5-speak.v1",
        "ts": utc(),
        "from": "C5",
        "parent": "C1",
        "consult_used": False,
        "council_seats_this_channel": False,
        "dialogues": rows,
        "ok": all(r.get("ok") for r in rows) and all(r.get("llm_calls") == 0 for r in rows),
        "llm_calls": sum(int(r.get("llm_calls") or 0) for r in rows),
        "wal_written": False,
        "gl005_proven": False,
        "price_invented": False,
        "law": [
            "LANGUAGE_PROFESSIONAL_IS_NEUROLINGUA",
            "HF_WEIGHTS_NE_CUSTOMER_LANGUAGE",
            "PRICE_UNPROVEN_NE_INVENTED",
            "THIS_CHANNEL_NO_C_SEAT_CONSULT",
        ],
    }
    wal_after = wal_mtime()
    if wal_before != wal_after:
        raise SystemExit("SPEAK_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "LAST.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT_DIR / "LAST.md").write_text(render_md(rec), encoding="utf-8")
    return rec


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--text", default=None)
    p.add_argument("--company", default=None, choices=sorted(COMPANIES))
    p.add_argument("--demo", action="store_true")
    args = p.parse_args()
    if args.text and args.company:
        items = [(args.company, args.text)]
    else:
        items = list(DEMOS)
    rec = asyncio.run(run_dialogues(items))
    print(json.dumps({"ok": rec["ok"], "n": len(rec["dialogues"]), "llm_calls": rec["llm_calls"], "gl005_proven": False}, ensure_ascii=False, indent=2))
    print((OUT_DIR / "LAST.md").read_text(encoding="utf-8"))
    return 0 if rec["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
