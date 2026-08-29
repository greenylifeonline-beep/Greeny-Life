from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .assimilation import build_curriculum
from .state_import import import_factory_estate


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def runtime_root() -> Path:
    return Path(
        os.getenv(
            "RAIOS_FACTORY_RUNTIME_ROOT",
            str(Path.home() / ".raios" / "runtime" / "factory-fabric"),
        )
    ).expanduser().resolve()


def resource_factory_probe() -> dict[str, Any]:
    from raios.resource_fabric.census import collect_world
    from raios.resource_fabric.factory import evaluate_workload

    world = collect_world()
    control = evaluate_workload("CONTROL", world, request_id="FACTORY-FABRIC-CONTROL")
    model = evaluate_workload("MODEL_FACTORY", world, request_id="FACTORY-FABRIC-MODEL")
    return {
        "factory": "RESOURCE_FACTORY",
        "status": "PASS",
        "control": {
            "result_class": control["decision"]["result_class"],
            "selected_resource": control["decision"]["selected_resource"],
            "dispatch_allowed": control["plan"]["dispatch_allowed"],
            "provider_mutation": control["plan"]["PROVIDER_MUTATION"],
        },
        "model_factory": {
            "result_class": model["decision"]["result_class"],
            "selected_resource": model["decision"]["selected_resource"],
            "dispatch_allowed": model["plan"]["dispatch_allowed"],
            "gpu_session_started": model["plan"]["GPU_SESSION_STARTED"],
            "paid_resource_created": model["plan"]["PAID_RESOURCE_CREATED"],
        },
    }


def training_factory_probe() -> dict[str, Any]:
    root = repo_root()
    runner = root / "scripts" / "runtime" / "verify-training-factory.mjs"
    proc = subprocess.run(
        ["node", str(runner)],
        cwd=root,
        text=True,
        capture_output=True,
        timeout=60,
    )
    if proc.returncode != 0:
        return {
            "factory": "TRAINING_FACTORY",
            "status": "FAIL",
            "returncode": proc.returncode,
            "stderr": proc.stderr[-4000:],
        }
    line = next((x for x in proc.stdout.splitlines() if x.strip().startswith("{")), "")
    try:
        payload = json.loads(line)
    except Exception:
        payload = {"raw_stdout": proc.stdout[-4000:]}
    return {"factory": "TRAINING_FACTORY", "status": "PASS", **payload}


def foundry_probe(max_files: int = 120, case_limit: int = 120) -> dict[str, Any]:
    root = repo_root()
    rt = runtime_root() / "foundry"
    env = dict(os.environ)
    env["RAIOS_FOUNDRY_REPO_ROOT"] = str(root)
    env["RAIOS_FOUNDRY_RUNTIME_ROOT"] = str(rt)
    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "raios.factory_fabric.foundry_engine",
            "run",
            "--max-files",
            str(max_files),
            "--case-limit",
            str(case_limit),
        ],
        cwd=root,
        env=env,
        text=True,
        capture_output=True,
        timeout=300,
    )
    if proc.returncode != 0:
        return {
            "factory": "C5_EXPERT_FOUNDRY",
            "status": "FAIL",
            "returncode": proc.returncode,
            "stdout": proc.stdout[-4000:],
            "stderr": proc.stderr[-4000:],
        }
    try:
        payload = json.loads(proc.stdout)
    except Exception:
        payload = {"raw_stdout": proc.stdout[-4000:]}
    return {
        "factory": "C5_EXPERT_FOUNDRY",
        "status": "PASS",
        "extract": payload.get("extract"),
        "cases": payload.get("cases"),
        "split": payload.get("split"),
        "train": payload.get("train"),
        "blind": payload.get("blind"),
        "promotion": payload.get("promotion"),
        "receipt": payload.get("receipt"),
        "runtime_root": str(rt),
    }


def assimilation_probe() -> dict[str, Any]:
    rt = runtime_root()
    estate = import_factory_estate(rt)
    curriculum = build_curriculum(rt)
    return {
        "factory": "ASSIMILATION_FACTORY",
        "status": "PASS" if curriculum["raw_events"] > 0 else "FAIL_EMPTY_INPUT",
        "estate_source_files": estate["source_file_count"],
        "estate_unique_objects": estate["unique_object_count"],
        "objects_copied": estate["objects_copied"],
        "objects_reused": estate["objects_reused"],
        "raw_events": curriculum["raw_events"],
        "unique_materials": curriculum["unique_materials"],
        "assimilation_units": curriculum["assimilation_units"],
        "capabilities": curriculum["capabilities"],
        "runtime_root": str(rt),
        "manifest": estate["manifest"],
    }


def run_all(*, max_files: int = 120, case_limit: int = 120) -> dict[str, Any]:
    root = repo_root()
    rt = runtime_root()
    rt.mkdir(parents=True, exist_ok=True)

    results = {
        "resource_factory": resource_factory_probe(),
        "assimilation_factory": assimilation_probe(),
        "training_factory": training_factory_probe(),
        "expert_foundry": foundry_probe(max_files=max_files, case_limit=case_limit),
    }
    all_pass = all(str(x.get("status", "")).startswith("PASS") for x in results.values())
    report = {
        "schema": "raios.factory-fabric.run.v1",
        "generated_at": utc(),
        "repo_root": str(root),
        "runtime_root": str(rt),
        "status": "PASS" if all_pass else "FAIL",
        "factories": results,
        "canonical_repo_mutation": False,
        "provider_mutation": False,
        "automatic_canonical_promotion": False,
    }
    report_path = rt / "FACTORY-FABRIC-LATEST.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    report["report_path"] = str(report_path)
    return report


def main() -> int:
    report = run_all()
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0 if report["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
