"""Bind C2 to existing A2A semantic layer. Prints required all-hands flags."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from raios.a2a_all_hands.bind import bind_c2, flags_text


def main() -> int:
    flags = bind_c2(probe_live=True)
    report = ROOT / ".ai-os" / "reports" / "a2a-all-hands" / "RAIOS-A2A-ALL-HANDS-BIND-02"
    report.mkdir(parents=True, exist_ok=True)
    (report / "BIND-RESULT.json").write_text(json.dumps(flags, indent=2, default=str) + "\n", encoding="utf-8")
    print(flags_text(flags))
    return 0 if flags["BLOCKERS"] == "none" and flags["C2_A2A_BOUND"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
