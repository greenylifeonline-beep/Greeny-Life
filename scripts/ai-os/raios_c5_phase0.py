#!/usr/bin/env python3
"""Phase Zero: RAIOS world-class discovery and execution map. Not a new kernel. Not GL-005."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from raios_c5_foundation import load_foundation  # noqa: E402
from raios_c5_p0 import ASSIMILATION_CHAIN, GATE_ORDER, stamp as p0_stamp  # noqa: E402
from raios_c5_train import KEEPERS  # noqa: E402

WAL = ROOT / "RAIOS" / "V9" / "wal" / "cognitive-events.jsonl"
OUT = ROOT / ".ai-os" / "receipts" / "c5-phase0"
REPORT_JSON = ROOT / ".ai-os" / "reports" / "RAIOS-PHASE-ZERO-MAP.json"
REPORT_MD = ROOT / ".ai-os" / "reports" / "RAIOS-PHASE-ZERO-MAP.md"

WORLD_CLASS_IS = (
    "ONE_LIVE_PRODUCT_PATH",
    "ONE_AUTHENTICATED_ORCHESTRATION_PATH",
    "ONE_LEARNING_AUTHORITY_COGNITIVE_WAL",
    "FAIL_CLOSED_EVIDENCE",
    "C5_HYBRID_THEN_SOURCE_INDEPENDENT_ASSIMILATION",
    "THREE_COMPANY_BRAINS_UNDER_GOVERNANCE",
    "ZERO_PAID_API",
    "ENTROPY_REDUCTION_NOT_FOREST_GROWTH",
)
WORLD_CLASS_IS_NOT = (
    "CI_PASS_AS_INTELLIGENCE",
    "NINETY_DAY_EMPIRE",
    "TWENTY_TWO_PHASE_ARCHIVE_REVIVAL",
    "CLONE_ODOO_CELERP_AG2_LIGHTRAG",
    "LANGCHAIN_OPENAI_CHROMA_FAISS_DIFY",
    "NINETY_THREE_STUDY_STUBS",
    "SECOND_WAL_OR_MCP_TOOL",
    "MILL_MS_AS_LEARNING",
    "SOURCE_DELETION_ON_ASSUMED_ASSIMILATION",
    "PRINTED_PASS_AS_EVIDENCE",
)
REJECT = (
    ("Celerp", "CELERP_NE_LIVE_ERP", "prisma/schema.prisma + app/api"),
    ("AG2/AutoGen", "AG2_NE_RAIOS_COUNCIL", ".ai-os/mcp + council seats"),
    ("LightRAG", "LIGHTRAG_NE_COGNITIVE_WAL", "DIGESTS/INDEX + Cognitive WAL + greenlines_brain/graph.py"),
    ("LangChain/OpenAI/Chroma/FAISS/Dify/Flowise", "HUNT_FREE_NE_PAID_API", "INDEX + NeuroLingua + mind-fill"),
    ("93 study_*.py", "NAMED_SCRIPT_NE_EXISTING_SCRIPT", "live C5 keepers"),
)
BRAINS = (
    {
        "id": "GREENY_LIFE_EGYPT",
        "keepers": (
            "lib/intelligence/greeny-life-egypt-brain.ts",
            "app/api/brains/greeny-life-egypt/route.ts",
            "tests/greeny_life_egypt_brain_check.ts",
        ),
        "gaps": (),
        "http": "/api/brains/greeny-life-egypt",
    },
    {
        "id": "GREENS_NATURE_UAE",
        "keepers": ("lib/intelligence/three-operating-brains.ts",),
        "gaps": (
            "lib/intelligence/greens-nature-uae-brain.ts",
            "app/api/brains/greens-nature-uae/route.ts",
            "tests/greens_nature_uae_brain_check.ts",
        ),
        "http": "/api/brains/greens-nature-uae",
    },
    {
        "id": "GREEN_LINES_NORWAY_EU",
        "keepers": (
            "greenlines_brain/kernel.py",
            "greenlines_brain/graph.py",
            "lib/intelligence/three-operating-brains.ts",
        ),
        "gaps": (
            "lib/intelligence/greenlines-norway-brain.ts",
            "app/api/brains/greenlines-norway/route.ts",
            "tests/greenlines_norway_brain_check.ts",
        ),
        "http": "/api/brains/green-lines-norway-eu",
    },
)
PACKS = (
    "RAIOS-COGNITIVE-BOOT.json",
    "_raios-qwen-forensics/reports/QWEN36-FORENSIC-CERTIFICATION.json",
    "_raios-a17-native-cortex/cortex/runtime/MAIN-CORTEX-BINDING.json",
)
LAWS = [
    "PHASE_ZERO_MAP_NE_NEW_KERNEL",
    "PHASE_ZERO_MAP_NE_GL005",
    "ORGANIZE_BEFORE_EXPAND",
    "CI_PASS_NE_ASSIMILATION",
    "CI_PASS_NE_GL005",
    "REUSE_BEFORE_BUILD",
    "HOLD_NE_THROW",
]


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def wal_mtime():
    return WAL.stat().st_mtime if WAL.exists() else None


def git_head() -> str:
    r = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, capture_output=True)
    return (r.stdout or "").strip()


def exists(rel: str) -> bool:
    return (ROOT / rel).is_file() or (ROOT / rel).is_dir()


def http_code(path: str) -> int | None:
    req = urllib.request.Request(
        "http://127.0.0.1:3000" + path,
        method="GET",
        headers={"User-Agent": "raios-c5-phase0/1"},
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            return int(resp.status)
    except urllib.error.HTTPError as exc:
        return int(exc.code)
    except Exception:
        return None


def host() -> dict:
    ram_gb = None
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                ram_gb = round(int(line.split()[1]) / (1024 ** 2), 2)
                break
    except OSError:
        ram_gb = None
    return {
        "head": git_head(),
        "ram_gb": ram_gb,
        "gpu": Path("/dev/nvidia0").exists(),
        "database_url": bool(os.environ.get("DATABASE_URL", "").strip()),
        "app_session_secret": bool(os.environ.get("APP_SESSION_SECRET", "").strip()),
        "hf_token": bool(os.environ.get("HF_TOKEN", "").strip()),
        "c1_cortex_run": bool(os.environ.get("C1_CORTEX_RUN", "").strip()),
        "c1_login_email": bool(os.environ.get("C1_LOGIN_EMAIL", "").strip()),
    }


def brain_row(spec: dict) -> dict:
    keepers = [{"path": p, "exists": exists(p)} for p in spec["keepers"]]
    gaps = [{"path": p, "exists": exists(p)} for p in spec["gaps"]]
    code = http_code(spec["http"])
    gap_open = any(not g["exists"] for g in gaps) if gaps else False
    if code == 401:
        http_class = "CAPABILITY_PROTECTED"
    elif code == 404:
        http_class = "CAPABILITY_ABSENT"
    elif code == 500:
        http_class = "CAPABILITY_UNAVAILABLE"
    elif isinstance(code, int) and 200 <= code < 300:
        http_class = "HTTP_2XX_NE_SEMANTIC_SUCCESS"
    else:
        http_class = "UNPROVEN"
    return {
        "id": spec["id"],
        "keepers": keepers,
        "gaps": gaps,
        "gap_open": gap_open,
        "http": spec["http"],
        "http_code": code,
        "classification": http_class,
        "fill_from_this_slice": False,
    }


def execution_ladder(p0: dict) -> list[dict]:
    g1, g2, g3 = p0["gate1"], p0["gate2"], p0["gate3"]
    return [
        {
            "id": "Z",
            "name": "PHASE_ZERO_MAP",
            "status": "DONE_DISCOVERED",
            "meaning": "inventory + ordered execution; not a new kernel",
            "keeper": "python3 scripts/ai-os/raios_c5_phase0.py",
            "blocks": [],
        },
        {
            "id": "0.1",
            "name": GATE_ORDER[0],
            "status": g1["status"],
            "meaning": "live authenticated POST /api/tasks creates visible OrchestrationTask row",
            "keeper": "python3 scripts/ai-os/raios_c5_p0.py",
            "requires": ["existing DATABASE_URL", "legitimate login / session authenticated=true"],
            "forbids": ["mint APP_SESSION_SECRET", "forge gl_session", "provision-admin as proof", "mock/unit-test as proof"],
            "flip": "AUTHENTICATED_ORCHESTRATION_TASK=true still GL005_PROVEN=false",
        },
        {
            "id": "0.2",
            "name": GATE_ORDER[1],
            "status": g2["status"],
            "stop": g2.get("stop_stage"),
            "meaning": " → ".join(ASSIMILATION_CHAIN),
            "keeper": "python3 scripts/ai-os/raios_c5_p0.py",
            "requires": ["qwen3.6:35b-a3b loaded", "granite loaded", "C5 independent pack after isolate"],
            "forbids": ["treat qwen2.5:0.5b as source", "delete weights", "skip SOURCE_PRESENT"],
            "flip": "EXTRACTED_QWEN_GRANITE=true only after full chain",
        },
        {
            "id": "0.3",
            "name": GATE_ORDER[2],
            "status": g3["status"],
            "meaning": "routing + association + execution + persistence + reuse",
            "keeper": "python3 scripts/ai-os/raios_c5_p0.py",
            "requires": ["0.1 PASS", "0.2 PASS"],
            "forbids": ["PASS_CANDIDATE as GL005_PROVEN", "this Cursor claiming GL-005"],
            "flip": "GL005_PROVEN still requires C1/allowed-agent review",
        },
        {
            "id": "1",
            "name": "WAL_BIND_PRODUCT_EXPERIENCES",
            "status": "FORBIDDEN_UNTIL_P0",
            "meaning": "workflow/integrity/task-orchestration → one cognitive event each; no second bus",
            "keeper": "existing RAIOS/V9 WAL after P0; A15 lock remains",
            "requires": ["0.1", "0.2", "0.3 or C1 burst grant"],
            "forbids": ["second WAL", "mutate A15 while LOCK-20260818130148 ACTIVE without grant"],
        },
        {
            "id": "2",
            "name": "GL003_UAE_NORWAY_NEXT",
            "status": "GAP_OTHER_AGENT",
            "meaning": "UAE/Norway Next routes remain open; Python Norway brain already exists",
            "keeper": "GL-003 claimed by deepseek-local",
            "forbids": ["fill UAE/Norway Next routes from this Cursor slice"],
        },
        {
            "id": "3",
            "name": "SLEEPLESS_CRON_ON_MAIN",
            "status": "BLOCKED_NEEDS_C1_MERGE",
            "meaning": "c5-week.yml exists on this branch; GitHub cron fires only from default main",
            "keeper": ".github/workflows/c5-week.yml",
        },
        {
            "id": "4",
            "name": "CORTEX_C1_TREAT_RUN_THROW",
            "status": "HOLD",
            "meaning": "identity qwen3.6:35b-a3b stays; this host HOST_NO_GPU",
            "keeper": "python3 scripts/ai-os/raios_c5_qwen.py --cortex",
            "forbids": ["executor throw", "swap to 0.5b identity"],
        },
    ]


def render_md(rec: dict) -> str:
    p0 = rec["p0"]
    g1, g2, g3 = p0["gate1"], p0["gate2"], p0["gate3"]
    lines = [
        "# PHASE ZERO — RAIOS WORLD-CLASS DISCOVERY & EXECUTION MAP",
        "",
        f"- Decision: `D-061` (DISCOVERED, not CANONICAL). Foundation remains `D-059` / P0 `D-060`.",
        f"- HEAD: `{rec['host']['head']}`",
        f"- Stamp: `{rec['ts']}`",
        f"- Runner: `python3 scripts/ai-os/raios_c5_phase0.py`",
        f"- `GL005_PROVEN=false` `EXTRACTED_QWEN_GRANITE=false` `SAFE_TO_REMOVE_SOURCE=false`",
        "",
        "## What world-class means here",
        "",
        "World-class RAIOS is entropy reduction on one live path: product + authenticated orchestration + C5 mind + one Cognitive WAL. It is not a 22-phase archive, not a 90-day empire, and not CI-as-intelligence.",
        "",
        "IS:",
        *[f"- `{item}`" for item in WORLD_CLASS_IS],
        "",
        "IS NOT:",
        *[f"- `{item}`" for item in WORLD_CLASS_IS_NOT],
        "",
        "## Locked facts (D-059 still binds)",
        "",
        "```text",
        rec["text"].rstrip(),
        "```",
        "",
        "## Discovery — live this host",
        "",
        f"- RAM ~`{rec['host']['ram_gb']}Gi`. GPU=`{str(rec['host']['gpu']).lower()}`. `DATABASE_URL`=`{str(rec['host']['database_url']).lower()}`. `C1_CORTEX_RUN`={'true' if rec['host']['c1_cortex_run'] else 'false'}.",
        f"- Product Next `:3000`: session authenticated=`{g1['session'].get('authenticated')}`. GET `/api/tasks`=`{g1['before'].get('code')}`. POST unauth=`{g1['unauthenticated_post'].get('code')}`. Path=`product` mock=`false`.",
        f"- C5 screen `:8765` present in inventory. Live answer = INDEX + file-read + NeuroLingua. Cortex identity `qwen3.6:35b-a3b` is named, not bound.",
        f"- Ollama models: `{','.join(g2['sources']['models']) or 'none'}`. Student is not the source. `QWEN_GRANITE_SOURCE_PRESENT={str(g2['sources']['source_present']).lower()}`.",
        f"- Transferred packs: " + ", ".join(f"`{p['path']}`={'yes' if p['exists'] else 'no'}" for p in rec["packs"]) + ".",
        "",
        "### Three company brains",
        "",
        "| Brain | Keepers | Gap | HTTP | Class | Fill here |",
        "|---|---|---|---|---|---|",
    ]
    for b in rec["brains"]:
        lines.append(
            f"| `{b['id']}` | {sum(1 for k in b['keepers'] if k['exists'])}/{len(b['keepers'])} | "
            f"{'open' if b['gap_open'] else 'closed'} | `{b['http_code']}` | `{b['classification']}` | no |"
        )
    lines += [
        "",
        "Egypt HTTP 401 = protected capability, not missing. UAE/Norway HTTP 404 = Next route absent (GL-003). Norway Python keepers exist. Do not fill GL-003 from this Cursor slice.",
        "",
        "### Live C5 keepers",
        "",
        *[f"- `{row['name']}` → `{row['path']}`" + ("" if row.get("exists") else " (missing)") for row in rec["keepers"]],
        "",
        "### Rejected as world-class substitutes",
        "",
        "| Claim | Law | Live keeper |",
        "|---|---|---|",
        *[f"| {n} | `{law}` | `{keep}` |" for n, law, keep in REJECT],
        "",
        "## Execution map — fail-closed, no skip",
        "",
        "```mermaid",
        "flowchart TD",
        "  Z[Z Phase Zero map DISCOVERED] --> A[0.1 Authenticated OrchestrationTask]",
        "  A --> B[0.2 Qwen/Granite source-independent assimilation]",
        "  B --> C[0.3 GL005 brain behavior]",
        "  C --> D[1 WAL bind product experiences]",
        "  D --> E[2 GL-003 UAE/Norway Next other agent]",
        "  D --> F[3 c5-week cron on main]",
        "  D --> G[4 Cortex C1 treat/run/throw]",
        "```",
        "",
    ]
    for step in rec["execution"]:
        extra = f" stop=`{step['stop']}`" if step.get("stop") else ""
        lines.append(f"### {step['id']} `{step['name']}` — `{step['status']}`{extra}")
        lines.append("")
        lines.append(step["meaning"])
        if step.get("keeper"):
            lines.append(f"- Keeper: `{step['keeper']}`")
        if step.get("requires"):
            lines.append("- Requires: " + "; ".join(f"`{x}`" for x in step["requires"]))
        if step.get("forbids"):
            lines.append("- Forbids: " + "; ".join(f"`{x}`" for x in step["forbids"]))
        if step.get("flip"):
            lines.append(f"- Flip: `{step['flip']}`")
        lines.append("")
    lines += [
        "## Required from C1 / Repair (this slice cannot mint)",
        "",
        "1. Existing `DATABASE_URL` + legitimate login so `GET /api/auth/session` is `authenticated=true`, then live `POST /api/tasks`.",
        "2. Load cortex `qwen3.6:35b-a3b` and Granite on a capable host. Do not substitute `qwen2.5:0.5b`.",
        "3. After the assimilation chain, C1 re-evaluates `SAFE_TO_REMOVE_SOURCE`. Executor never throws.",
        "4. Merge `c5-week.yml` to default `main` if sleepless cron is wanted.",
        "5. Do not order source deletion or brain downsizing on CI green.",
        "",
        "## Stop / next",
        "",
        f"- `STOP={rec['stop']}`",
        f"- `NEXT={rec['next']}`",
        "- This map does not close GL-005 and does not authorize deletion.",
        "",
    ]
    return "\n".join(lines)


def render_kv(rec: dict) -> str:
    p0 = rec["p0"]
    return "\n".join(
        [
            "############################################################",
            "# RAIOS PHASE ZERO — WORLD-CLASS DISCOVERY & EXECUTION MAP",
            "############################################################",
            f"HEAD={rec['host']['head'][:12] if rec['host']['head'] else 'unknown'}",
            "DECISION=D-061",
            "FOUNDATION=D-059",
            "P0=D-060",
            "PHASE_ZERO_MAP_NE_NEW_KERNEL=true",
            "PHASE_ZERO_MAP_NE_GL005=true",
            "CI_PASS_NE_ASSIMILATION=true",
            "CI_PASS_NE_GL005=true",
            "AUTHENTICATED_ORCHESTRATION_TASK=false",
            f"GATE1={p0['gate1']['status']}",
            "EXTRACTED_QWEN_GRANITE=false",
            f"GATE2_STOP={p0['gate2']['stop_stage']}",
            "SAFE_TO_REMOVE_SOURCE=false",
            "SOURCE_DELETED=false",
            "GL005_PROVEN=false",
            f"GATE3={p0['gate3']['status']}",
            f"EGYPT_HTTP={next(b['http_code'] for b in rec['brains'] if b['id']=='GREENY_LIFE_EGYPT')}",
            f"UAE_HTTP={next(b['http_code'] for b in rec['brains'] if b['id']=='GREENS_NATURE_UAE')}",
            f"NORWAY_HTTP={next(b['http_code'] for b in rec['brains'] if b['id']=='GREEN_LINES_NORWAY_EU')}",
            f"GPU={str(rec['host']['gpu']).lower()}",
            f"STOP={rec['stop']}",
            f"NEXT={rec['next']}",
            "############################################################",
            "",
        ]
    )


def stamp() -> dict:
    wal_before = wal_mtime()
    foundation = load_foundation()
    p0 = p0_stamp()
    rec = {
        "schema": "raios.phase0-map.v1",
        "knowledge_state": "DISCOVERED",
        "canonical": False,
        "from": "C2",
        "parent": "C1",
        "decision": "D-061",
        "foundation_decision": "D-059",
        "p0_decision": "D-060",
        "ts": utc(),
        "host": host(),
        "facts": foundation["facts"],
        "world_class_is": list(WORLD_CLASS_IS),
        "world_class_is_not": list(WORLD_CLASS_IS_NOT),
        "reject": [{"claim": n, "law": law, "keeper": k} for n, law, k in REJECT],
        "keepers": [{"name": n, "path": p, "exists": exists(p)} for n, p in KEEPERS],
        "brains": [brain_row(spec) for spec in BRAINS],
        "packs": [{"path": p, "exists": exists(p)} for p in PACKS],
        "p0": {
            "stop": p0["stop"],
            "gate1": p0["gate1"],
            "gate2": p0["gate2"],
            "gate3": p0["gate3"],
            "authenticated_orchestration_task": p0["authenticated_orchestration_task"],
            "extracted_qwen_granite": False,
            "gl005_proven": False,
        },
        "execution": execution_ladder(p0),
        "stop": p0["stop"],
        "next": "AUTHENTICATED_ORCHESTRATION_TASK;THEN_QWEN_GRANITE_ASSIMILATION;THEN_GL005",
        "law": LAWS,
        "gl005_proven": False,
        "extracted_qwen_granite": False,
        "safe_to_remove_source": False,
        "source_deleted": False,
        "new_kernel": False,
        "wal_written": False,
        "ok": True,
    }
    rec["canonical"] = False
    rec["text"] = render_kv(rec)
    rec["markdown"] = render_md(rec)
    rec["ok"] = (
        rec["gl005_proven"] is False
        and rec["extracted_qwen_granite"] is False
        and rec["safe_to_remove_source"] is False
        and rec["source_deleted"] is False
        and rec["new_kernel"] is False
        and rec["facts"]["GL005_PROVEN"] is False
        and rec["execution"][0]["name"] == "PHASE_ZERO_MAP"
        and rec["execution"][1]["name"] == GATE_ORDER[0]
        and rec["execution"][2]["name"] == GATE_ORDER[1]
        and rec["execution"][3]["name"] == GATE_ORDER[2]
    )
    if wal_mtime() != wal_before:
        raise SystemExit("PHASE0_WAL_VIOLATION")
    rec["wal_mtime_unchanged"] = True
    OUT.mkdir(parents=True, exist_ok=True)
    REPORT_JSON.parent.mkdir(parents=True, exist_ok=True)
    public = {k: v for k, v in rec.items() if k not in {"markdown", "p0"}}
    public["p0"] = {
        "stop": rec["p0"]["stop"],
        "authenticated_orchestration_task": False,
        "extracted_qwen_granite": False,
        "gl005_proven": False,
        "gate1_status": rec["p0"]["gate1"]["status"],
        "gate2_status": rec["p0"]["gate2"]["status"],
        "gate2_stop": rec["p0"]["gate2"]["stop_stage"],
        "gate3_status": rec["p0"]["gate3"]["status"],
        "models": rec["p0"]["gate2"]["sources"]["models"],
        "mock": rec["p0"]["gate1"]["mock"],
    }
    (OUT / "LAST.json").write_text(json.dumps(public, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "LAST.txt").write_text(rec["text"], encoding="utf-8")
    REPORT_JSON.write_text(json.dumps(public, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    REPORT_MD.write_text(rec["markdown"], encoding="utf-8")
    return rec


def main() -> int:
    rec = stamp()
    print(rec["text"], end="")
    print(f"MAP={REPORT_MD}")
    return 0 if rec["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
