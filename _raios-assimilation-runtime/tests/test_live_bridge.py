from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
RUNTIME = REPO / "_raios-assimilation-runtime"
sys.path.insert(0, str(REPO / "_raios-a17-native-cortex"))
sys.path.insert(0, str(REPO / "_raios-a17-integration-wave" / "src"))
sys.path.insert(0, str(REPO / "_raios-a17-cursor-parallel" / "src"))
sys.path.insert(0, str(RUNTIME))

from live_bridge import LiveAssimilationBridge  # noqa: E402


class LiveAssimilationBridgeTests(unittest.TestCase):
    def test_contact_ok(self) -> None:
        bridge = LiveAssimilationBridge()
        try:
            contact = bridge.contact_status()
            self.assertEqual(contact["RAIOS_CONTACT"], "OK")
        finally:
            bridge.close()

    def test_discover_real_engines(self) -> None:
        bridge = LiveAssimilationBridge()
        try:
            engines = bridge.discover_engines()
            names = {e["name"] for e in engines}
            self.assertTrue({"student_loop", "cortex", "execution_fabric"} <= names)
            student = next(e for e in engines if e["name"] == "student_loop")
            self.assertEqual(student["classification"], "FOUND")
            self.assertTrue(student["usable"])
        finally:
            bridge.close()

    def test_execution_fabric_observe_dispatch(self) -> None:
        bridge = LiveAssimilationBridge()
        try:
            fabric = bridge.probe_execution_fabric(task_id="ASIM-TEST")
            self.assertTrue(fabric["observe_dispatch_ok"])
            self.assertIn("COMPLETED", fabric["states"])
        finally:
            bridge.close()

    def test_student_turn_is_real_not_simulated(self) -> None:
        bridge = LiveAssimilationBridge()
        try:
            turn = bridge.ask_student(task_id="ASIM-UNIT-001", intent="find assimilation modules")
            self.assertEqual(turn["actor"], "RAIOS")
            self.assertTrue(turn.get("turn_id"))
            self.assertTrue(turn.get("action_taken"))
            self.assertFalse(turn.get("execution_authority"))
        finally:
            bridge.close()


if __name__ == "__main__":
    unittest.main()
