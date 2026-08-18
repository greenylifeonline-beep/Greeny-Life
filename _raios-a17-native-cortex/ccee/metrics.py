"""Metrics façade over the acceleration time series."""
from __future__ import annotations

from typing import Any

from .learning_acceleration import LearningAcceleration, NAMES


class Metrics:
    def __init__(self, acceleration: LearningAcceleration) -> None:
        self.acceleration = acceleration

    def record(self, name: str, value: float, **payload: Any) -> None:
        self.acceleration.record(name, value, payload or None)

    def snapshot(self) -> dict[str, float]:
        return self.acceleration.snapshot()

    def names(self) -> tuple[str, ...]:
        return NAMES
