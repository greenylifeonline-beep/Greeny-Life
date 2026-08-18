"""Idle-compute scheduler. Foreground always wins."""
from __future__ import annotations

from typing import Any

from .curriculum import Curriculum
from .resource_governor import ResourceGovernor
from .subconscious import SubconsciousBrain


class Scheduler:
    def __init__(self, governor: ResourceGovernor, subconscious: SubconsciousBrain, curriculum: Curriculum) -> None:
        self.governor = governor
        self.subconscious = subconscious
        self.curriculum = curriculum

    def tick(self, foreground_busy: bool) -> dict[str, Any]:
        if foreground_busy:
            self.governor.enter("FOREGROUND_PRIORITY")
            return {"mode": self.governor.mode, "background": False}
        self.governor.release_foreground()
        if not self.governor.allow_background():
            return {"mode": self.governor.mode, "background": False}
        cycle = self.subconscious.cycle()
        nxt = self.curriculum.next_mission()
        return {"mode": self.governor.mode, "background": True, "cycle": cycle, "next_mission": nxt}
