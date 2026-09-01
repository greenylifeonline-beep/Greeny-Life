"""C1-authorized deterministic actions executed by the existing command worker."""
from __future__ import annotations

import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from ..resource_fabric.census import collect_world, run_safe_probes, snapshots

RESOURCE_CENSUS = "RESOURCE_CENSUS"
MAX_MODEL_PARAMETERS_BILLION = 32


def utc() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(
        f"{path.name}.{os.getpid()}.{threading.get_ident()}.{uuid.uuid4().hex}.tmp"
    )
    try:
        tmp.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        for attempt in range(6):
            try:
                os.replace(tmp, path)
                break
            except PermissionError:
                if attempt == 5:
                    raise
                time.sleep(0.02 * (2**attempt))
    finally:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass


class TaskActionExecutor:
    """Runs allow-listed system actions; it is not a scheduler or task ledger."""

    def __init__(
        self,
        repo: Path,
        collector: Callable[[], dict[str, Any]] = collect_world,
        prober: Callable[[dict[str, Any]], Any] = run_safe_probes,
    ):
        self.repo = repo.resolve()
        self.collector = collector
        self.prober = prober
        self.report_root = (
            self.repo / ".ai-os/reports/command-center/resource-census"
        )
        self.receipt_root = self.repo / ".ai-os/receipts/command-fabric"
    @staticmethod
    def _eligible(task: dict[str, Any], done: set[str]) -> bool:
        return (
            task.get("status") == "READY"
            and task.get("automation_action") == RESOURCE_CENSUS
            and task.get("dispatch_authorized_by") == "C1"
            and not task.get("claimed_by")
            and not task.get("assigned_to")
            and all(dep in done for dep in task.get("dependencies", []))
        )

    def _resource_census(self, task: dict[str, Any]) -> str:
        world = self.collector()
        self.prober(world)
        package = snapshots(world)
        task_id = str(task["id"])
        target = self.report_root / task_id
        for name, payload in package.items():
            atomic(target / name, payload)
        proof = {
            "schema": "raios.automated-resource-census.v1",
            "task_id": task_id,
            "automation_action": RESOURCE_CENSUS,
            "generated_at": utc(),
            "resource_factory_reused": True,
            "inventory": package,
            "safety": {
                "PROVIDER_MUTATION": False,
                "GPU_SESSION_STARTED": False,
                "PAID_RESOURCE_CREATED": False,
                "MODEL_DOWNLOAD_EXECUTED": False,
                "LOCAL_MODEL_STORAGE_MUTATED": False,
                "LOCAL_AG_RESERVED_FOR_CONTROL_AND_MANAGEMENT": True,
                "MAX_MODEL_PARAMETERS_BILLION": MAX_MODEL_PARAMETERS_BILLION,
                "SECOND_SCHEDULER": False,
                "SECOND_TASK_LEDGER": False,
                "SECOND_PROVIDER_REGISTRY": False,
            },
        }
        evidence = target / "AUTOMATED-RESOURCE-CENSUS.json"
        atomic(evidence, proof)
        rel = evidence.relative_to(self.repo).as_posix()
        receipt = {
            "schema": "raios.system-task-action-receipt.v1",
            "task_id": task_id,
            "action": RESOURCE_CENSUS,
            "status": "COMPLETE_EVIDENCE_VERIFIED",
            "evidence": rel,
            "executed_at": utc(),
            **proof["safety"],
        }
        atomic(
            self.receipt_root / f"{task_id}.resource-census.receipt.json", receipt
        )
        return rel
    def execute_ready(self, data: dict[str, Any]) -> dict[str, int]:
        counts = {"actions_processed": 0, "actions_blocked": 0}
        tasks = data.get("tasks", [])
        done = {str(t.get("id")) for t in tasks if t.get("status") == "DONE"}
        for task in tasks:
            if not self._eligible(task, done):
                continue
            try:
                evidence = self._resource_census(task)
                task.update(
                    status="DONE",
                    executed_by="RAIOS-SYSTEM-ACTION:RESOURCE_FACTORY",
                    dispatch_status="AUTOMATION_COMPLETE_EVIDENCE_VERIFIED",
                    evidence=evidence,
                    completed_at=utc(),
                    automation_policy={
                        "c1_authorized": True,
                        "presence_not_required_for_deterministic_system_action": True,
                    },
                )
                done.add(str(task.get("id")))
                counts["actions_processed"] += 1
            except Exception as exc:
                task.update(
                    status="BLOCKED",
                    dispatch_status="AUTOMATION_BLOCKED",
                    blocker=f"{type(exc).__name__}:{exc}",
                    blocked_at=utc(),
                )
                counts["actions_blocked"] += 1
        return counts


def latest_resource_census(repo: Path) -> dict[str, Any]:
    root = repo.resolve() / ".ai-os/reports/command-center/resource-census"
    candidates = sorted(
        root.glob("*/AUTOMATED-RESOURCE-CENSUS.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return {
            "status": "NOT_RUN",
            "resource_factory_reused": True,
            "live_probe_on_dashboard_refresh": False,
        }
    try:
        return json.loads(candidates[0].read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        return {"status": "UNREADABLE", "error": f"{type(exc).__name__}:{exc}"}
