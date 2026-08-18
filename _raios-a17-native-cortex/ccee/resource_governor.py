"""Foreground always wins. Idle-compute modes are bounded."""
from __future__ import annotations

import os
from typing import Any, Literal

Mode = Literal["FOREGROUND_PRIORITY", "LIGHT_LEARNING", "NORMAL_LEARNING", "DEEP_REPLAY", "EVOLUTION_EXPERIMENT"]


class ResourceGovernor:
    def __init__(self) -> None:
        self.mode: Mode = "LIGHT_LEARNING"
        self.foreground_held = False

    def snapshot(self) -> dict[str, Any]:
        load1, _, _ = os.getloadavg() if hasattr(os, "getloadavg") else (0.0, 0.0, 0.0)
        ram = None
        try:
            ram = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
        except (ValueError, OSError, AttributeError):
            ram = None
        return {
            "cpu_load": load1,
            "ram_bytes": ram,
            "gpu": "UNKNOWN",
            "mode": self.mode,
            "foreground_held": self.foreground_held,
        }

    def enter(self, mode: Mode) -> Mode:
        if self.foreground_held and mode != "FOREGROUND_PRIORITY":
            self.mode = "FOREGROUND_PRIORITY"
            return self.mode
        if mode == "FOREGROUND_PRIORITY":
            self.foreground_held = True
        self.mode = mode
        return self.mode

    def release_foreground(self) -> None:
        self.foreground_held = False
        snap = self.snapshot()
        load = float(snap["cpu_load"] or 0)
        if load > 4:
            self.mode = "LIGHT_LEARNING"
        elif load > 1:
            self.mode = "NORMAL_LEARNING"
        else:
            self.mode = "DEEP_REPLAY"

    def allow_background(self) -> bool:
        return not self.foreground_held and self.mode != "FOREGROUND_PRIORITY"

    def allow_high_risk(self) -> bool:
        return False
