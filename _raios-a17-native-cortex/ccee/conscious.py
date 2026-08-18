"""Conscious (foreground) brain. User-facing task solving. No background monopoly."""
from __future__ import annotations

from typing import Any

from .config import FailClosed
from .event_bus import EventBus
from .resource_governor import ResourceGovernor


class ConsciousBrain:
    def __init__(self, bus: EventBus, governor: ResourceGovernor) -> None:
        self.bus = bus
        self.governor = governor
        self.busy = False

    def handle_task(self, task: dict[str, Any]) -> dict[str, Any]:
        self.governor.enter("FOREGROUND_PRIORITY")
        self.busy = True
        self.bus.emit("TASK_RECEIVED", "conscious", {"task": task})
        try:
            plan = list(task.get("plan") or ["observe", "act", "verify"])
            result = {
                "ok": bool(task.get("ok", True)),
                "plan": plan,
                "execution_authority": False,
                "teacher_used": False,
            }
            if task.get("fail"):
                self.bus.emit("TASK_FAILED", "conscious", {"task": task, "error": task.get("error") or "TASK_FAILED"})
                raise FailClosed(task.get("error") or "TASK_FAILED")
            self.bus.emit("TASK_COMPLETED", "conscious", {"task_id": task.get("id"), "result": result})
            return result
        finally:
            self.busy = False
            self.governor.release_foreground()
