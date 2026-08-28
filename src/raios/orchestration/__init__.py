"""Canonical RAIOS orchestration surface."""

from .task_submission import (
    OrchestrationTask,
    TaskSubmissionError,
    authorize_task_capability,
    get_registered_task,
    submit_authenticated_task,
    task_is_registered,
)

__all__ = [
    "OrchestrationTask",
    "TaskSubmissionError",
    "authorize_task_capability",
    "get_registered_task",
    "submit_authenticated_task",
    "task_is_registered",
]
