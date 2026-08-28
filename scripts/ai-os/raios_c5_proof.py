#!/usr/bin/env python3
"""Proof gate, not naming gate. Claims must become repeatable operational evidence. No C3. No GL005 PASS print."""
from __future__ import annotations

import importlib.util
import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
OUT_DIR = ROOT / ".ai-os" / "receipts" / "c5-proof"
MEETING = "GL-COUNCIL-4a11023c3c321b6f"
LIVE = (
    ("grind", "scripts/ai-os/raios_c5_grind.py", "grind"),
    ("week", "scripts/ai-os/raios_c5_week.py", "run_slot"),
    ("minute", "scripts/ai-os/raios_c5_minute.py", "exam"),
    ("plan", "scripts/ai-os/raios_c5_plan.py", "evaluate"),
)
PORTS = (3000, 3001, 3107, 8787)


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_mod(rel: str):
    path = ROOT / rel
    if not path.is_file():
        raise FileNotFoundError(rel)
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def wal_mtime():
    return WAL.stat().st_mtime if WAL.exists() else None


def gate(name: str, status: str, detail: str, evidence: dict | None = None) -> dict:
    rec = {"gate": name, "status": status, "detail": detail}
    if evidence:
        rec["evidence"] = evidence
    return rec


def http(method: str, url: str, data: bytes | None = None) -> dict:
    req = urllib.request.Request(url, data=data, method=method, headers={"Content-Type": "application/json", "User-Agent": "raios-c5-proof/1"})
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            body = resp.read()[:400]
            return {"ok": True, "code": resp.status, "len": len(body)}
    except urllib.error.HTTPError as exc:
        return {"ok": False, "code": exc.code, "len": 0}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "code": None, "error": type(exc).__name__}


def prove() -> dict:
    wal_before = wal_mtime()
    plan = load_mod("scripts/ai-os/raios_c5_plan.py")
    claimed = list(plan.CLAIMED_SCRIPTS)
    present = [n for n in claimed if (ROOT / "scripts" / "ai-os" / n).exists()]
    missing = [n for n in claimed if n not in present]
    gates: list[dict] = []

    gates.append(
        gate(
            "c1_foundation",
            "LOCKED",
            "CI(1e28f84)=PASS; CI(68af867)=PASS; EXTRACTED_QWEN_GRANITE=false; SAFE_TO_REMOVE_SOURCE=false; GL005_PROVEN=false",
            {
                "CI_PASS_NE_ASSIMILATION": True,
                "CI_PASS_NE_GL005": True,
                "gl005_proven": False,
                "extracted_qwen_granite": False,
                "safe_to_remove_source": False,
                "authenticated_orchestration_task": False,
            },
        )
    )
    gates.append(
        gate(
            "p0_order",
            "LOCKED",
            "1=AUTHENTICATED_ORCHESTRATION_TASK 2=QWEN_GRANITE_ASSIMILATION 3=GL005; CI pass is not either proof",
            {
                "authenticated_orchestration_task": False,
                "extracted_qwen_granite": False,
                "gl005_proven": False,
                "safe_to_remove_source": False,
                "source_deleted": False,
                "student_ne_extraction": True,
            },
        )
    )
    gates.append(
        gate(
            "claim_inventory",
            "OBSERVED",
            f"claimed={len(claimed)} live={len(LIVE)}",
            {"claimed": len(claimed), "live_keepers": [x[0] for x in LIVE]},
        )
    )
    gates.append(
        gate(
            "existence",
            "FAIL" if missing else "PASS_CANDIDATE",
            f"claimed_present={len(present)}/{len(claimed)} live_present={sum((ROOT / p).exists() for _, p, _ in LIVE)}/{len(LIVE)}",
            {"claimed_present": present, "claimed_missing_count": len(missing)},
        )
    )

    import_live = []
    mods = {}
    for name, rel, fn in LIVE:
        try:
            mods[name] = load_mod(rel)
            import_live.append({"name": name, "ok": True, "fn": hasattr(mods[name], fn)})
        except Exception as exc:  # noqa: BLE001
            import_live.append({"name": name, "ok": False, "error": type(exc).__name__})
    gates.append(
        gate(
            "import_load",
            "PASS_CANDIDATE" if all(x["ok"] and x.get("fn") for x in import_live) and not present else "FAIL",
            "claimed imports skipped because existence failed; live modules loaded",
            {"live": import_live, "claimed_import_attempted": False},
        )
    )

    exec_rows = []
    io_rows = []
    if "plan" in mods:
        rec = mods["plan"].evaluate()
        exec_rows.append({"name": "plan", "ok": rec.get("ok") is True, "execute_empire": rec.get("execute_empire")})
        io_rows.append({"name": "plan", "ok": (OUT_DIR.parent / "c5-plan" / "LAST.md").exists() and rec.get("gl005_proven") is False})
    if "minute" in mods:
        rec = mods["minute"].exam()
        exec_rows.append({"name": "minute", "ok": rec.get("ok") is True})
        io_rows.append({"name": "minute", "ok": rec.get("gl005_proven") is False})
    if "week" in mods:
        rec = mods["week"].run_slot(4)
        exec_rows.append({"name": "week-day-4", "ok": rec.get("ok") is True})
        io_rows.append({"name": "week", "ok": rec.get("gl005_proven") is False and rec.get("wal_mtime_unchanged") is True})
    grind_rec = None
    if "grind" in mods:
        grind_rec = mods["grind"].grind()
        exec_rows.append({"name": "grind", "ok": grind_rec.get("ok") is True})
        last = ROOT / ".ai-os" / "receipts" / "c5-grind" / "LAST.json"
        io_rows.append(
            {
                "name": "grind",
                "ok": last.exists() and grind_rec.get("files_scanned", 0) > 0 and grind_rec.get("gl005_proven") is False,
                "files_scanned": grind_rec.get("files_scanned"),
            }
        )
    gates.append(gate("execution", "PASS_CANDIDATE" if all(x["ok"] for x in exec_rows) else "FAIL", "live keepers executed", {"rows": exec_rows}))
    gates.append(gate("real_io", "PASS_CANDIDATE" if all(x["ok"] for x in io_rows) else "FAIL", "real receipts written; GL005 stays false", {"rows": io_rows}))

    wal_mid = wal_mtime()
    second_wal = (ROOT / "RAIOS" / "V9" / "wal" / "sqlite").exists() or (ROOT / ".ai-os" / "wal.sqlite").exists()
    live_guard_ok = wal_mid == wal_before and not second_wal
    gates.append(
        gate(
            "live_guard",
            "PASS_CANDIDATE" if live_guard_ok else "FAIL",
            "WAL unchanged; no second WAL; no GL005 print-PASS",
            {"wal_unchanged": wal_mid == wal_before, "second_wal": second_wal},
        )
    )

    recovered = True
    try:
        load_mod("scripts/ai-os/" + (missing[0] if missing else "nope.py"))
        recovered = False
    except (FileNotFoundError, ImportError, ValueError, AttributeError, OSError):
        recovered = True
    except Exception:
        recovered = True
    if missing:
        plan.evaluate()
    gates.append(
        gate(
            "failure_recovery",
            "PASS_CANDIDATE" if recovered and missing else "FAIL",
            "absent claimed script does not crash the runner; plan still evaluates",
            {"missing_sample": missing[0] if missing else None, "recovered": recovered},
        )
    )

    probes = []
    session = None
    post = None
    for port in PORTS:
        base = f"http://127.0.0.1:{port}"
        get_s = http("GET", base + "/api/auth/session")
        probes.append({"port": port, "path": "/api/auth/session", **get_s})
        if get_s.get("code") is not None:
            session = get_s
            get_t = http("GET", base + "/api/tasks")
            probes.append({"port": port, "path": "/api/tasks", **get_t})
            post = http("POST", base + "/api/tasks", b'{"title":"proof-gate"}')
            probes.append({"port": port, "path": "POST /api/tasks", **post})
            break
    if session is None:
        gl_status = "UNPROVEN"
        gl_detail = "no live HTTP app on probed ports; AUTHENTICATED_MUTATION not observed"
    elif post and post.get("code") == 401:
        gl_status = "BLOCKED"
        gl_detail = "POST 401 AUTH_GATE_PRESENT; mutation not executed"
    elif post and post.get("code") in {200, 201}:
        gl_status = "UNPROVEN"
        gl_detail = "POST returned success without before/after proof; not GL005"
    else:
        gl_status = "UNPROVEN"
        gl_detail = f"session/post observed without authenticated mutation post={post}"
    gates.append(gate("gl005_proof", gl_status, gl_detail, {"probes": probes, "gl005_proven": False}))

    brains = (grind_rec or {}).get("brains") or []
    domains = (grind_rec or {}).get("domains") or []
    cycle = {
        "observe": {
            "files_scanned": (grind_rec or {}).get("files_scanned"),
            "prisma_models": len((grind_rec or {}).get("prisma_models") or []),
            "api_routes": len((grind_rec or {}).get("api_routes") or []),
            "ms": (grind_rec or {}).get("ms"),
            "mill_stats_ne_learning": True,
        },
        "reason": {
            "highest_value_gaps": [
                b["id"] for b in brains if b.get("gap_open")
            ]
            + [d["id"] for d in domains if d.get("thin")],
            "reuse_before_build": True,
        },
        "act_shadow": {
            "executed_product_write": False,
            "filled_gl003": False,
            "install_celerp": False,
        },
        "verify": {g["gate"]: g["status"] for g in gates},
        "learn": {"knowledge_state": "DISCOVERED", "promoted": False, "validated": False},
        "replay": {"week_day_4": True, "proof_rerunnable": True},
    }
    (OUT_DIR / "CYCLE.json").parent.mkdir(parents=True, exist_ok=True)

    rec = {
        "schema": "raios.c5-proof.v1",
        "meeting_id": MEETING,
        "case": "CASE-009",
        "ts": utc(),
        "from": "C5",
        "parent": "C1",
        "naming_gate": False,
        "proof_gate": True,
        "c3_transition": False,
        "wide_execute_adopted": False,
        "claimed_count": len(claimed),
        "claimed_present": len(present),
        "gates": gates,
        "cycle": cycle,
        "gl005_proven": False,
        "gl005_status": gl_status,
        "knowledge_state": "DISCOVERED",
        "canonical": False,
        "wal_written": False,
        "law": [
            "NAMING_GATE_NE_PROOF_GATE",
            "CLAIM_INVENTORY_NE_EXISTENCE",
            "EXISTENCE_NE_IMPORT",
            "IMPORT_NE_EXECUTION",
            "EXECUTION_NE_REAL_IO",
            "REAL_IO_NE_LIVE_GUARD",
            "LIVE_GUARD_NE_GL005",
            "CI_PASS_NE_ASSIMILATION",
            "CI_PASS_NE_GL005",
            "PRINTED_PASS_NE_EVIDENCE",
            "C3_TRANSITION_REQUIRES_PROOF",
            "FAIL_STAYS_FALSE",
            "REUSE_BEFORE_BUILD",
            "LIVE_GUARD_BEFORE_NEW_ENGINE",
            "PRACTICE_BEFORE_PROMOTION",
            "MILL_STATS_NE_LEARNING",
            "MS_NE_INTELLIGENCE",
        ],
    }
    wal_after = wal_mtime()
    if wal_before != wal_after:
        raise SystemExit("PROOF_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    rec["ok"] = gl_status in {"FAIL", "BLOCKED", "UNPROVEN"} and rec["gl005_proven"] is False and rec["c3_transition"] is False
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "CYCLE.json").write_text(json.dumps(cycle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT_DIR / "LAST.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# بوابة إثبات — CASE-009",
        "",
        "- بوابة تسمية: `false`",
        f"- ادعاءات: `{len(claimed)}` موجودة: `{len(present)}`",
        f"- انتقال C3: `{rec['c3_transition']}`",
        f"- تنفيذ واسع: `{rec['wide_execute_adopted']}`",
        f"- GL005: `{gl_status}` → يبقى `false`",
        f"- فجوات الظل: `{cycle['reason']['highest_value_gaps']}`",
        "- أرقام الطحن ≠ تعلم. ms ≠ ذكاء.",
        "",
        "| بوابة | حالة |",
        "|---|---|",
    ]
    for g in gates:
        lines.append(f"| `{g['gate']}` | `{g['status']}` |")
    lines += ["", "`GL005_PROVEN=false`", ""]
    (OUT_DIR / "LAST.md").write_text("\n".join(lines), encoding="utf-8")
    return rec


def main() -> int:
    rec = prove()
    print(
        json.dumps(
            {
                "ok": rec["ok"],
                "claimed_present": rec["claimed_present"],
                "c3_transition": False,
                "wide_execute_adopted": False,
                "gl005_status": rec["gl005_status"],
                "gl005_proven": False,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    print((OUT_DIR / "LAST.md").read_text(encoding="utf-8"))
    return 0 if rec["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
