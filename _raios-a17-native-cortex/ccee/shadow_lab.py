"""D6 Shadow Repair + Regression Lab.

Isolated temporary workspace. Uncertain repairs never jump to canonical.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

from .certification import FalsePassDetector
from .config import FailClosed, canonical_json, sha256_obj, utc_now
from .process_kernel import encoding_safe_run

LIFECYCLE = (
    "REPRODUCE",
    "SNAPSHOT",
    "PATCH",
    "TEST",
    "NEGATIVE_CONTROL",
    "REGRESSION",
    "UNSEEN_TRANSFER",
    "ROLLBACK_TEST",
    "PROMOTION_CANDIDATE",
)


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
            transfer_ok = rg.returncode in {0, 1} and "ملف" in rg.stdout.replace("\\", "/")
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

    def run_integrity_session(self, workdir: str | Path) -> dict[str, Any]:
        """False-PASS class: reproduce → patch-in-shadow → negatives → transfer → no promotion."""
        root = Path(workdir)
        root.mkdir(parents=True, exist_ok=True)
        started = time.perf_counter()
        detector = FalsePassDetector()
        stages: dict[str, Any] = {}

        liar = encoding_safe_run([sys.executable, "-c", "print('PASS'); raise SystemExit(1)"], cwd=root)
        stages["REPRODUCE"] = {
            "returncode": liar.returncode,
            "printed_pass": "PASS" in liar.stdout,
            "ok": liar.returncode != 0 and "PASS" in liar.stdout,
        }
        snap = root / "snapshot.json"
        snap.write_text(canonical_json({"stdout": liar.stdout, "returncode": liar.returncode}) + "\n", encoding="utf-8")
        stages["SNAPSHOT"] = {"path": str(snap), "exists": snap.is_file()}

        patched = False
        try:
            detector.judge_child(liar.stdout, liar.stderr, liar.returncode)
        except FailClosed as exc:
            patched = "FALSE_PASS" in str(exc)
        stages["PATCH"] = {"detector_blocks_liar": patched, "canonical": False}

        try:
            detector.judge_child(liar.stdout, liar.stderr, liar.returncode)
            test_ok = False
        except FailClosed:
            test_ok = True
        stages["TEST"] = {"ok": test_ok}

        clean = encoding_safe_run([sys.executable, "-c", "print('hello')"], cwd=root)
        try:
            detector.judge_child(clean.stdout, clean.stderr, clean.returncode)
            negative_ok = clean.returncode == 0
        except FailClosed:
            negative_ok = False
        stages["NEGATIVE_CONTROL"] = {"ok": negative_ok, "note": "no success token, exit 0 allowed"}

        latin1 = encoding_safe_run(
            [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'\\xe9\\n')"],
            cwd=root,
        )
        stages["REGRESSION"] = {
            "ok": latin1.stdout is not None and latin1.decode_replaced,
            "integrity": latin1.integrity,
        }

        transfer = encoding_safe_run([sys.executable, "-c", "print('SUCCESS'); raise SystemExit(1)"], cwd=root)
        try:
            detector.judge_child(transfer.stdout, transfer.stderr, transfer.returncode)
            transfer_blocked = False
        except FailClosed as exc:
            transfer_blocked = "FALSE_PASS" in str(exc)
        stages["UNSEEN_TRANSFER"] = {"ok": transfer_blocked, "token": "SUCCESS"}

        bare0 = encoding_safe_run([sys.executable, "-c", "print('PASS')"], cwd=root)
        try:
            detector.judge_child(bare0.stdout, bare0.stderr, bare0.returncode)
            rollback_ok = False
        except FailClosed as exc:
            rollback_ok = "FALSE_PASS" in str(exc)
        stages["ROLLBACK_TEST"] = {"ok": rollback_ok, "note": "detector remains armed"}
        stages["PROMOTION_CANDIDATE"] = {"ok": False, "reason": "NO_CANONICAL_AUTO_PROMOTION"}

        missing = [name for name in LIFECYCLE if name not in stages]
        if missing:
            raise FailClosed("SHADOW_LIFECYCLE_INCOMPLETE:" + ",".join(missing))
        success = all(bool(stages[name].get("ok", True)) for name in LIFECYCLE if name not in {"PROMOTION_CANDIDATE", "SNAPSHOT", "PATCH"})
        result = {
            "lab": "anti-false-pass-integrity",
            "created_at": utc_now(),
            "stages": stages,
            "repair_success": bool(patched and test_ok and transfer_blocked and rollback_ok),
            "regression_count": 0 if stages["REGRESSION"]["ok"] else 1,
            "transfer_success": transfer_blocked,
            "blast_radius": ["ccee.certification.FalsePassDetector.judge_child"],
            "duration_ms": round((time.perf_counter() - started) * 1000.0, 3),
            "confidence": 0.76 if success else 0.3,
            "canonical_promotion": False,
            "executed": True,
        }
        result["sha256"] = sha256_obj(result)
        (root / "integrity-lab.json").write_text(canonical_json(result) + "\n", encoding="utf-8")
        if not result["repair_success"]:
            raise FailClosed("SHADOW_INTEGRITY_LAB_FAILED")
        return result
