"""Thin C5 bridge onto the single AI Gateway ModelRouter. Not a second gateway."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from raios.ai_gateway.router import ModelRouter


def _repo_root() -> Path:
    env = os.environ.get("RAIOS_REPO_ROOT")
    if env:
        return Path(env).resolve()
    # src/raios/c5_gateway/model_fabric.py -> repo root
    return Path(__file__).resolve().parents[3]


class C5ModelFabric:
    """Optional cascade when privacy allows cloud and local fails / cloud preferred.

    Keeps student local default. Does not force HOLD main-cortex changes.
    """

    def __init__(self, repo: Path | None = None) -> None:
        self.repo = (repo or _repo_root()).resolve()
        self.router = ModelRouter(self.repo)
        self.student_default = (
            os.getenv("RAIOS_STUDENT_MODEL")
            or os.getenv("RAIOS_MAIN_CORTEX")
            or "qwen3:0.6b"
        )

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        task_class: str = "NORMAL_CHAT",
        privacy_class: str = "local_preferred",
        task_id: str | None = None,
        prefer_cloud: bool = False,
        local_failed: bool = False,
        max_tokens: int = 64,
    ) -> dict[str, Any]:
        privacy = privacy_class
        if prefer_cloud and privacy in {"local_preferred", ""}:
            privacy = "cloud_preferred"
        # Student local remains default unless local failed or cloud explicitly preferred.
        if not local_failed and not prefer_cloud and privacy in {"local_preferred", "local_only", "local_private"}:
            route = self.router.route_for_task_class(
                "HEALTH" if task_class.upper() in {"HEALTH", "ROUTING", "CLASSIFICATION"} else task_class,
                privacy_class="local_only" if privacy != "local_preferred" else "local_preferred",
                seat="C5",
                task_id=task_id,
                dispatch=True,
                messages=messages,
                max_tokens=max_tokens,
            )
            return {
                "schema": "raios.c5.model-fabric.v1",
                "seat": "C5",
                "student_default": self.student_default,
                "main_cortex_forced": False,
                "gateway": route,
                "second_gateway_created": False,
            }

        route = self.router.route_for_task_class(
            task_class,
            privacy,
            seat="C5",
            task_id=task_id,
            dispatch=True,
            messages=messages,
            max_tokens=max_tokens,
        )
        return {
            "schema": "raios.c5.model-fabric.v1",
            "seat": "C5",
            "student_default": self.student_default,
            "main_cortex_forced": False,
            "gateway": route,
            "second_gateway_created": False,
        }
