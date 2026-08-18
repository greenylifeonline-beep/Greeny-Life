"""Learning acceleration metrics time series."""
from __future__ import annotations

from typing import Any

from .ledger import Ledger

NAMES = (
    "CapabilityGainPerHour",
    "TimeToCapability",
    "TimeToMastery",
    "LearningAccelerationIndex",
    "ExperienceMultiplicationFactor",
    "CognitiveCompressionRatio",
    "ZeroLLMConversionRate",
    "TeacherDependency",
    "TransferEfficiency",
    "FailureRecurrenceRate",
    "SkillCreationVelocity",
    "AutonomousCurriculumYield",
    "RetentionScore",
    "ComputePerCapabilityGain",
)


class LearningAcceleration:
    def __init__(self, ledger: Ledger) -> None:
        self.ledger = ledger

    def record(self, name: str, value: float, payload: dict[str, Any] | None = None) -> None:
        if name not in NAMES:
            from .config import FailClosed

            raise FailClosed(f"UNKNOWN_METRIC:{name}")
        self.ledger.add_metric(name, value, payload)

    def snapshot(self) -> dict[str, float]:
        rows = self.ledger.conn.execute(
            "SELECT name, value FROM metrics ORDER BY ts"
        ).fetchall()
        out: dict[str, float] = {n: 0.0 for n in NAMES}
        for row in rows:
            out[row["name"]] = float(row["value"])
        return out
