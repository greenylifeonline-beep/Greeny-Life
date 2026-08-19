from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent
sys.path.insert(0, str(ROOT))

from ccee.config import FailClosed, contains_forbidden_success  # noqa: E402
from ccee.engine import CCEE  # noqa: E402
from ccee.gateway_cert import GatewayChatCertifier, prove_real_chat  # noqa: E402
from ccee.gateway_incident import case_from_incident, execute_incident_probe, load_incident  # noqa: E402
from ccee.root_cause import classify_failure, diagnose  # noqa: E402
from ccee.shadow_lab import ShadowRepairLab  # noqa: E402
from ccee.training_loop import LiveCognitiveLoop  # noqa: E402


class GatewayIncidentTests(unittest.TestCase):
    def test_incident_file_invalidates_live(self) -> None:
        incident = load_incident(REPO)
        self.assertEqual(incident["id"], "GL-GW-001")
        self.assertTrue(incident["certification_invalidated"])
        self.assertEqual(incident["forbidden_live_claim"], "RAIOS_MULTIMODAL_GATEWAY_LIVE")
        emitted = incident["observed"]["script_emitted"]
        self.assertEqual(emitted["STATUS"], "RAIOS_MULTIMODAL_GATEWAY_LIVE")
        self.assertIn("500", incident["observed"]["POST_/v1/chat"])

    def test_current_d4_http500_with_live_is_false_pass(self) -> None:
        incident = load_incident(REPO)
        case = case_from_incident(incident)
        self.assertTrue(case["printed_pass"])
        self.assertEqual(case["http"], 500)
        family = classify_failure(case)
        self.assertEqual(family, "FALSE_PASS")
        self.assertEqual(classify_failure({"http": 500, "failed": True}), "OLLAMA_SERVER_ERROR")

    def test_probe_executes_and_does_not_claim_live(self) -> None:
        probe = execute_incident_probe(REPO)
        self.assertTrue(probe["ok"])
        self.assertTrue(probe["live_claim_rejected"])
        self.assertNotEqual(probe.get("overall_status"), "PASS")
        self.assertTrue(probe["action_taken"])
        self.assertFalse(probe["ollama"]["ok"])
        self.assertIn("LIVE", str(probe["student_claims"]["emitted_status"]))
        self.assertFalse(probe["token_search"]["gateway_source_found_outside_incident_file"])

    def test_attempt_two_strategy_is_evidence_probe(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        ccee = CCEE(Path(tmp.name) / "ccee", repo_root=REPO)
        loop = LiveCognitiveLoop(ccee, REPO)
        t1 = loop.ask_raios(task_id="GL-GW-TEST", intent="diagnose gateway false PASS")
        self.assertEqual((t1.get("result") or {}).get("strategy"), "naive_repo_rg")
        t2 = loop.ask_raios(task_id="GL-GW-TEST", intent="diagnose gateway false PASS")
        self.assertEqual((t2.get("result") or {}).get("strategy"), "incident_evidence_probe")
        diagnosis = (t2.get("result") or {}).get("gateway_diagnosis") or {}
        self.assertEqual(diagnosis.get("d4_family"), "FALSE_PASS")
        self.assertFalse(diagnosis.get("live_status_bypasses_pass_detector"))
        t3 = loop.ask_raios(task_id="GL-GW-TEST", intent="shadow gateway false PASS")
        self.assertEqual((t3.get("result") or {}).get("strategy"), "gateway_shadow_integrity")
        lab = (t3.get("result") or {}).get("gateway_diagnosis") or {}
        self.assertTrue(lab.get("repair_success"))
        self.assertTrue(lab.get("transfer_success"))
        self.assertFalse(lab.get("canonical_promotion"))
        self.assertEqual(lab.get("STATUS"), "NOT_LIVE")
        ccee.close()
        tmp.cleanup()

    def test_certifier_rejects_health_only_live(self) -> None:
        cert = GatewayChatCertifier()
        with self.assertRaises(FailClosed) as ctx:
            cert.certify(health={"http": 200, "ok": True}, chat={"http": 500, "body": ""})
        self.assertIn("CHAT_GATE_FAILED", str(ctx.exception))

    def test_language_transfer_arabic_english_norwegian(self) -> None:
        cert = GatewayChatCertifier()
        with self.assertRaises(FailClosed) as ctx:
            cert.certify(
                health={"http": 200, "ok": True},
                chat={"http": 200, "body": "hello"},
                languages={"arabic": "hello", "english": "hello", "norwegian": "Hei"},
            )
        self.assertIn("LANGUAGE_GATE_FAILED", str(ctx.exception))
        ok = cert.certify(
            health={"http": 200, "ok": True},
            chat={"http": 200, "body": "hello مرحبا Hei hvordan"},
            languages={"arabic": "مرحبا", "english": "hello", "norwegian": "Hei, hvordan går det?"},
        )
        self.assertEqual(ok["overall_status"], "GATES_SATISFIED")
        self.assertEqual(ok["STATUS"], "NOT_LIVE")
        self.assertFalse(contains_forbidden_success(ok["overall_status"]))

    def test_stale_live_plus_nonzero_is_not_certification(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        stale = Path(tmp.name) / "stale.json"
        stale.write_text('{"run_id":"old","STATUS":"RAIOS_MULTIMODAL_GATEWAY_LIVE"}', encoding="utf-8")
        cert = GatewayChatCertifier()
        with self.assertRaises(FailClosed):
            cert.certify(
                health={"http": 200, "ok": True},
                chat={"http": 500, "body": ""},
                stale_live_path=stale,
                run_id="new",
            )
        tmp.cleanup()

    def test_real_chat_fail_closed_without_qwen(self) -> None:
        proof = prove_real_chat()
        self.assertFalse(proof["ok"])
        self.assertEqual(proof["overall_status"], "FAILED")
        self.assertEqual(proof["QWEN_CHAT"], "FAILED")
        self.assertEqual(proof["STATUS"], "NOT_LIVE")

    def test_gateway_shadow_lab_and_graph(self) -> None:
        tmp = tempfile.TemporaryDirectory()
        ccee = CCEE(Path(tmp.name) / "ccee", repo_root=REPO)
        lab = ShadowRepairLab().run_gateway_false_pass_session(Path(tmp.name) / "gw")
        self.assertTrue(lab["repair_success"])
        self.assertTrue(lab["transfer_success"])
        self.assertEqual(lab["shared_principle"], "partial_gate_success_plus_failed_mandatory_gate_cannot_certify")
        graph = diagnose(
            ccee.causal,
            None,
            printed_pass=True,
            error="http=500",
            secondary="live_claim",
        )
        self.assertEqual(graph["family"], "FALSE_PASS")
        self.assertEqual(graph["root_cause"], "false_pass_live_after_failed_chat_gate")
        self.assertEqual(graph["secondary_failure"], "http_500_or_chat_runtime_failure")
        ccee.close()
        tmp.cleanup()


if __name__ == "__main__":
    unittest.main()
