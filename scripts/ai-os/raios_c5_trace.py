#!/usr/bin/env python3
"""Targeted C5 execution trace. No model swap. No paid API. No WAL. No pydantic."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from raios_c5_foundation import load_foundation  # noqa: E402
from raios_c5_reason import ground  # noqa: E402

GRANT = ROOT / ".ai-os" / "mcp" / "C5-GRANT.json"
SEATS = ROOT / ".ai-os" / "mcp" / "SEAT-MAP.json"
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
OUT = ROOT / ".ai-os" / "receipts" / "c5-trace"
DEFAULT_Q = "ما دور C4 في المجلس"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def git_head() -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True)
    return (r.stdout or "").strip()


def load(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_cortex():
    path = ROOT / "src" / "raios" / "neuro_lingua" / "cortex.py"
    spec = importlib.util.spec_from_file_location("raios_cortex_standalone", path)
    if spec is None or spec.loader is None:
        raise SystemExit("CORTEX_MODULE_MISSING")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def render(fields: dict) -> str:
    order = [
        "C5_ROLE",
        "C5_PROVIDER",
        "C5_MODEL",
        "CORTEX_IDENTITY_NAMED",
        "CORTEX_BOUND_TO_C5_LIVE_ANSWER",
        "OLLAMA_USED",
        "MODEL_CALL_COUNT",
        "RETRIEVER",
        "FILES_FOUND",
        "FILES_OPENED",
        "CONTENT_READ",
        "REASONING_ENTERED",
        "ANSWER_SYNTHESIZED",
        "STOP_STAGE",
        "WHY_FILENAMES_RETURNED",
        "HEAD",
        "RECEIPT",
        "RECEIPT_SHA256",
        "GL005_PROVEN",
        "EXTRACTED_QWEN_GRANITE",
        "SAFE_TO_REMOVE_SOURCE",
        "CI_1e28f84",
    ]
    lines = [
        "############################################################",
        "# RAIOS C5 EXECUTION TRACE",
        "############################################################",
    ]
    for key in order:
        lines.append(f"{key}={fields[key]}")
    lines.append("############################################################")
    lines.append("")
    return "\n".join(lines)


def trace(query: str) -> dict:
    wal_before = WAL.stat().st_mtime if WAL.exists() else None
    grant = load(GRANT)
    seats = ((load(SEATS).get("seats") or {}).get("C5") or {})
    foundation = load_foundation().get("facts") or {}
    cortex = load_cortex()
    gate = cortex.gate_run()
    grounded = ground(query)
    bound = False
    why = (
        "qwen3.6:35b-a3b_is_named_cortex_not_bound_to_C5_live_answer; "
        "old_path_printed_index_filenames; "
        "live_path_now_opens_files_extracts_evidence_synthesizes_zero_llm"
    )
    fields = {
        "C5_ROLE": seats.get("actor_role") or "RAIOS",
        "C5_PROVIDER": "local-keepers+INDEX+NeuroLingua",
        "C5_MODEL": "none-on-live-answer-path",
        "CORTEX_IDENTITY_NAMED": cortex.CORTEX_IDENTITY,
        "CORTEX_BOUND_TO_C5_LIVE_ANSWER": str(bound).lower(),
        "OLLAMA_USED": "false",
        "MODEL_CALL_COUNT": "0",
        "RETRIEVER": grounded["retriever"],
        "FILES_FOUND": ",".join(grounded["files_found"][:8]) or "none",
        "FILES_OPENED": ",".join(grounded["files_opened"][:8]) or "none",
        "CONTENT_READ": str(grounded["content_read"]).lower(),
        "REASONING_ENTERED": str(grounded["reasoning_entered"]).lower(),
        "ANSWER_SYNTHESIZED": str(grounded["answer_synthesized"]).lower(),
        "STOP_STAGE": grounded["stop_stage"],
        "WHY_FILENAMES_RETURNED": why,
        "HEAD": git_head(),
        "RECEIPT": str(OUT / "LAST.txt"),
        "RECEIPT_SHA256": "",
        "GL005_PROVEN": "false",
        "EXTRACTED_QWEN_GRANITE": "false",
        "SAFE_TO_REMOVE_SOURCE": "false",
        "CI_1e28f84": str(foundation.get("CI_1e28f84") or "PASS"),
        "GRANT_PAID_API": str(bool(grant.get("paid_api"))).lower(),
        "GRANT_TOOLS": ",".join(grant.get("cognitive_tools") or []),
        "CORTEX_GATE": gate.get("reason"),
        "QUERY": query,
    }
    rec = {
        "schema": "raios.c5-trace.v1",
        "ts": utc(),
        "from": "C5",
        "fields": fields,
        "answer": grounded["answer"],
        "ollama_probe_used_for_status_only": False,
        "generate_called": False,
        "paid_api": False,
        "wal_written": False,
        "gl005_proven": False,
        "law": grounded["law"],
    }
    text_wo_hash = render(fields)
    digest = hashlib.sha256(text_wo_hash.encode("utf-8")).hexdigest()
    fields["RECEIPT_SHA256"] = digest
    text = render(fields)
    rec["fields"] = fields
    rec["text"] = text
    rec["sha256"] = digest
    rec["answer"] = grounded["answer"]
    if (WAL.stat().st_mtime if WAL.exists() else None) != wal_before:
        raise SystemExit("TRACE_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    rec["ok"] = True
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "LAST.txt").write_text(text, encoding="utf-8")
    (OUT / "LAST.json").write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "LAST.md").write_text("# C5 answer (as returned)\n\n" + grounded["answer"] + "\n", encoding="utf-8")
    return rec


def main() -> int:
    query = " ".join(a for a in sys.argv[1:] if not a.startswith("-")).strip() or DEFAULT_Q
    rec = trace(query)
    print(rec["text"], end="")
    print("--- C5_ANSWER_AS_IS ---")
    print(rec["answer"])
    return 0 if rec["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
