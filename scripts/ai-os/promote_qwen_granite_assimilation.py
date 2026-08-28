#!/usr/bin/env python3
"""One-shot extract: teacher-harvest text -> compiled capability JSON.

Offline extract tool only. Runtime (assimilated_brain.py) must never import
this module or any _raios-* tree. Does not call models or store weights.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HEADINGS = [
    "CURRENT_OPERATIONAL_TRUTH",
    "HISTORICAL_TRUTHS",
    "CONTRADICTIONS",
    "SAFE_DECISION",
    "GENERAL_RULE",
    "FAILURE_MODES",
    "TEACHABLE_SKILL",
    "ROOT_CAUSE",
    "PROCEDURE",
    "FAILURE_RECOVERY",
    "TRANSFER_EXERCISE",
    "INGESTION_METHOD",
    "KNOWLEDGE_OBJECTS",
    "LINKING_POLICY",
    "CONTRADICTION_POLICY",
    "CRITIQUE_PROCEDURE",
    "QUESTION_SET",
    "FAILURE_PATTERNS",
    "STOP_RULE",
    "STRONG_CAPABILITIES",
    "WEAK_CAPABILITIES",
    "USEFUL_PROCEDURES",
    "COMMON_FAILURES",
    "REUSABLE_PATTERNS",
    "GOOD_PRACTICE_TASKS",
    "GOOD_TRANSFER_TESTS",
    "CURRENT_AUTHORITY",
    "HISTORICAL_EVIDENCE",
    "GENERALIZED_RULE",
    "CONFIDENCE",
]

ALIASES = {
    "GENERALIZED_RULE": "GENERAL_RULE",
    "CURRENT_AUTHORITY": "CURRENT_OPERATIONAL_TRUTH",
    "HISTORICAL_EVIDENCE": "HISTORICAL_TRUTHS",
    "CONFIDENCE": "EVIDENCE",
}

FAMILIES = {
    "qwen2.5-coder:3b": {
        "family": "qwen",
        "teacher_id": "TEACHER_QWEN25_CODER_3B",
        "role": ["CODING", "REPOSITORY_ANALYSIS", "DEBUGGING", "REFACTORING", "TEST_GENERATION"],
        "dir": "qwen2.5-coder-3b",
    },
    "granite4:3b": {
        "family": "granite",
        "teacher_id": "TEACHER_GRANITE4_3B",
        "role": ["GENERALIST", "TEXT_ANALYSIS", "CLASSIFICATION", "SUMMARIZATION", "CRITIQUE"],
        "dir": "granite4-3b",
    },
}

CSI = re.compile(r"\x1b\[([0-9]*)([A-Za-z])")
HEADING_RE = re.compile(
    r"(?m)^\s*(?:#{1,6}\s*)?("
    + "|".join(re.escape(h) for h in sorted(HEADINGS, key=len, reverse=True))
    + r")\s*:?\s*$"
)


def utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def replay_ansi(text: str) -> str:
    out: list[str] = []
    i = 0
    while i < len(text):
        if text.startswith("\x1b[", i):
            m = CSI.match(text, i)
            if m:
                n = int(m.group(1) or "1")
                cmd = m.group(2)
                i = m.end()
                if cmd == "D" and n:
                    del out[max(0, len(out) - n) :]
                continue
        out.append(text[i])
        i += 1
    cleaned = "".join(out)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def split_sections(text: str) -> dict[str, str]:
    matches = list(HEADING_RE.finditer(text))
    sections: dict[str, str] = {}
    for i, m in enumerate(matches):
        key = ALIASES.get(m.group(1), m.group(1))
        body = text[m.end() : matches[i + 1].start() if i + 1 < len(matches) else len(text)].strip()
        sections[key] = (sections.get(key, "") + ("\n" if key in sections else "") + body).strip()
    return sections


def listish(text: str) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for line in (text or "").splitlines():
        line = re.sub(r"^[-*•\d\.\)\s]+", "", line).strip()
        line = re.sub(r"\*\*([^*]+)\*\*", r"\1", line)
        if len(line) < 24:
            continue
        key = " ".join(line.lower().split())
        if key in seen:
            continue
        seen.add(key)
        out.append(line)
    return out


def classify(sections: dict[str, str]) -> dict[str, list[str]]:
    claims, procedures, failures, skills, transfers = [], [], [], [], []
    for k, v in sections.items():
        items = listish(v)
        if any(x in k for x in ["TRUTH", "RULE", "DECISION", "OBJECT", "CAPABILIT"]):
            claims.extend(items)
        if any(x in k for x in ["PROCEDURE", "METHOD", "POLICY", "PATTERN", "PRACTICE"]):
            procedures.extend(items)
        if any(x in k for x in ["FAILURE", "CONTRADICTION", "WEAK"]):
            failures.extend(items)
        if "SKILL" in k or "PATTERN" in k:
            skills.extend(items)
        if "TRANSFER" in k:
            transfers.extend(items)
        if k == "TEACHABLE_SKILL":
            skills.extend(items)
    def d(xs: list[str]) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for x in xs:
            k = x.lower()
            if k not in seen:
                seen.add(k)
                out.append(x)
        return out[:40]
    return {
        "claims": d(claims),
        "procedures": d(procedures),
        "failure_patterns": d(failures),
        "skills": d(skills),
        "transfer_tests": d(transfers),
    }


def ingest_dir(harvest_dir: Path, teachers_dir: Path, spec: dict, model: str) -> dict:
    units: list[dict] = []
    sources: list[dict] = []
    for path in sorted(harvest_dir.glob("*.txt")):
        raw = path.read_bytes()
        digest = sha256_bytes(raw)
        text = replay_ansi(raw.decode("utf-8-sig", errors="replace"))
        meta_path = path.with_suffix(".txt").with_name(path.stem + ".meta.json")
        meta = {}
        if meta_path.exists():
            meta = json.loads(meta_path.read_text(encoding="utf-8-sig"))
        classified = classify(split_sections(text))
        unit = {
            "task_id": meta.get("task_id") or path.stem,
            "capability": meta.get("capability") or path.stem,
            "source_rel": str(path).replace("\\", "/"),
            "source_sha256": digest,
            **classified,
        }
        units.append(unit)
        sources.append({"path": path.name, "sha256": digest, "bytes": len(raw)})
    inv = teachers_dir / "SELF-CAPABILITY-INVENTORY.txt"
    if inv.exists():
        raw = inv.read_bytes()
        digest = sha256_bytes(raw)
        classified = classify(split_sections(replay_ansi(raw.decode("utf-8-sig", errors="replace"))))
        units.append({
            "task_id": "SELF-CAPABILITY-INVENTORY",
            "capability": "TEACHER_SELF_INVENTORY",
            "source_rel": str(inv).replace("\\", "/"),
            "source_sha256": digest,
            **classified,
        })
        sources.append({"path": inv.name, "sha256": digest, "bytes": len(raw)})
    bag = {"claims": [], "procedures": [], "failure_patterns": [], "skills": [], "transfer_tests": []}
    capabilities: list[str] = []
    for unit in units:
        for k in bag:
            for item in unit[k]:
                if item not in bag[k]:
                    bag[k].append(item)
        if unit["capability"] not in capabilities:
            capabilities.append(unit["capability"])
    return {
        "schema": "raios.enterprise-brain.assimilated-family.v1",
        "family": spec["family"],
        "teacher_id": spec["teacher_id"],
        "teacher_model": model,
        "role": spec["role"],
        "canonical_runtime_location": f"intelligence/knowledge_base/assimilated/{spec['family'].upper()}.json",
        "weights_stored": False,
        "source_package_imported": False,
        "unit_count": len(units),
        "capabilities": capabilities,
        "aggregate": {k: v[:60] for k, v in bag.items()},
        "units": units,
        "source_files": sources,
    }


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: promote_qwen_granite_assimilation.py HARVEST_ROOT [DEST]", file=sys.stderr)
        print("extract-only; not a runtime dependency", file=sys.stderr)
        return 2
    harvest_root = Path(sys.argv[1])
    dest = Path(sys.argv[2] if len(sys.argv) > 2 else Path.cwd())
    out_dir = dest / "intelligence" / "knowledge_base" / "assimilated"
    out_dir.mkdir(parents=True, exist_ok=True)
    harvest = harvest_root / "experience" / "raw" / "teacher-harvest"
    teachers = harvest_root / "teachers"
    families = {}
    for model, spec in FAMILIES.items():
        families[spec["family"]] = ingest_dir(harvest / spec["dir"], teachers / spec["dir"], spec, model)
        (out_dir / f"{spec['family'].upper()}.json").write_text(
            json.dumps(families[spec["family"]], indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    index = {
        "schema": "raios.enterprise-brain.assimilated-index.v1",
        "created_at": utc(),
        "compiler": "scripts/ai-os/promote_qwen_granite_assimilation.py",
        "compiler_semantics": "A17.5 a17_5_assimilation.py heading-split/classify",
        "canonical_locations": {
            "qwen": "intelligence/knowledge_base/assimilated/QWEN.json",
            "granite": "intelligence/knowledge_base/assimilated/GRANITE.json",
            "index": "intelligence/knowledge_base/assimilated/INDEX.json",
            "capabilities": "intelligence/knowledge_base/assimilated/CAPABILITIES.json",
            "acceptance": "intelligence/knowledge_base/assimilated/D059-ACCEPTANCE.json",
        },
        "source_package_on_delivery_branch": False,
        "runtime_requires_historical_tree": False,
        "PAID_API": False,
        "MODEL_WEIGHTS_STORED": False,
        "families": {
            name: {
                "teacher_model": rec["teacher_model"],
                "teacher_id": rec["teacher_id"],
                "unit_count": rec["unit_count"],
                "skill_count": len(rec["aggregate"]["skills"]),
                "procedure_count": len(rec["aggregate"]["procedures"]),
                "claim_count": len(rec["aggregate"]["claims"]),
                "file_sha256": sha256_bytes((out_dir / f"{name.upper()}.json").read_bytes()),
            }
            for name, rec in families.items()
        },
    }
    (out_dir / "INDEX.json").write_text(json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"status": "PROMOTED", "index": index["families"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
