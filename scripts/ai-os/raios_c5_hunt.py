#!/usr/bin/env python3
"""Hunt free local resources for C5. Catalog + invent. No paid API. No WAL dump."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_JSON = ROOT / ".ai-os" / "learning" / "FREE-RESOURCES.json"
OUT_MD = ROOT / ".ai-os" / "learning" / "FREE-RESOURCES.md"
GIT_MEMORY = ROOT / ".ai-os" / "learning" / "C1-GIT-MEMORY.md"
WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def which(name: str) -> str | None:
    return shutil.which(name)


def count_files(rel: str) -> int:
    path = ROOT / rel
    if path.is_file():
        return 1
    if not path.is_dir():
        return 0
    return sum(1 for p in path.rglob("*") if p.is_file())


def write_git_memory() -> dict:
    r = subprocess.run(
        ["git", "log", "--format=%h %ad %s", "--date=short"],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )
    body = r.stdout or ""
    commits = [ln for ln in body.splitlines() if ln.strip()]
    GIT_MEMORY.parent.mkdir(parents=True, exist_ok=True)
    GIT_MEMORY.write_text(
        "# ذاكرة C1 المضغوطة — سجل git\n\n"
        "هذا ليس عشر سنوات حرفياً. هذا كل ما عاشه Cursor في هذا المستودع، مضغوطاً.\n"
        "الهضم يتم عبر SHA256+skim. ليس صبّاً في Cognitive WAL.\n\n"
        + "\n".join(f"- `{ln}`" for ln in commits)
        + "\n",
        encoding="utf-8",
    )
    return {"path": ".ai-os/learning/C1-GIT-MEMORY.md", "commits": len(commits), "bytes": GIT_MEMORY.stat().st_size}


def probe_ollama() -> dict:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=1) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return {"present": True, "models": [m.get("name") for m in data.get("models") or []]}
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
        return {"present": False, "note": "Ollama lives on Repair Windows in MODEL-REGISTRY, not on this cloud VM."}


def probe_hf_public() -> dict:
    try:
        req = urllib.request.Request(
            "https://huggingface.co/api/models?pipeline_tag=feature-extraction&sort=downloads&limit=3",
            headers={"User-Agent": "raios-c5-hunt/1"},
        )
        with urllib.request.urlopen(req, timeout=6) as resp:
            rows = json.loads(resp.read().decode("utf-8"))
        ids = [r.get("modelId") or r.get("id") for r in rows[:3] if isinstance(r, dict)]
        return {
            "reachable": True,
            "catalog_only": True,
            "loaded": False,
            "ids": ids,
            "why_not_loaded": "No torch/transformers. CONFIDENTIAL default. Local inverted index is faster here.",
        }
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as err:
        return {"reachable": False, "loaded": False, "error": type(err).__name__}


def hunt() -> dict:
    t0 = time.perf_counter()
    wal_before = WAL.stat().st_mtime if WAL.exists() else None
    git_mem = write_git_memory()
    ollama = probe_ollama()
    hf = probe_hf_public()
    bins = {name: bool(which(name)) for name in ("python3", "git", "rg", "curl", "jq", "gh", "node")}
    rec = {
        "schema": "raios.c5-hunt.v1",
        "from": "C5",
        "parent": "C1",
        "ts": utc(),
        "paid_api": False,
        "wal_written": False,
        "gl005_proven": False,
        "fastest_local": "sha256+skim+inverted-index+git-log",
        "discovered": [
            {"id": "python-stdlib", "use": "hashlib json pathlib re collections — absorb/mind/index", "cost": 0},
            {"id": "git-log", "use": "compressed C1 memory", "commits": git_mem["commits"], "cost": 0},
            {"id": "handoffs", "files": count_files(".ai-os/handoffs"), "use": "inherit C1 experience", "cost": 0},
            {"id": "receipts", "files": count_files(".ai-os/receipts"), "use": "fail-closed evidence", "cost": 0},
            {"id": "experience-pending-validation", "files": count_files(".ai-os/experience/pending-validation"), "use": "cases not A15 pending", "cost": 0},
            {"id": "ripgrep", "present": bins["rg"], "use": "millisecond corpus scan", "cost": 0},
            {"id": "gh-readonly", "present": bins["gh"], "use": "mail collect, not write", "cost": 0},
            {"id": "mcp-8787", "use": "eight V1 tools already live on this VM", "cost": 0},
            {"id": "numpy", "present": True, "use": "unused; hashlib is the right tool for digest", "cost": 0},
        ],
        "invented": [
            {"id": "permanent-grant", "path": ".ai-os/mcp/C5-GRANT.json"},
            {"id": "digest-plane", "path": ".ai-os/learning/DIGESTS.jsonl"},
            {"id": "inverted-index", "path": ".ai-os/learning/INDEX.json"},
            {"id": "five-consult", "path": ".ai-os/learning/LAST-CONSULT.md"},
            {"id": "summon-codes", "path": ".ai-os/summon/SESSION.json"},
        ],
        "deferred": [
            {"id": "ollama-deepseek", **ollama, "reason": "ABSENT on this VM; registry points at Repair Windows"},
            {"id": "hf-embeddings", **hf, "reason": "catalog only; do not download; do not send CONFIDENTIAL text"},
        ],
        "bins": bins,
        "git_memory": git_mem,
        "hf_token": Path.home().joinpath(".cache/huggingface/token").exists(),
        "elapsed_ms": round((time.perf_counter() - t0) * 1000.0, 3),
        "law": ["HUNT_FREE_NE_PAID_API", "ABSORB_DIGEST_NE_WAL_DUMP", "C5_INHERITS_C1_EXPERIENCE"],
    }
    wal_after = WAL.stat().st_mtime if WAL.exists() else None
    if wal_before != wal_after:
        raise SystemExit("HUNT_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(rec, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    OUT_MD.write_text(render_md(rec), encoding="utf-8")
    return rec


def render_md(rec: dict) -> str:
    lines = [
        "# صيد الموارد المجانية — C5",
        "",
        f"- الوقت: `{rec.get('ts')}`",
        f"- الأسرع محلياً: `{rec.get('fastest_local')}`",
        f"- API مدفوع: `{rec.get('paid_api')}`",
        f"- `GL005_PROVEN`: `{rec.get('gl005_proven')}`",
        "",
        "## مكتشف",
        "",
    ]
    for item in rec.get("discovered") or []:
        lines.append(f"- `{item.get('id')}` {json.dumps({k: v for k, v in item.items() if k != 'id'}, ensure_ascii=False)}")
    lines += ["", "## مخترع", ""]
    for item in rec.get("invented") or []:
        lines.append(f"- `{item.get('id')}` `{item.get('path')}`")
    lines += ["", "## مؤجّل", ""]
    for item in rec.get("deferred") or []:
        lines.append(f"- `{item.get('id')}` present={item.get('present', item.get('reachable'))} — {item.get('reason')}")
    lines.append("")
    return "\n".join(lines)


def main() -> int:
    rec = hunt()
    print(json.dumps({"from": "C5", "fastest": rec["fastest_local"], "paid_api": False, "gl005_proven": False, "ms": rec["elapsed_ms"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
