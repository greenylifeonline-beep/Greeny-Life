from __future__ import annotations

import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(r"C:\Users\Ghanam\Documents\Codex\Greeny-Life-Repair").resolve()

OUT_ROOT = REPO / "_raios-wave2-gap-resolution"
REPORTS = OUT_ROOT / "reports"
REPORTS.mkdir(parents=True, exist_ok=True)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def git(*args: str) -> str:
    p = subprocess.run(
        ["git", *args],
        cwd=REPO,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if p.returncode != 0:
        raise RuntimeError(
            f"GIT_FAILED::{args}::{p.returncode}::{p.stderr.strip()}"
        )
    return p.stdout.strip()


def rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO))
    except Exception:
        return str(path)


branch = git("branch", "--show-current")
head = git("rev-parse", "HEAD")
root = git("rev-parse", "--show-toplevel").replace("\\", "/")

if Path(root).resolve() != REPO:
    raise RuntimeError(f"WRONG_REPOSITORY::{root}")

audit_hits = list(REPO.rglob("WAVE2-RESURRECTION-AUDIT.json"))

if len(audit_hits) != 1:
    raise RuntimeError(
        f"AUTHORITATIVE_AUDIT_COUNT_INVALID::{len(audit_hits)}"
    )

audit_path = audit_hits[0]

with audit_path.open("r", encoding="utf-8-sig") as f:
    audit = json.load(f)

audit_head = audit["repository"]["head"]
audit_hash = sha256_file(audit_path)

gl004 = audit["missions"]["GL-004"]
gl005 = audit["missions"]["GL-005"]

missing_gl004_signals = [
    x["path"]
    for x in gl004["signals"]
    if not x["exists"]
]

missing_gl005_signals = [
    x["path"]
    for x in gl005["signals"]
    if not x["exists"]
]

SEARCH_TERMS = {
    "gl004": [
        "GL-004",
        "gl-004",
        "runtime trace",
        "runtime_trace",
        "runtime-trace",
        "prove execution truth",
    ],
    "gl005": [
        "GL-005",
        "gl-005",
        "Unified Orchestrator",
        "unified orchestrator",
        "orchestration demonstrated",
        "task orchestration",
        "runtime orchestrator",
    ],
}

EXTENSIONS = {
    ".json", ".jsonl", ".md", ".txt", ".py",
    ".ps1", ".ts", ".tsx", ".js", ".yaml", ".yml"
}

EXCLUDED_PARTS = {
    ".git",
    "node_modules",
    ".next",
    "__pycache__",
    ".venv",
    "venv",
}

files = []

for path in REPO.rglob("*"):
    if not path.is_file():
        continue

    if any(part in EXCLUDED_PARTS for part in path.parts):
        continue

    if path.suffix.lower() not in EXTENSIONS:
        continue

    files.append(path)


def search_terms(terms):
    hits = []

    for path in files:
        try:
            text = path.read_text(
                encoding="utf-8",
                errors="replace",
            )
        except Exception:
            continue

        matched = []

        lower = text.lower()

        for term in terms:
            if term.lower() in lower:
                matched.append(term)

        if matched:
            hits.append({
                "path": rel(path),
                "matched_terms": sorted(set(matched)),
                "bytes": path.stat().st_size,
                "sha256": sha256_file(path),
            })

    return hits


gl004_hits = search_terms(SEARCH_TERMS["gl004"])
gl005_hits = search_terms(SEARCH_TERMS["gl005"])

path_candidates = []

for path in REPO.rglob("*"):
    s = str(path).replace("\\", "/").lower()

    if (
        "migration/gl-004" in s
        or "migration/gl-005" in s
        or "gl-004-runtime" in s
        or "gl-005-convergence" in s
    ):
        path_candidates.append({
            "path": rel(path),
            "exists": path.exists(),
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
            "sha256": sha256_file(path)
            if path.is_file()
            else None,
        })

candidate_names = [
    "controlled-runtime-orchestrator.ts",
    "task-orchestration.ts",
    "runtime-trace",
    "workflowEngine.ts",
]

concrete_candidates = []

for path in REPO.rglob("*"):
    if not path.is_file():
        continue

    p = str(path).replace("\\", "/").lower()

    if any(name.lower() in p for name in candidate_names):
        concrete_candidates.append({
            "path": rel(path),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        })

package_path = REPO / "package.json"
package_scripts = {}

if package_path.exists():
    try:
        package = json.loads(
            package_path.read_text(
                encoding="utf-8-sig"
            )
        )
        package_scripts = package.get("scripts", {})
    except Exception as e:
        package_scripts = {
            "_parse_error": repr(e)
        }

test_files = []

tests_root = REPO / "tests"

if tests_root.exists():
    for path in tests_root.rglob("*"):
        if path.is_file():
            test_files.append(rel(path))

retired_archive_hits = []

archive_root = REPO / "archive" / "retired-worktree-preservation"

if archive_root.exists():
    for path in archive_root.rglob("*"):
        s = str(path).replace("\\", "/").lower()

        if (
            "gl-004-runtime" in s
            or "gl-005-convergence" in s
        ):
            retired_archive_hits.append({
                "path": rel(path),
                "is_file": path.is_file(),
                "is_dir": path.is_dir(),
                "sha256": sha256_file(path)
                if path.is_file()
                else None,
            })

observations = []

observations.append({
    "claim": "GL004_SIGNAL_GAP",
    "status": "OBSERVED",
    "value": missing_gl004_signals,
})

observations.append({
    "claim": "GL005_SIGNAL_GAP",
    "status": "OBSERVED",
    "value": missing_gl005_signals,
})

observations.append({
    "claim": "GL004_SEMANTIC_VALIDATION_CONTRACT",
    "status": "OBSERVED",
    "value": next(
        (
            x["validation"]
            for x in audit["wave2_tasks"]
            if x["id"] == "GL-004"
        ),
        None,
    ),
})

observations.append({
    "claim": "GL005_SEMANTIC_VALIDATION_CONTRACT",
    "status": "OBSERVED",
    "value": next(
        (
            x["validation"]
            for x in audit["wave2_tasks"]
            if x["id"] == "GL-005"
        ),
        None,
    ),
})

report = {
    "schema": "raios.wave2.targeted-gap-resolution.v1",
    "repository": {
        "root": str(REPO),
        "branch": branch,
        "head_current": head,
        "audit_head": audit_head,
        "head_matches_audit": head == audit_head,
    },
    "authoritative_audit": {
        "path": str(audit_path),
        "sha256": audit_hash,
    },
    "signal_gaps": {
        "GL-004": missing_gl004_signals,
        "GL-005": missing_gl005_signals,
    },
    "observations": observations,
    "estate": {
        "gl004_textual_hits": gl004_hits,
        "gl005_textual_hits": gl005_hits,
        "migration_and_retired_path_candidates": path_candidates,
        "concrete_runtime_orchestration_candidates": concrete_candidates,
        "retired_archive_hits": retired_archive_hits,
        "package_scripts": package_scripts,
        "test_files": test_files,
    },
    "invariants": {
        "signal_gap_is_not_capability_gap": True,
        "path_absence_is_not_capability_absence": True,
        "presence_is_not_execution_proof": True,
        "no_new_implementation_before_estate_resolution": True,
    },
    "safety": {
        "production_source_mutation": False,
        "merge": False,
        "delete": False,
        "canonical_promotion": False,
    },
    "next": "SEMANTICALLY_CLASSIFY_GL004_GL005_EXISTING_CAPABILITIES",
    "created_at": datetime.now(timezone.utc).isoformat(),
}

report_path = REPORTS / "WAVE2-TARGETED-GAP-RESOLUTION.json"

report_path.write_text(
    json.dumps(
        report,
        indent=2,
        ensure_ascii=False,
    ),
    encoding="utf-8",
)

report_hash = sha256_file(report_path)

print("")
print("############################################################")
print("# RAIOS WAVE2 TARGETED GAP RESOLUTION")
print("############################################################")

print(f"REPOSITORY={REPO}")
print(f"BRANCH={branch}")
print(f"CURRENT_HEAD={head}")
print(f"AUDIT_HEAD={audit_head}")
print(f"HEAD_MATCHES_AUDIT={str(head == audit_head).upper()}")

print("")
print(f"AUDIT={audit_path}")
print(f"AUDIT_SHA256={audit_hash}")

print("")
print(
    "GL004_SIGNAL_GAP="
    + ",".join(missing_gl004_signals)
)
print(
    "GL005_SIGNAL_GAP="
    + ",".join(missing_gl005_signals)
)

print("")
print(f"GL004_ESTATE_HITS={len(gl004_hits)}")
print(f"GL005_ESTATE_HITS={len(gl005_hits)}")
print(f"PATH_CANDIDATES={len(path_candidates)}")
print(f"CONCRETE_CANDIDATES={len(concrete_candidates)}")
print(f"RETIRED_ARCHIVE_HITS={len(retired_archive_hits)}")
print(f"TEST_FILES={len(test_files)}")

print("")
print("SIGNAL_GAP_IS_CAPABILITY_GAP=FALSE")
print("PATH_ABSENCE_IS_CAPABILITY_ABSENCE=FALSE")
print("PRESENCE_IS_EXECUTION_PROOF=FALSE")

print("")
print(f"REPORT={report_path}")
print(f"REPORT_SHA256={report_hash}")

print("")
print("DELETE=FALSE")
print("MERGE=FALSE")
print("CANONICAL_PROMOTION=FALSE")
print("NEXT=CLASSIFY_EXISTING_GL004_GL005_CAPABILITY_EVIDENCE")
print("STATUS=TARGETED_ESTATE_RESOLUTION_COMPLETE")
print("############################################################")
