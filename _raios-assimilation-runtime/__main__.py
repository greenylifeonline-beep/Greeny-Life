"""Live assimilation runtime CLI."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from live_bridge import main

if __name__ == "__main__":
    raise SystemExit(main())
