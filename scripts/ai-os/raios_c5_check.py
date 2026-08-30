#!/usr/bin/env python3
"""C5 loyal-assistant checks: pulse evaluates, absorb digests, WAL untouched. Not GL-005 proof."""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from raios_absorb import absorb  # noqa: E402
from raios_c5_enforce import enforce  # noqa: E402
from raios_c5_read import classify, read_file  # noqa: E402
from raios_seats import load_seat_map  # noqa: E402

WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"


def check(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit("FAIL: " + msg)
    print("ok:", msg)


def load_heartbeat():
    spec = importlib.util.spec_from_file_location(
        "raios_heartbeat", ROOT / "scripts" / "ai-os" / "raios-service-heartbeat.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    seats_all = load_seat_map()["seats"]
    seats = seats_all["C5"]
    c1 = seats_all["C1"]
    check(seats["instance_role"] == "c1-assistant", "C5 instance is c1-assistant")
    check(seats["parent"] == "C1", "C5 parent is C1")
    check("post_opinion" in seats["tools"], "C5 has post_opinion")
    check("send_packet" in seats["tools"], "C5 has send_packet")
    check(seats["tools"] == c1["tools"], "C5 tools equal C1 tools")
    check("shell" in seats["deny"], "C5 denied shell")
    check("set_proven" in seats["deny"], "C5 denied set_proven")
    grant = json.loads((ROOT / ".ai-os" / "mcp" / "C5-GRANT.json").read_text(encoding="utf-8"))
    check(grant["duration"] == "PERMANENT", "C5 grant duration is PERMANENT")
    check(grant["grantor"] == "C1" and grant["grantee"] == "C5", "grant is C1 to C5")
    png = tempfile.NamedTemporaryFile("wb", suffix=".png", delete=False)
    png.write(bytes.fromhex("89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c4890000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"))
    png.close()
    kind = classify(Path(png.name), Path(png.name).read_bytes())
    check(kind == "image", "classifies png as image")
    deep = read_file(ROOT / ".ai-os" / "mcp" / "C5-GRANT.json", mode="deep")
    check(deep["kind"] in {"json", "text"}, "deep-reads grant json")
    check(deep.get("structure") is not None, "deep read extracted structure")
    Path(png.name).unlink(missing_ok=True)

    wal_before = WAL.stat().st_mtime if WAL.exists() else None
    hb = load_heartbeat()
    receipt = hb.evaluate()
    check(receipt["from"] == "C5", "pulse from C5")
    check(receipt["parent"] == "C1", "pulse parent C1")
    check(receipt["gl005_proven"] is False, "pulse cannot prove GL-005")
    check(receipt["wal_written_this_cycle"] is False, "pulse did not write WAL")
    check(receipt["second_wal_created"] is False, "no second WAL")
    check(receipt["seats"]["c5_loyal_assistant"] is True, "seat eval loyal assistant")
    check(receipt["seats"]["c5_has_post_opinion"] is True, "C5 may speak")
    mind_mod = importlib.util.spec_from_file_location(
        "raios_c5_mind", ROOT / "scripts" / "ai-os" / "raios_c5_mind.py"
    )
    assert mind_mod and mind_mod.loader
    mind_py = importlib.util.module_from_spec(mind_mod)
    mind_mod.loader.exec_module(mind_py)
    mind = mind_py.think()
    check(mind["from"] == "C5", "mind from C5")
    check(mind["parent"] == "C1", "mind parent C1")
    check(mind["gl005_proven"] is False, "mind cannot prove GL-005")
    check(mind["paid_api"] is False, "mind uses no paid API")
    check(mind["second_bus"] is False, "mind is not a second bus")
    check(mind["law_count"] >= 20, "mind indexed real laws")
    check(receipt["wal"]["exists"] is True, "WAL exists")
    md = hb.render_eval_md(receipt)
    check("ابن Cursor" in md, "eval md names son of Cursor")
    check("GL005_PROVEN" in md, "eval md keeps proven visible as false")

    huge = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
    nonce = datetime.now().isoformat()
    huge.write(("RAIOS DIGEST LINE %s %s\n" % (nonce, "x" * 80)) * 12000)
    huge.close()
    huge_path = Path(huge.name)
    rec = absorb([huge_path], source="c5-check-huge")
    check(rec["absorbed"] == 1, "first huge absorb is new")
    check(rec["bytes"] >= 1_000_000, "huge input was at least 1MB")
    check(rec["elapsed_ms"] < 5000, "huge absorb finished in moments")
    check(rec["wal_written"] is False, "absorb did not write WAL")
    check(rec["gl005_proven"] is False, "absorb cannot prove GL-005")
    again = absorb([huge_path], source="c5-check-huge-dup")
    check(again["deduped"] >= 1, "second absorb of same bytes is deduped")
    check(again["absorbed"] == 0, "duplicate does not create a new digest row")
    wal_after = WAL.stat().st_mtime if WAL.exists() else None
    check(wal_before == wal_after, "Cognitive WAL untouched by C5 pulse/absorb checks")
    huge_path.unlink(missing_ok=True)
    enf = enforce()
    check(enf["gl005_proven"] is False, "enforce cannot prove GL-005")
    check(enf["wal_written"] is False, "enforce did not write WAL")
    check((WAL.stat().st_mtime if WAL.exists() else None) == wal_before, "WAL untouched by enforce")
    print("raios_c5_check: PASS")
    print(json.dumps({"gl005_proven": False, "status": receipt["status"], "absorb_ms": rec["elapsed_ms"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
