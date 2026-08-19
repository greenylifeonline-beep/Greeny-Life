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

    def run_gateway_false_pass_session(self, workdir: str | Path) -> dict[str, Any]:
        """HTTP 500 + liar LIVE. Isolated. Never promotes a gateway as LIVE."""
        from .gateway_cert import GatewayChatCertifier, language_evidence, prove_real_chat
        from .root_cause import classify_failure

        root = Path(workdir)
        root.mkdir(parents=True, exist_ok=True)
        started = time.perf_counter()
        detector = FalsePassDetector()
        cert = GatewayChatCertifier()
        stages: dict[str, Any] = {}

        liar_text = (
            "HEALTH_CHECK=PASS\nstatus=PASS\nQWEN_CHAT=PASS\nARABIC_CHAT=PASS\n"
            "STATUS=RAIOS_MULTIMODAL_GATEWAY_LIVE\n"
        )
        liar_script = "import sys; sys.stdout.write(" + repr(liar_text) + ")"
        liar = encoding_safe_run([sys.executable, "-c", liar_script], cwd=root)
        stages["REPRODUCE"] = {
            "returncode": liar.returncode,
            "printed_live": "LIVE" in liar.stdout,
            "printed_pass": "PASS" in liar.stdout,
            "ok": liar.returncode == 0 and "LIVE" in liar.stdout,
        }
        snap = root / "snapshot.json"
        snap.write_text(canonical_json({"stdout": liar.stdout, "returncode": liar.returncode}) + "\n", encoding="utf-8")
        stages["SNAPSHOT"] = {"path": str(snap), "exists": snap.is_file()}

        blocked = False
        try:
            detector.judge_child(liar.stdout, liar.stderr, liar.returncode)
        except FailClosed as exc:
            blocked = "FALSE_PASS" in str(exc)
        try:
            cert.certify(health={"http": 200, "ok": True}, chat={"http": 500, "body": ""})
            cert_blocked = False
        except FailClosed:
            cert_blocked = True
        stages["PATCH"] = {"detector_blocks_liar": blocked, "certifier_blocks_chat_500": cert_blocked, "canonical": False}

        family = classify_failure({"http": 500, "printed_pass": True, "live_claim": True, "failed": True, "chat_failed": True})
        family_500_only = classify_failure({"http": 500, "failed": True})
        stages["TEST"] = {"ok": blocked and cert_blocked and family == "FALSE_PASS" and family_500_only == "OLLAMA_SERVER_ERROR"}

        try:
            clean = cert.certify(
                health={"http": 200, "ok": True},
                chat={"http": 200, "body": "hello from cortex"},
                languages={"english": "hello from cortex"},
            )
            negative_ok = clean.get("overall_status") == "GATES_SATISFIED" and clean.get("STATUS") == "NOT_LIVE"
        except FailClosed:
            negative_ok = False
        stages["NEGATIVE_CONTROL"] = {"ok": negative_ok, "note": "healthy chat is GATES_SATISFIED not LIVE"}

        arabic_blocked = False
        try:
            cert.certify(
                health={"http": 200, "ok": True},
                chat={"http": 200, "body": "hello"},
                languages={"arabic": "hello", "english": "hello", "norwegian": "Hei"},
            )
        except FailClosed as exc:
            arabic_blocked = "LANGUAGE_GATE" in str(exc)
        stages["REGRESSION"] = {
            "ok": arabic_blocked and language_evidence("arabic", "مرحبا"),
            "note": "ARABIC_CHAT without Arabic script fails; 500-only stays OLLAMA_SERVER_ERROR",
        }

        stale = root / "stale-success.json"
        stale.write_text(canonical_json({"run_id": "old", "STATUS": "RAIOS_MULTIMODAL_GATEWAY_LIVE", "ok": True}) + "\n", encoding="utf-8")
        child = encoding_safe_run([sys.executable, "-c", "raise SystemExit(2)"], cwd=root)
        transfer_blocked = False
        try:
            cert.certify(
                health={"http": 200, "ok": True},
                chat={"http": 500, "body": ""},
                stale_live_path=stale,
                run_id="new-run",
            )
        except FailClosed:
            transfer_blocked = child.returncode != 0
        stages["UNSEEN_TRANSFER"] = {
            "ok": transfer_blocked,
            "child_exit": child.returncode,
            "stale_artifact": str(stale),
            "principle": "nonzero_or_failed_chat_plus_stale_success_is_not_certification",
        }

        try:
            detector.judge_child(liar.stdout, liar.stderr, 0)
            rollback_ok = False
        except FailClosed as exc:
            rollback_ok = "FALSE_PASS" in str(exc)
        stages["ROLLBACK_TEST"] = {"ok": rollback_ok, "note": "LIVE+PASS still fail-closed"}
        live_proof = prove_real_chat()
        stages["PROMOTION_CANDIDATE"] = {
            "ok": False,
            "reason": "NO_CANONICAL_AUTO_PROMOTION",
            "real_chat": live_proof,
        }

        missing = [name for name in LIFECYCLE if name not in stages]
        if missing:
            raise FailClosed("SHADOW_LIFECYCLE_INCOMPLETE:" + ",".join(missing))
        success = all(
            bool(stages[name].get("ok", True))
            for name in LIFECYCLE
            if name not in {"PROMOTION_CANDIDATE", "SNAPSHOT", "PATCH"}
        )
        result = {
            "lab": "gateway-anti-false-pass",
            "created_at": utc_now(),
            "stages": stages,
            "repair_success": bool(blocked and cert_blocked and transfer_blocked and rollback_ok and negative_ok),
            "regression_count": 0 if stages["REGRESSION"]["ok"] else 1,
            "transfer_success": transfer_blocked,
            "shared_principle": "partial_gate_success_plus_failed_mandatory_gate_cannot_certify",
            "blast_radius": ["ccee.gateway_cert.GatewayChatCertifier", "ccee.root_cause.classify_failure", "ccee.config.contains_forbidden_success"],
            "duration_ms": round((time.perf_counter() - started) * 1000.0, 3),
            "confidence": 0.74 if success else 0.3,
            "canonical_promotion": False,
            "executed": True,
            "STATUS": "NOT_LIVE",
            "QWEN_CHAT": "FAILED" if not live_proof.get("ok") else "UNPROVEN",
        }
        result["sha256"] = sha256_obj(result)
        (root / "gateway-integrity-lab.json").write_text(canonical_json(result) + "\n", encoding="utf-8")
        if not result["repair_success"]:
            raise FailClosed("SHADOW_GATEWAY_LAB_FAILED")
        return result
