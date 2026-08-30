#!/usr/bin/env python3
"""Bind the already-running Next server. Do not start one. Do not kill one."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gl004_lib import (  # noqa: E402
    BindError,
    EXIT_USAGE,
    ROOT,
    bind_live,
    refuse_spawn,
    write_json,
)

RECEIPT = ROOT / ".ai-os" / "receipts" / "GL004-RUNTIME-BIND.json"


def main() -> int:
    p = argparse.ArgumentParser(description="GL-004 RUNTIME_TRACE binder. BIND_DONT_SPAWN.")
    p.add_argument("--json", action="store_true", help="print bind receipt JSON")
    p.add_argument("--out", default=str(RECEIPT))
    p.add_argument("--spawn", action="store_true", help="forbidden; always refused")
    p.add_argument("--start", action="store_true", help="forbidden alias of --spawn")
    args = p.parse_args()
    if args.spawn or args.start:
        try:
            refuse_spawn()
        except BindError as err:
            print(json.dumps({"exit": err.code, "reason": err.reason, **err.extra}, indent=2))
            return err.code
    try:
        rec = bind_live()
    except BindError as err:
        payload = {"schema": "raios.gl004-runtime-bind.v1", "ok": False, "exit": err.code, "reason": err.reason, **err.extra}
        write_json(Path(args.out), payload)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return err.code
    rec["ok"] = True
    rec["exit"] = 0
    rec["receipt"] = args.out
    digest = write_json(Path(args.out), rec)
    rec_out = dict(rec)
    rec_out["receipt_sha256"] = digest
    # rewrite with hash of pre-hash file would change bytes. Record hash beside file.
    sidecar = Path(args.out).with_suffix(".sha256")
    sidecar.write_text(digest + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps({**rec, "receipt_sha256": digest}, indent=2, ensure_ascii=False))
    else:
        print(f"RUNTIME_TRACE_EXIT=0")
        print(f"PID={rec['pid']}")
        print(f"PPID={rec['ppid']}")
        print(f"PORT={rec['listen_port']}")
        print(f"MODE={rec['mode']}")
        print(f"HEAD={rec['head']}")
        print(f"HTTP_ROOT={rec['http'][0].get('status')}")
        print(f"LOG={rec['log'].get('path')}")
        print(f"RECEIPT={args.out}")
        print(f"RECEIPT_SHA256={digest}")
        print("SPAWNED=false")
        print("GL004_PROVEN=false  # bind is one child, not the set")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
