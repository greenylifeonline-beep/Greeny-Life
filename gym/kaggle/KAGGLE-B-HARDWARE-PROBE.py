#!/usr/bin/env python3
"""KAGGLE-B hardware probe. Independent worker. Not a quota bypass for A."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from hardware_probe import probe  # noqa: E402

WORKER_ID = "KAGGLE_B"


def main() -> int:
    import json

    rec = probe(WORKER_ID)
    print(json.dumps(rec, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
