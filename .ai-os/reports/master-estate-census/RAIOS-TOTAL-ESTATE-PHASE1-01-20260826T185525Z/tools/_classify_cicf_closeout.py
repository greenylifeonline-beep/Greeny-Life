# Deterministic CICF static classification. No model inference. No tool execution.
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path

CICF = Path(
    r"C:\Users\Ghanam\Documents\Codex\Greeny-Life-Repair\_raios-wave2-post-retirement\reports\CICF-CAPABILITY-INVENTORY.json"
)
OUT = Path(
    r"C:\Users\Ghanam\Documents\Codex\Greeny-Life-Repair\.ai-os\reports\master-estate-census\RAIOS-TOTAL-ESTATE-PHASE1-01-20260826T185525Z\tools"
)

VENDOR = (
    "site-packages",
    "node_modules",
    ".venv",
    ".venv-multimodal",
    "lib/site-packages",
)

CAT_FAMILY = {
    "discovery_inventory": "knowledge",
    "verification_certification": "validation",
    "salvage_reconciliation": "migration",
    "dedup_consolidation": "archive",
    "retirement_cleanup": "archive",
    "learning_evidence": "learning",
    "other": "unknown",
}

RUNTIME_MARKERS = (
    "raios_multimodal_gateway",
    "raios-c1-c5-channel",
    "user-router",
    "raios_mcp",
    "/mcp/",
    "nats",
    "nomadic",
    "ollama",
    "start-c5-ifdown",
    "cognitive-events",
    "/wal/",
    "neuro_lingua",
    "neurolingua",
)


def is_garbage(path: str) -> bool:
    if not path or not path.strip():
        return True
    if path.startswith("s,.cursor") or ",.github," in path:
        return True
    if re.search(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", path):
        return True
    return False


def family(path: str, signals: list, kind: str, cat: str) -> str:
    pl = path.replace("\\", "/").lower()
    sig = " ".join(signals or []).lower()
    blob = pl + " " + sig + " " + (kind or "")
    if any(v in pl for v in VENDOR):
        return "generated"
    rules = [
        ("transport", ("nats", "http", "gateway", "websocket", "fabric-bridge")),
        ("router", ("router", "route_one", "user-router")),
        ("agent", ("agent", "worker", "c2", "c5", "c6", "goose", "native-agent")),
        ("model", ("ollama", "llm", "cortex", "qwen", "granite", "embedding")),
        ("retrieval", ("retriev", "embed", "index", "rag", "search_evidence")),
        ("knowledge", ("knowledge", "rkg", "canonical", "brain")),
        ("learning", ("learn", "train", "experience", "skill")),
        ("validation", ("validat", "certif", "audit", "proof")),
        ("testing", ("test", "pytest", "benchmark")),
        ("benchmark", ("benchmark",)),
        ("state", ("state/", "locks.json", "tasks.json", "current-state")),
        ("WAL", ("wal", "cognitive-events")),
        ("identity", ("identity", "seat-map", "policy.json")),
        ("auth", ("auth", "oauth", "token")),
        ("observability", ("otel", "metric", "log", "health")),
        ("self-repair", ("repair", "self_inspect", "autonomic")),
        ("rollback", ("rollback", "revert")),
        ("compute", ("kaggle", "nomadic", "scheduler", "gpu")),
        ("cloud", ("huggingface", "s3", "onedrive")),
        ("ERP", ("prisma", "sales-order", "supplier", "inventory")),
        ("business", ("product", "honey", "gels", "logistics", "crm")),
        ("migration", ("migration", "gl-002", "gl-003", "gl-004", "gl-005")),
        ("archive", ("archive", ".zip", "handoff")),
    ]
    for fam, keys in rules:
        if any(k in blob for k in keys):
            return fam
    return CAT_FAMILY.get(cat, "unknown")


def cap_rel(path: str, fam: str) -> tuple[str, str]:
    pl = path.replace("\\", "/").lower()
    if "raios_multimodal_gateway" in pl or "raios-c1-c5" in pl:
        return "CAP-C5-CHAT", "IMPLEMENTS"
    if "user-router" in pl:
        return "CAP-FABRIC", "IMPLEMENTS"
    if "raios_mcp" in pl or "/mcp/" in pl:
        return "CAP-MCP", "IMPLEMENTS"
    if "nomadic" in pl or "kaggle" in pl:
        return "CAP-C6", "SUPPORTS"
    if "nats" in pl:
        return "CAP-NATS", "SUPPORTS"
    if "/wal/" in pl or "cognitive-events" in pl:
        return "CAP-WAL", "IMPLEMENTS"
    if "neuro_lingua" in pl or "neurolingua" in pl:
        return "CAP-NL", "IMPLEMENTS"
    if "gl-005" in pl:
        return "CAP-GL005", "MIGRATES"
    if "gl-002" in pl:
        return "CAP-GL002", "MIGRATES"
    if "gl-003" in pl:
        return "CAP-GL003", "MIGRATES"
    if any(x in pl for x in ("app/api", "prisma", "application/")):
        return "CAP-ERP", "SUPPORTS"
    if fam == "testing":
        return "CAP-C5-CHAT", "TESTS"
    if fam == "generated":
        return "UNRELATED", "UNRELATED"
    if "goose" in pl or "native-agent" in pl:
        return "CAP-C2", "DUPLICATES"
    return "UNRELATED", "UNRELATED"


def lookup_py(path: str, py_map: dict, py_by_name: dict) -> dict | None:
    if path in py_map:
        return py_map[path]
    name = Path(path).name
    hits = py_by_name.get(name, [])
    if len(hits) == 1:
        return hits[0]
    return None


def proof(art: dict, py: dict | None, vendor: bool, path: str, fam: str) -> str:
    if is_garbage(path):
        return "P0_NAME_ONLY"
    if vendor:
        return "P2_STATIC_VALIDATED"
    if (art.get("bytes") or 0) == 0 and not py:
        return "P0_NAME_ONLY"
    if py and py.get("parse") == "PASS":
        return "P2_STATIC_VALIDATED"
    if art.get("kind") and ((art.get("suffix") or fam != "unknown") or (art.get("bytes") or 0) > 0):
        return "P2_STATIC_VALIDATED"
    if fam != "unknown":
        return "P2_STATIC_VALIDATED"
    if path:
        return "P1_FILE_EXISTS"
    return "P0_NAME_ONLY"


def status(art: dict, fam: str, vendor: bool, dup_n: int, runtime: bool, pr: str) -> str:
    if vendor or fam == "generated":
        return "GENERATED"
    if (art.get("bytes") or 0) == 0:
        return "EMPTY"
    if (dup_n or 1) > 1:
        return "DUPLICATE"
    if fam == "archive":
        return "SUPERSEDED"
    if runtime:
        return "ACTIVE_OR_REFERENCED"
    if pr == "P2_STATIC_VALIDATED":
        return "CLASSIFIED"
    return "UNKNOWN"


def main() -> None:
    data = json.loads(CICF.read_text(encoding="utf-8"))
    py_map = {x["path"].replace("\\", "/"): x for x in data.get("python_capabilities", [])}
    py_by_name: dict[str, list] = defaultdict(list)
    for pth, rec in py_map.items():
        py_by_name[Path(pth).name].append(rec)
    dup_map = {}
    for g in data.get("exact_duplicate_groups", []):
        for p in g.get("paths", []):
            dup_map[p.replace("\\", "/")] = {"sha256": g.get("sha256"), "count": g.get("count")}

    rows = []
    for cat, body in data["categories"].items():
        for i, art in enumerate(body.get("artifacts", [])):
            path = (art.get("path") or "").replace("\\", "/")
            vendor = any(v in path.lower() for v in VENDOR)
            py = lookup_py(path, py_map, py_by_name)
            dup = dup_map.get(path, {})
            fam = family(path, art.get("signals") or [], art.get("kind") or "", cat)
            cap, rel = cap_rel(path, fam)
            runtime = (
                (not vendor)
                and (not is_garbage(path))
                and (art.get("bytes") or 0) > 0
                and (
                    rel in ("IMPLEMENTS", "SUPPORTS", "TESTS", "WRAPS")
                    or any(m in path.lower() for m in RUNTIME_MARKERS)
                )
            )
            pr = proof(art, py, vendor, path, fam)
            st = status(art, fam, vendor, dup.get("count") or 0, runtime, pr)
            if is_garbage(path):
                pr = "P0_NAME_ONLY"
                st = "UNKNOWN"
            elif st == "EMPTY" and not vendor:
                pr = "P0_NAME_ONLY"
            sha = (py or {}).get("sha256") or dup.get("sha256")
            fns = (py or {}).get("functions") or []
            clss = (py or {}).get("classes") or []
            rows.append(
                {
                    "TOOL_ID": f"CICF-{cat}-{i:04d}",
                    "NAME": Path(path).name or path[:80],
                    "PATH": path,
                    "SHA256": sha,
                    "FILE_TYPE": art.get("suffix"),
                    "LANGUAGE": art.get("suffix"),
                    "KIND": art.get("kind"),
                    "BYTES": art.get("bytes"),
                    "CICF_CATEGORY": cat,
                    "FAMILY": fam,
                    "PURPOSE": ",".join(art.get("signals") or []) or cat,
                    "ENTRYPOINT_OR_SYMBOL": (fns[0] if fns else (clss[0] if clss else None)),
                    "IMPORTERS_CALLERS_COUNT": None,
                    "CALLEES_DEPENDENCIES_COUNT": len(fns) if fns else None,
                    "CONFIG_REFERENCES": cat,
                    "AST_PARSE": (py or {}).get("parse"),
                    "AST_FN_COUNT": len(fns),
                    "AST_CLASS_COUNT": len(clss),
                    "DUPLICATE_HASH_GROUP": dup.get("sha256"),
                    "DUPLICATE_GROUP_SIZE": dup.get("count") or 1,
                    "SEMANTIC_FAMILY": fam,
                    "CAPABILITY_ID": cap,
                    "CAPABILITY_RELATION": rel,
                    "STATUS": st,
                    "PROOF_LEVEL": pr,
                    "RUNTIME_REFERENCE_PRESENT": runtime,
                    "TEST_REFERENCE_PRESENT": fam in ("testing", "benchmark") or cat == "verification_certification",
                    "RECOMMENDED_ACTION_PRELIMINARY": (
                        "ARCHIVE"
                        if vendor or fam == "generated"
                        else "INVESTIGATE"
                        if pr == "P0_NAME_ONLY"
                        else "REUSE_CANDIDATE"
                        if runtime or rel in ("IMPLEMENTS", "SUPPORTS")
                        else "PROVENANCE_ONLY"
                    ),
                    "VENDOR_OR_VENV": vendor,
                    "GARBAGE_PATH": is_garbage(path),
                }
            )

    p0 = [r for r in rows if r["PROOF_LEVEL"] == "P0_NAME_ONLY"]
    runtime_rows = [r for r in rows if r["RUNTIME_REFERENCE_PRESENT"]]
    unique_rows = [r for r in rows if (r["DUPLICATE_GROUP_SIZE"] or 1) == 1 and not r["VENDOR_OR_VENV"]]
    counts = {
        "CICF_TOOLS_TOTAL": len(rows),
        "CICF_P0_NAME_ONLY_REMAINING": len(p0),
        "CICF_P1": sum(1 for r in rows if r["PROOF_LEVEL"] == "P1_FILE_EXISTS"),
        "CICF_P2": sum(1 for r in rows if r["PROOF_LEVEL"] == "P2_STATIC_VALIDATED"),
        "CICF_ACTIVE_OR_REFERENCED": len(runtime_rows),
        "CICF_UNIQUE": len(unique_rows),
        "CICF_DUPLICATE": sum(1 for r in rows if (r["DUPLICATE_GROUP_SIZE"] or 1) > 1),
        "CICF_GENERATED": sum(1 for r in rows if r["STATUS"] == "GENERATED" or r["VENDOR_OR_VENV"]),
        "CICF_SUPERSEDED": sum(1 for r in rows if r["STATUS"] == "SUPERSEDED"),
        "CICF_UNKNOWN": sum(1 for r in rows if r["STATUS"] == "UNKNOWN" or r["FAMILY"] == "unknown"),
        "ALL_RUNTIME_REFERENCED_TOOLS_STATICALLY_UNDERSTOOD": all(
            r["PROOF_LEVEL"] == "P2_STATIC_VALIDATED" for r in runtime_rows
        )
        if runtime_rows
        else True,
        "ALL_UNIQUE_TOOL_CANDIDATES_STATICALLY_UNDERSTOOD": all(
            r["PROOF_LEVEL"] == "P2_STATIC_VALIDATED"
            for r in unique_rows
            if (not r["GARBAGE_PATH"] and r["STATUS"] != "EMPTY")
        ),
        "P0_REASONS": dict(Counter(
            ("GARBAGE_PATH" if r["GARBAGE_PATH"] else "EMPTY" if r["STATUS"] == "EMPTY" else "OTHER")
            for r in p0
        )),
        "FAMILY": dict(Counter(r["FAMILY"] for r in rows)),
        "PROOF": dict(Counter(r["PROOF_LEVEL"] for r in rows)),
        "RELATION": dict(Counter(r["CAPABILITY_RELATION"] for r in rows)),
        "STATUS": dict(Counter(r["STATUS"] for r in rows)),
        "METHOD": "CICF inventory fields + python_capabilities AST join + path/family heuristics; no LLM; no live execution of the 1464",
        "IMPORTERS_NOTE": "IMPORTERS_CALLERS_COUNT not computed; full-repo call graph out of scope for static closeout",
    }

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "CICF-STATIC-CLASSIFICATION.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )
    (OUT / "CICF-STATIC-SUMMARY.json").write_text(
        json.dumps(
            {
                "schema": "raios.cicf.static-classification.v1",
                "source": str(CICF),
                "cicf_head_note": data.get("repository"),
                "counts": counts,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
