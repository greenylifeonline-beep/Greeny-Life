from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


SCRIPT = Path(__file__).resolve()
V9 = SCRIPT.parents[1]
REPO = V9.parents[1]

CONTINUITY = V9 / "continuity"
EXPERIENCE = V9 / "experience"
EVIDENCE = V9 / "evidence"
EVOLUTION = V9 / "evolution"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO,
        text=True,
        capture_output=True,
    )

    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip())

    return result.stdout.strip()


def current_head() -> str:
    return git("rev-parse", "HEAD")


def current_branch() -> str:
    return git("branch", "--show-current")


# ============================================================
# CONTINUITY / STARTUP GATE
# ============================================================

def startup_gate() -> dict:

    checks = []

    def add(name, passed, evidence):
        checks.append({
            "check": name,
            "passed": bool(passed),
            "evidence": evidence,
        })

    identity_path = CONTINUITY / "RAIOS-IDENTITY.json"
    state_path = CONTINUITY / "RAIOS-CURRENT-STATE.json"
    task_path = CONTINUITY / "RAIOS-CURRENT-TASK.json"

    add("repository_found", REPO.exists(), str(REPO))
    add("identity_found", identity_path.exists(), str(identity_path))
    add("current_state_found", state_path.exists(), str(state_path))
    add("current_task_found", task_path.exists(), str(task_path))

    identity = load_json(identity_path) if identity_path.exists() else {}
    state = load_json(state_path) if state_path.exists() else {}
    task = load_json(task_path) if task_path.exists() else {}

    observed_head = current_head()

    recognized_sha = (
        state.get("repository_sha_observed") == observed_head
        or identity.get("repository_sha_observed") == observed_head
    )

    add(
        "repository_sha_recognized",
        recognized_sha,
        {
            "current": observed_head,
            "identity": identity.get("repository_sha_observed"),
            "state": state.get("repository_sha_observed"),
        },
    )

    add(
        "architecture_version_known",
        bool(identity.get("architecture_generation")),
        identity.get("architecture_generation"),
    )

    add(
        "active_phase_known",
        bool(state.get("current_phase")),
        state.get("current_phase"),
    )

    add(
        "current_task_known",
        bool(task.get("task")),
        task.get("task"),
    )

    certified = all(item["passed"] for item in checks)

    return {
        "schema": "raios.startup-gate.v1",
        "timestamp": utc_now(),
        "context_certified": certified,
        "write_permission": "ALLOWED_V9_SCOPE_ONLY" if certified else "DENIED",
        "checks": checks,
    }


# ============================================================
# EXPERIENCE CAPTURE
# ============================================================

def capture_experience(
    intent: str,
    observations: list[str] | None = None,
    tools: list[str] | None = None,
    failures: list[str] | None = None,
    corrections: list[str] | None = None,
    lessons: list[str] | None = None,
    evidence: list[str] | None = None,
    result_status: str = "RECORDED",
    plan: list[str] | None = None,
) -> dict:

    timestamp = utc_now()

    seed = json.dumps({
        "timestamp": timestamp,
        "intent": intent,
        "head": current_head(),
    }, sort_keys=True)

    experience_id = sha256_text(seed)

    record = {
        "schema": "raios.experience.v9",
        "experience_id": experience_id,
        "timestamp": timestamp,

        "intent": intent,

        "context": {
            "repository": str(REPO),
            "branch": current_branch(),
            "repository_sha": current_head(),
            "v9_phase": "V9.0-A",
        },

        "plan": plan or [],

        "tools": tools or [],

        "observations": observations or [],

        "failures": failures or [],

        "corrections": corrections or [],

        "result": {
            "status": result_status,
        },

        "evidence": evidence or [],

        "lesson": lessons or [],

        "reusability": {
            "assessment": "UNASSESSED",
            "repeat_count": 1,
            "candidate_for_compilation": False,
        },

        "skill_candidate": None,

        "status": "PENDING_VALIDATION",
    }

    output = EXPERIENCE / "pending" / f"{experience_id}.json"
    write_json(output, record)

    return record


# ============================================================
# READING
# ============================================================

def classify_source(path: Path) -> str:

    suffix = path.suffix.lower()

    if suffix in {".ts", ".tsx", ".js", ".jsx", ".py", ".ps1"}:
        return "CODE"

    if suffix == ".json":
        return "JSON"

    if suffix in {".md", ".txt"}:
        return "DOCUMENT"

    if suffix in {".log", ".jsonl"}:
        return "LOG"

    return "UNKNOWN"


def read_source(relative_path: str) -> dict:

    path = (REPO / relative_path).resolve()

    try:
        path.relative_to(REPO.resolve())
    except ValueError:
        raise ValueError("READ_OUTSIDE_REPOSITORY_DENIED")

    if not path.exists():
        raise FileNotFoundError(relative_path)

    if not path.is_file():
        raise ValueError("NOT_A_FILE")

    source_type = classify_source(path)

    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    result = {
        "schema": "raios.read-result.v1",
        "path": str(path.relative_to(REPO)),
        "type": source_type,
        "size_bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    }

    if source_type == "CODE":

        result["structural_signals"] = {
            "imports": len(
                re.findall(
                    r"^\s*(?:import|from|require\()",
                    text,
                    re.MULTILINE,
                )
            ),

            "exports": len(
                re.findall(
                    r"\bexport\b|module\.exports",
                    text,
                )
            ),

            "functions": len(
                re.findall(
                    r"\b(?:def|function|class|async\s+function)\b",
                    text,
                )
            ),

            "possible_side_effects": len(
                re.findall(
                    r"writeFile|unlink|remove|delete|update|POST|PUT|PATCH",
                    text,
                    re.IGNORECASE,
                )
            ),
        }

    elif source_type == "JSON":

        try:
            data = json.loads(text)

            if isinstance(data, dict):
                result["top_level_keys"] = sorted(data.keys())
            elif isinstance(data, list):
                result["array_length"] = len(data)

        except Exception as exc:
            result["json_parse_error"] = str(exc)

    result["preview"] = text[:4000]

    return result


# ============================================================
# SEARCH
# ============================================================

def search_repository(query: str, limit: int = 100) -> dict:

    matches = []

    excluded_parts = {
        ".git",
        "node_modules",
        ".next",
        "_raios-kaggle-census",
    }

    query_lower = query.lower()

    for root, dirs, files in os.walk(REPO):

        dirs[:] = [
            d for d in dirs
            if d not in excluded_parts
        ]

        for filename in files:

            path = Path(root) / filename

            try:
                relative = str(path.relative_to(REPO))

                if query_lower in filename.lower():
                    matches.append({
                        "path": relative,
                        "kind": "FILENAME",
                    })

                if len(matches) >= limit:
                    break

                if path.suffix.lower() not in {
                    ".ts", ".tsx", ".js", ".jsx",
                    ".py", ".ps1", ".json",
                    ".md", ".txt", ".jsonl"
                }:
                    continue

                text = path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )

                if query_lower in text.lower():
                    matches.append({
                        "path": relative,
                        "kind": "CONTENT",
                    })

                if len(matches) >= limit:
                    break

            except Exception:
                continue

        if len(matches) >= limit:
            break

    return {
        "schema": "raios.search-result.v1",
        "query": query,
        "count": len(matches),
        "matches": matches[:limit],
    }


# ============================================================
# COMPARISON
# ============================================================

def compare_files(left: str, right: str) -> dict:

    left_path = REPO / left
    right_path = REPO / right

    left_hash = hashlib.sha256(left_path.read_bytes()).hexdigest()
    right_hash = hashlib.sha256(right_path.read_bytes()).hexdigest()

    return {
        "schema": "raios.compare-result.v1",
        "left": left,
        "right": right,
        "left_sha256": left_hash,
        "right_sha256": right_hash,
        "identical": left_hash == right_hash,
        "left_size": left_path.stat().st_size,
        "right_size": right_path.stat().st_size,
    }


# ============================================================
# BACKGROUND EVOLUTION
# ============================================================

def evolve_once() -> dict:

    timestamp = utc_now()

    pending = sorted(
        (EXPERIENCE / "pending").glob("*.json")
    )

    candidates = []

    for path in pending:

        try:
            record = load_json(path)

            if (
                record.get("lesson")
                and record.get("intent")
            ):

                candidates.append({
                    "experience_id":
                        record["experience_id"],

                    "intent":
                        record["intent"],

                    "lesson_count":
                        len(record.get("lesson", [])),

                    "status":
                        "REVIEW_REQUIRED",
                })

        except Exception:
            continue

    report = {
        "schema": "raios.evolution-pass.v1",
        "timestamp": timestamp,

        "mode":
            "BACKGROUND_CANDIDATE_GENERATION_ONLY",

        "canonical_mutation":
            False,

        "pending_experiences":
            len(pending),

        "candidate_count":
            len(candidates),

        "candidates":
            candidates,
    }

    output = (
        EVOLUTION /
        "reports" /
        f"evolution-{timestamp.replace(':','-')}.json"
    )

    write_json(output, report)

    return report


# ============================================================
# CONTEXT
# ============================================================

def context():

    output = {
        "identity":
            load_json(
                CONTINUITY /
                "RAIOS-IDENTITY.json"
            ),

        "state":
            load_json(
                CONTINUITY /
                "RAIOS-CURRENT-STATE.json"
            ),

        "task":
            load_json(
                CONTINUITY /
                "RAIOS-CURRENT-TASK.json"
            ),

        "startup_gate":
            startup_gate(),
    }

    print(
        json.dumps(
            output,
            indent=2,
            ensure_ascii=False,
        )
    )


# ============================================================
# CLI
# ============================================================

def main():

    parser = argparse.ArgumentParser(
        prog="raios-v9"
    )

    sub = parser.add_subparsers(
        dest="command",
        required=True,
    )

    sub.add_parser("context")
    sub.add_parser("doctor")
    sub.add_parser("evolve-once")

    read_parser = sub.add_parser("read")
    read_parser.add_argument("path")

    search_parser = sub.add_parser("search")
    search_parser.add_argument("query")
    search_parser.add_argument(
        "--limit",
        type=int,
        default=100,
    )

    compare_parser = sub.add_parser("compare")
    compare_parser.add_argument("left")
    compare_parser.add_argument("right")

    capture_parser = sub.add_parser("capture")
    capture_parser.add_argument("intent")
    capture_parser.add_argument(
        "--lesson",
        action="append",
        default=[],
    )
    capture_parser.add_argument(
        "--observation",
        action="append",
        default=[],
    )
    capture_parser.add_argument(
        "--tool",
        action="append",
        default=[],
    )
    capture_parser.add_argument(
        "--evidence",
        action="append",
        default=[],
    )

    args = parser.parse_args()

    if args.command == "context":
        context()

    elif args.command == "doctor":
        print(
            json.dumps(
                startup_gate(),
                indent=2,
                ensure_ascii=False,
            )
        )

    elif args.command == "read":
        print(
            json.dumps(
                read_source(args.path),
                indent=2,
                ensure_ascii=False,
            )
        )

    elif args.command == "search":
        print(
            json.dumps(
                search_repository(
                    args.query,
                    args.limit,
                ),
                indent=2,
                ensure_ascii=False,
            )
        )

    elif args.command == "compare":
        print(
            json.dumps(
                compare_files(
                    args.left,
                    args.right,
                ),
                indent=2,
                ensure_ascii=False,
            )
        )

    elif args.command == "capture":

        record = capture_experience(
            intent=args.intent,
            observations=args.observation,
            tools=args.tool,
            lessons=args.lesson,
            evidence=args.evidence,
        )

        print(
            json.dumps(
                record,
                indent=2,
                ensure_ascii=False,
            )
        )

    elif args.command == "evolve-once":
        print(
            json.dumps(
                evolve_once(),
                indent=2,
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
