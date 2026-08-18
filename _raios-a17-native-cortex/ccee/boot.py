"""Boot RAIOS CCEE with the Diagnostic & Repair Nervous System.

Does not print WORK_GATE=OPEN. The supervisor writes the gate file.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from .config import canonical_json, native_root, repo_root_from, sha256_text, authoritative_exit
from .doctor import run_doctor
from .ollama_runtime import OllamaRuntimeManager


def boot(argv: list[str] | None = None) -> dict[str, Any]:
    repo = repo_root_from()
    native = native_root(repo)
    root = native / "ccee" / "var" / "boot"
    evidence = native / "evidence"
    report = run_doctor(root, repo, evidence)
    ollama = OllamaRuntimeManager()
    inv = ollama.inventory()
    try:
        ollama.generate("ping")
        generate_ok = True
        generate_error = None
    except Exception as exc:  # FailClosed and transport
        generate_ok = False
        generate_error = f"{type(exc).__name__}:{exc}"
    gate_path = root / "nervous" / "work_gate.json"
    gate = {}
    if gate_path.is_file():
        import json

        gate = json.loads(gate_path.read_text(encoding="utf-8"))
    out = {
        "overall_status": report.get("overall_status"),
        "exit_code": report.get("exit_code"),
        "work_gate": gate.get("state") or "CLOSED",
        "semantic": gate.get("semantic") or "NOT_READY_FOR_REAL_PROJECT_WORK",
        "main_cortex": inv,
        "generate_ok": generate_ok,
        "generate_error": generate_error,
        "nervous": report.get("nervous"),
        "canonical": False,
    }
    if out["work_gate"] == "READY_FOR_REAL_PROJECT_WORK" and not inv.get("main_cortex_present"):
        out["overall_status"] = "FAILED"
        out["exit_code"] = 1
        out["integrity"] = "SYSTEM_INTEGRITY_FAILURE"
    text = canonical_json(out)
    out["sha256"] = sha256_text(text)
    receipt = native / "reports" / "RAIOS-BOOT-RECEIPT.json"
    receipt.parent.mkdir(parents=True, exist_ok=True)
    receipt.write_text(canonical_json(out) + "\n", encoding="utf-8")
    readback = receipt.read_text(encoding="utf-8")
    if sha256_text(canonical_json({k: v for k, v in out.items() if k != "sha256"})) not in readback and out["sha256"] not in readback:
        out["exit_code"] = 1
        out["overall_status"] = "FAILED"
        out["integrity"] = "RECEIPT_READBACK_FAILED"
    return out


def main(argv: list[str] | None = None) -> int:
    report = boot(argv)
    sys.stdout.write(
        canonical_json(
            {
                "overall_status": report.get("overall_status"),
                "exit_code": report.get("exit_code"),
                "work_gate": report.get("work_gate"),
                "semantic": report.get("semantic"),
            }
        )
        + "\n"
    )
    return authoritative_exit(report.get("exit_code"))


if __name__ == "__main__":
    raise SystemExit(main())
