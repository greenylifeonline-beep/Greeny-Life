#!/usr/bin/env python3
"""Live seat map. C0 is abolished. Cursor is C1. Repair is not a C-code."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEAT_MAP_PATH = ROOT / ".ai-os" / "mcp" / "SEAT-MAP.json"

C0_ABOLISHED = "C0_SEAT_ABOLISHED"
REPAIR_UNSEATED = "REPAIR_EXECUTOR_NE_C_SEAT"
LIVE_CODES = tuple(f"C{i}" for i in range(1, 13))
MAIL_CODES = LIVE_CODES
LEGACY_MAIL: dict[str, str] = {}


def load_seat_map() -> dict:
    return json.loads(SEAT_MAP_PATH.read_text(encoding="utf-8"))


def seats() -> dict:
    return dict(load_seat_map()["seats"])


def board_codes() -> dict[str, dict]:
    out = {}
    for code, spec in seats().items():
        out[code] = {
            "actor": spec["actor_role"],
            "name": spec["name_ar"],
            "where": spec.get("where"),
            "instance": spec["instance_role"],
        }
    return out


def alias_to_code() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for code, spec in seats().items():
        mapping[code] = code
        mapping[spec["actor_role"].upper()] = code
        mapping[spec["instance_role"].upper().replace("-", "_")] = code
        for alias in spec.get("aliases") or []:
            mapping[str(alias).upper()] = code
    return mapping


def resolve_live_code(value: str) -> tuple[str, str]:
    raw = (value or "").strip().upper().replace(" ", "_")
    if raw in {"C0", "C-0"}:
        raise SystemExit(C0_ABOLISHED)
    if raw in {"POWERSHELL", "ENGINEER", "REPAIR"}:
        raise SystemExit(REPAIR_UNSEATED)
    mapping = alias_to_code()
    if raw not in mapping:
        raise SystemExit(f"UNKNOWN_CODE:{value}")
    code = mapping[raw]
    if code not in LIVE_CODES:
        raise SystemExit(f"UNKNOWN_CODE:{value}")
    return code, seats()[code]["actor_role"]


def resolve_mail_title_code(claimed: str) -> str | None:
    code = (claimed or "").strip().upper()
    if code == "C0":
        return None
    if code in LEGACY_MAIL:
        return LEGACY_MAIL[code]
    if code in MAIL_CODES:
        return code
    return None


def policy_actors() -> dict:
    actors = {}
    for code, spec in seats().items():
        actors[code] = {
            "actor_role": spec["actor_role"],
            "instance_role": spec["instance_role"],
            "tools": list(spec["tools"]),
            "deny": list(spec.get("deny") or []),
            "notes": spec.get("notes") or spec.get("name_en"),
        }
    return actors
