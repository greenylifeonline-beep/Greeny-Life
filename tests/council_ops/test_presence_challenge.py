import json
import pytest
from pathlib import Path

from raios.council_ops import CouncilOperations
from raios.council_ops.presence_challenge import PresenceChallengeError


def live_auth(seat):
    return {
        "seat_id": seat,
        "SIGNATURE_VALID": True,
        "ISSUER_IDENTIFIED": True,
        "ISSUER_TRUSTED": True,
        "PRINCIPAL_BOUND": True,
        "AUTHORITY_SOURCE_PROVENANCE": {"issuer": "test", "principal": seat},
        "actor_id": seat + "-ACTOR",
        "origin_instance": seat.lower() + "-session",
        "device_id": "DEV-" + seat,
        "session_id": "SESSION-" + seat,
    }


def setup(tmp_path):
    repo = tmp_path / "repo"
    (repo / ".ai-os/state").mkdir(parents=True)
    (repo / ".ai-os/state/TASKS.json").write_text('{"tasks":[]}', encoding="utf-8")
    (repo / ".ai-os/state/LOCKS.json").write_text('{"locks":[]}', encoding="utf-8")
    return CouncilOperations(repo, tmp_path / "runtime")


def test_challenge_response_creates_verified_attendance_and_binding(tmp_path):
    op = setup(tmp_path)
    challenge = op.challenges.issue("C6", reason="DISCOVERED_LIVE_UNVERIFIED")
    op.challenges.bind_message(challenge["challenge_id"], "MSG-1")
    out = op.respond_presence_challenge(
        seat="C6", challenge_id=challenge["challenge_id"], nonce=challenge["nonce"],
        origin_salt="fresh-salt-from-c6", response_word="fresh-word-from-c6",
        availability="AVAILABLE", auth=live_auth("C6"), idem="respond-c6")
    assert out["status"] == "VERIFIED"
    assert out["presence"] == "PRESENT"
    assert out["attendance_fingerprint"]
    presence = json.loads(op.presence_path.read_text(encoding="utf-8"))
    row = presence["seats"]["C6"]
    assert row["attendance_proof_type"] == "CHALLENGE_RESPONSE"
    assert row["availability_source"] == "SELF_CHALLENGE_RESPONSE"
    binding = json.loads(op.bindings_path.read_text(encoding="utf-8"))["bindings"]["C6"]
    assert binding["session_id"] == "SESSION-C6"


def test_delivery_or_wrong_nonce_cannot_create_presence(tmp_path):
    op = setup(tmp_path)
    challenge = op.challenges.issue("C2", reason="PROCESS_DISCOVERED")
    with pytest.raises(PresenceChallengeError, match="NONCE_MISMATCH"):
        op.respond_presence_challenge(
            seat="C2", challenge_id=challenge["challenge_id"], nonce="wrong",
            origin_salt="fresh-salt", response_word="fresh-word",
            availability="AVAILABLE", auth=live_auth("C2"), idem="bad-c2")
    state = json.loads(op.presence_path.read_text(encoding="utf-8")) if op.presence_path.exists() else {"seats": {}}
    assert "C2" not in state.get("seats", {})


def test_offline_response_creates_departure_fingerprint(tmp_path):
    op = setup(tmp_path)
    challenge = op.challenges.issue("C4", reason="PROBE")
    out = op.respond_presence_challenge(
        seat="C4", challenge_id=challenge["challenge_id"], nonce=challenge["nonce"],
        origin_salt="fresh-offline-salt", response_word="offline-word",
        availability="OFFLINE", auth=live_auth("C4"), idem="offline-c4")
    assert out["presence"] == "ABSENT"
    state = json.loads(op.presence_path.read_text(encoding="utf-8"))
    assert state["seats"]["C4"]["departure_fingerprint"]
