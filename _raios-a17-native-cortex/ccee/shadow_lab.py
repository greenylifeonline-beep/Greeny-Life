"""D6 Shadow Repair + Regression Lab.

Executes the encoding-safe kernel against real children. Does not write
canonical files. Promotion remains forbidden here.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from .config import FailClosed, sha256_obj, utc_now
from .process_kernel import encoding_safe_run


class ShadowRepairLab:
    def run_encoding_lab(self, workdir: str | Path) -> dict[str, Any]:
        root = Path(workdir)
        root.mkdir(parents=True, exist_ok=True)
        positive = encoding_safe_run(
            [sys.executable, "-c", "import sys; sys.stdout.write('utf8-ok café\\n')"],
            cwd=root,
        )
        negative = encoding_safe_run(
            [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'\\xe9\\n')"],
            cwd=root,
        )
        transfer_dir = root / "xfer"
        transfer_dir.mkdir(exist_ok=True)
        unicode_file = transfer_dir / "ملف.txt"
        unicode_file.write_text("needle-raios\n", encoding="utf-8")
        try:
            rg = encoding_safe_run(["rg", "-l", "needle-raios", str(transfer_dir)], cwd=root)
            transfer_ok = rg.returncode in {0, 1} and ("ملف" in rg.stdout or "needle-raios" in unicode_file.read_text(encoding="utf-8"))
            rg_integrity = rg.integrity
            rg_code = rg.returncode
        except FailClosed:
            transfer_ok = "needle-raios" in unicode_file.read_text(encoding="utf-8")
            rg_integrity = "RG_UNAVAILABLE"
            rg_code = 127
        if positive.returncode != 0:
            raise FailClosed("SHADOW_POSITIVE_FAILED")
        if negative.stdout is None:
            raise FailClosed("SHADOW_NEGATIVE_NONE_STDOUT")
        if not negative.decode_replaced:
            raise FailClosed("SHADOW_NEGATIVE_EXPECTED_REPLACEMENT")
        transfer_ok = rg.returncode in {0, 1} and "ملف" in rg.stdout.replace("\\", "/")
        result = {
            "lab": "encoding-safe-subprocess",
            "created_at": utc_now(),
            "positive": {"ok": positive.returncode == 0, "integrity": positive.integrity},
            "negative": {
                "ok": negative.stdout != "" or negative.stdout_bytes_len > 0,
                "decode_replaced": negative.decode_replaced,
                "raised": False,
            },
            "transfer": {"ok": transfer_ok, "returncode": rg_code, "integrity": rg_integrity},
            "canonical_promotion": False,
            "executed": True,
        }
        result["sha256"] = sha256_obj(result)
        if not (result["positive"]["ok"] and result["negative"]["ok"]):
            raise FailClosed("SHADOW_LAB_FAILED")
        return result
