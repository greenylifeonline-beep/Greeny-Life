from __future__ import annotations

from .models import TaskState

TASK_TRANSITIONS = {
    TaskState.CREATED: {TaskState.ADMITTED, TaskState.CANCELLED, TaskState.FAILED},
    TaskState.ADMITTED: {TaskState.LEASED, TaskState.BLOCKED, TaskState.CANCELLED, TaskState.FAILED},
    TaskState.LEASED: {TaskState.RUNNING, TaskState.BLOCKED, TaskState.CANCELLED, TaskState.FAILED},
    TaskState.RUNNING: {TaskState.VERIFYING, TaskState.BLOCKED, TaskState.FAILED, TaskState.CANCELLED},
    TaskState.VERIFYING: {TaskState.COMPLETED, TaskState.FAILED, TaskState.RUNNING},
    TaskState.BLOCKED: {TaskState.ADMITTED, TaskState.LEASED, TaskState.CANCELLED, TaskState.FAILED},
    TaskState.COMPLETED: set(),
    TaskState.FAILED: set(),
    TaskState.CANCELLED: set(),
}
