"""Offline all-hands A2A bind tests. No LLM. No public listener. No mutation."""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

os.environ.setdefault("NO_LLM_CALLS", "true")

from raios.a2a.cards import PUBLIC_AGENT_ID
from raios.a2a.capability import CAPABILITY_NOOP
from raios.a2a.failclosed import DIRECT_EXECUTION_PATH_FORBIDDEN, SEAT_IDENTITY_NOT_PUBLIC_AGENT, FailClosed
from raios.a2a.flags import A2A_EXTERNAL_MUTATION_ALLOWED
from raios.a2a.gateway import A2ARequest
from raios.a2a.semantic import default_contract
from raios.a2a_all_hands.bind import (
    ENVELOPE_FIELDS,
    INTERNAL_SEATS,
    bind_c2,
    c2_semantic_bind,
    guarded_handle,
    reject_internal_seat,
    routing_matrix,
    side_effect_disposition,
    validate_envelope,
)
from raios.command_fabric.route import NATS, select_transport


class AllHandsBindTests(unittest.TestCase):
    def test_internal_seats_are_not_public_agents(self) -> None:
        for seat in INTERNAL_SEATS:
            with self.assertRaises(FailClosed) as ctx:
                reject_internal_seat(seat)
            self.assertEqual(ctx.exception.code, SEAT_IDENTITY_NOT_PUBLIC_AGENT)
            with self.assertRaises(FailClosed) as ctx2:
                guarded_handle(
                    A2ARequest(
                        agent_id=seat,
                        capability_id=CAPABILITY_NOOP,
                        a2a_task_id="t",
                        a2a_context_id="c",
                        desired_state={},
                        idempotency_key="k",
                        semantic_contract=default_contract(),
                    )
                )
            self.assertEqual(ctx2.exception.code, SEAT_IDENTITY_NOT_PUBLIC_AGENT)

    def test_routing_matrix_is_42_directed_pairs(self) -> None:
        matrix = routing_matrix(nats_available=True)
        self.assertEqual(len(matrix), 42)
        pairs = {(row["from"], row["to"]) for row in matrix}
        self.assertEqual(len(pairs), 42)
        for source in INTERNAL_SEATS:
            for dest in INTERNAL_SEATS:
                if source == dest:
                    self.assertNotIn((source, dest), pairs)
                else:
                    self.assertIn((source, dest), pairs)
        self.assertTrue(all(row["public_a2a_agent"] is False for row in matrix))
        self.assertTrue(all(row["direct_mutation"] is False for row in matrix))
        self.assertTrue(all(row["command_fabric_gate"] is True for row in matrix))
        c5_nats = [row for row in matrix if row["to"] == "C5"]
        self.assertTrue(all(row["selected_transport"] == NATS for row in c5_nats))

    def test_c5_falls_back_to_http_when_nats_unavailable(self) -> None:
        route = select_transport(target="C5", nats_available=False)
        self.assertEqual(route["selected_transport"], "HTTP")
        self.assertTrue(route["HTTP_FALLBACK_PRESERVED"])

    def test_side_effects_terminate_at_command_fabric(self) -> None:
        noop = side_effect_disposition(side_effects=False)
        self.assertFalse(noop["DIRECT_MUTATION"])
        gated = side_effect_disposition(side_effects=True)
        self.assertTrue(gated["COMMAND_FABRIC_GATE"])
        self.assertFalse(gated["DIRECT_MUTATION"])
        self.assertFalse(gated["EXECUTED"])
        self.assertIn("command_fabric", gated["TERMINATES_AT"])

    def test_direct_execute_forbidden(self) -> None:
        with self.assertRaises(FailClosed) as ctx:
            guarded_handle(
                A2ARequest(
                    agent_id=PUBLIC_AGENT_ID,
                    capability_id=CAPABILITY_NOOP,
                    a2a_task_id="t",
                    a2a_context_id="c",
                    desired_state={},
                    idempotency_key="k",
                    semantic_contract=default_contract(),
                    direct_execute=True,
                )
            )
        self.assertEqual(ctx.exception.code, DIRECT_EXECUTION_PATH_FORBIDDEN)

    def test_envelope_fields_and_c2_bind(self) -> None:
        self.assertFalse(A2A_EXTERNAL_MUTATION_ALLOWED)
        bind = c2_semantic_bind()
        self.assertTrue(bind["C2_A2A_BOUND"])
        self.assertFalse(bind["DIRECT_EXECUTED"])
        self.assertFalse(bind["EFFECTIVE_AUTHORITY_GRANTED"])
        env = bind["envelope"]
        for key in ENVELOPE_FIELDS:
            self.assertTrue(env.get(key), key)
        validate_envelope(env)
        flags = bind_c2(probe_live=False)
        self.assertTrue(flags["C2_A2A_BOUND"])
        self.assertTrue(flags["ROUTING_MATRIX_42_PAIRS"])
        self.assertTrue(flags["COMMAND_FABRIC_ROUTE"])
        self.assertTrue(flags["NATS_REUSED"])
        self.assertTrue(flags["HTTP_REUSED"])
        self.assertFalse(flags["NEW_BUS_CREATED"])
        self.assertFalse(flags["DIRECT_MUTATION"])
        self.assertEqual(flags["pairs"], 42)


if __name__ == "__main__":
    unittest.main()
