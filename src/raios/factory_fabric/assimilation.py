from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .state_import import load_imported_jsonl_events


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def stable_id(prefix: str, payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return f"{prefix}:{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]}"


def canonical_text(event: dict[str, Any]) -> str:
    keys = (
        "lesson_type",
        "subject",
        "failure_class",
        "task",
        "task_id",
        "capability",
        "observation",
        "learned_rule",
        "teacher_evidence",
        "prompt",
        "student_response",
    )
    vals: list[str] = []
    for key in keys:
        if key in event:
            try:
                vals.append(json.dumps(event[key], ensure_ascii=False, sort_keys=True))
            except Exception:
                vals.append(str(event[key]))
    if not vals:
        vals.append(json.dumps(event, ensure_ascii=False, sort_keys=True)[:5000])
    return " ".join(vals)


def capability_guess(text: str) -> str:
    t = text.lower()
    rules = (
        ("FALSE_PASS", ("false_pass", "false-pass", "certification")),
        ("DIAGNOSTIC_REPAIR", ("repair", "root cause", "diagnostic", "failure", "traceback")),
        ("ENGINE_INTELLIGENCE", ("engine", "runtime", "orchestrator", "duplicate")),
        ("FILE_INTELLIGENCE", ("file", "search", "index", "parser", "symbol")),
        ("COMMUNICATION", ("gateway", "chat", "websocket", "message", "communication")),
        ("LEARNING", ("learning", "assimilation", "transfer", "retention", "teacher")),
        ("GOVERNANCE", ("permission", "approval", "governance", "canonical")),
        ("CODE_REPAIR", ("code", "syntax", "import", "patch", "compile")),
    )
    scored = []
    for name, terms in rules:
        score = sum(1 for term in terms if term in t)
        if score:
            scored.append((score, name))
    return sorted(scored, reverse=True)[0][1] if scored else "GENERAL"


def priority(event: dict[str, Any], text: str) -> int:
    t = text.lower()
    score = 0
    if any(x in t for x in ("failure", "error", "repair")):
        score += 4
    if any(x in t for x in ("false_pass", "false-pass")):
        score += 6
    if any(x in t for x in ("canonical", "permission")):
        score += 4
    if bool(event.get("student_execution_required") or event.get("execution_required")):
        score += 3
    if bool(event.get("transfer_required")):
        score += 2
    state = str(event.get("state") or event.get("status") or "").upper()
    if state in {"FAILED", "FAILED_ATTEMPT", "DISCOVERED", "OBSERVED", "ASSIGNED"}:
        score += 2
    return score


def build_curriculum(runtime_root: str | Path) -> dict:
    runtime_root = Path(runtime_root).expanduser().resolve()
    out = runtime_root / "assimilation"
    queue_dir = out / "queue"
    unit_dir = out / "units"
    report_dir = out / "reports"
    for p in (queue_dir, unit_dir, report_dir):
        p.mkdir(parents=True, exist_ok=True)

    raw = load_imported_jsonl_events(runtime_root)
    unique: dict[str, dict[str, Any]] = {}
    duplicates = 0

    for row in raw:
        event = row["event"]
        text = canonical_text(event)
        signature = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if signature in unique:
            duplicates += 1
            continue
        unique[signature] = {**row, "text": text}

    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for signature, row in unique.items():
        event = row["event"]
        text = row["text"]
        cap = capability_guess(text)
        groups[cap].append({
            "signature": signature,
            "priority": priority(event, text),
            **row,
        })

    units = []
    for capability, items in groups.items():
        items = sorted(items, key=lambda x: x["priority"], reverse=True)
        for start in range(0, len(items), 12):
            batch = items[start:start + 12]
            unit_id = stable_id(
                "assim",
                {"capability": capability, "signatures": [x["signature"] for x in batch]},
            )
            unit = {
                "schema": "raios.assimilation.unit.v2",
                "assimilation_unit_id": unit_id,
                "capability": capability,
                "material_count": len(batch),
                "priority": max(x["priority"] for x in batch),
                "materials": [
                    {
                        "signature": x["signature"],
                        "donor": x["donor"],
                        "source_relative": x["source_relative"],
                        "source_sha256": x["source_sha256"],
                        "source_event": x["event"],
                    }
                    for x in batch
                ],
                "student": "RAIOS_MAIN_CORTEX",
                "required_cycle": [
                    "COMPREHENSION",
                    "CONNECTION",
                    "STUDENT_EXECUTION",
                    "TEACHER_EVALUATION",
                    "CORRECTION",
                    "TRANSFER",
                    "RETENTION",
                ],
                "state": "QUEUED_FOR_ASSIMILATION",
                "mastery": False,
                "created_at": utc(),
            }
            (unit_dir / f"{unit_id.replace(':', '_')}.json").write_text(
                json.dumps(unit, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            units.append({
                "assimilation_unit_id": unit_id,
                "capability": capability,
                "priority": unit["priority"],
                "material_count": unit["material_count"],
                "state": "READY",
                "assigned_student": "RAIOS_MAIN_CORTEX",
            })

    units.sort(key=lambda x: (x["priority"], x["material_count"]), reverse=True)
    queue = {
        "schema": "raios.assimilation.queue.v2",
        "status": "READY",
        "raw_events": len(raw),
        "unique_materials": len(unique),
        "duplicates_removed": duplicates,
        "assimilation_units": len(units),
        "queue": units,
        "created_at": utc(),
    }
    (queue_dir / "ASSIMILATION-QUEUE.json").write_text(
        json.dumps(queue, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    summary = {
        "schema": "raios.assimilation.factory.report.v2",
        "status": "PASS" if raw else "PASS_EMPTY_INPUT",
        "raw_events": len(raw),
        "unique_materials": len(unique),
        "duplicates_removed": duplicates,
        "assimilation_units": len(units),
        "capabilities": dict(Counter(x["capability"] for x in units)),
        "state": "CURRICULUM_BUILT",
        "student_execution_required": True,
        "teacher_supervision_required": True,
        "transfer_required": True,
        "retention_required": True,
        "source_dependency": "EXTERNALIZED_FACTORY_ESTATE",
        "created_at": utc(),
    }
    (report_dir / "ASSIMILATION-FACTORY.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return summary
