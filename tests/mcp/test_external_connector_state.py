import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts/ai-os"))

from raios_mcp.gateway import Gateway, GatewayError  # noqa: E402


def gateway(tmp_path: Path) -> Gateway:
    return Gateway(root=tmp_path, policy={}, actors={})


def write_contract(root: Path, profile):
    path = root / ".ai-os" / "mcp" / "EXTERNAL-CONNECTOR-CONTRACT.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"external_principal_profiles": profile}),
        encoding="utf-8",
    )


def write_state(root: Path, payload):
    path = root / ".ai-os" / "mcp" / "EXTERNAL-CONNECTORS.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def test_malformed_binding_row_does_not_break_valid_chatgpt_binding(tmp_path):
    digest = "a" * 64
    write_contract(
        tmp_path,
        {
            "CHATGPT_NATIVE": {
                "principal": "CHATGPT_NATIVE_DELEGATE",
                "actor_role": "EXTERNAL_DELEGATED_CLIENT",
                "instance_role": "chatgpt-native",
                "tools": ["get_head"],
                "scopes": ["get_head"],
                "deny": [],
                "seat": False,
            }
        },
    )
    write_state(
        tmp_path,
        {
            "schema": "raios.external-connectors.v1",
            "version": 1,
            "bindings": [
                "historical-corrupt-row",
                {
                    "fingerprint_sha256": digest,
                    "status": "ACTIVE",
                    "connector_id": "CHATGPT_NATIVE",
                    "principal": "CHATGPT_NATIVE_DELEGATE",
                },
            ],
            "pending": [42, None],
        },
    )

    actor = gateway(tmp_path)._actor_from_external_binding(digest)

    assert actor is not None
    assert actor.actor_id == "CHATGPT_NATIVE_DELEGATE"
    assert actor.tools == ["get_head"]
    assert actor.scopes == ["get_head"]


def test_corrupt_connector_json_is_structured_not_internal_error(tmp_path):
    path = tmp_path / ".ai-os" / "mcp" / "EXTERNAL-CONNECTORS.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("{broken", encoding="utf-8")

    with pytest.raises(GatewayError) as caught:
        gateway(tmp_path)._external_rebind_state()

    assert caught.value.code == "CONNECTOR_STATE_INVALID"


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"bindings": {}, "pending": []},
        {"bindings": [], "pending": {}},
    ],
)
def test_invalid_connector_state_shape_fails_closed(tmp_path, payload):
    write_state(tmp_path, payload)

    with pytest.raises(GatewayError) as caught:
        gateway(tmp_path)._external_rebind_state()

    assert caught.value.code == "CONNECTOR_STATE_INVALID"


def test_invalid_external_profile_shape_is_structured(tmp_path):
    digest = "b" * 64
    write_contract(tmp_path, ["not", "a", "profile-map"])
    write_state(
        tmp_path,
        {
            "bindings": [
                {
                    "fingerprint_sha256": digest,
                    "status": "ACTIVE",
                    "connector_id": "CHATGPT_NATIVE",
                    "principal": "CHATGPT_NATIVE_DELEGATE",
                }
            ],
            "pending": [],
        },
    )

    with pytest.raises(GatewayError) as caught:
        gateway(tmp_path)._actor_from_external_binding(digest)

    assert caught.value.code == "CONNECTOR_CONTRACT_INVALID"


def test_malformed_binding_deadline_fails_row_closed(tmp_path):
    digest = "c" * 64
    write_contract(
        tmp_path,
        {
            "CHATGPT_NATIVE": {
                "principal": "CHATGPT_NATIVE_DELEGATE",
                "actor_role": "EXTERNAL_DELEGATED_CLIENT",
                "instance_role": "chatgpt-native",
                "tools": ["get_head"],
                "scopes": ["get_head"],
                "deny": [],
                "seat": False,
            }
        },
    )
    write_state(
        tmp_path,
        {
            "bindings": [
                {
                    "fingerprint_sha256": digest,
                    "status": "ACTIVE",
                    "connector_id": "CHATGPT_NATIVE",
                    "principal": "CHATGPT_NATIVE_DELEGATE",
                    "expires_at": "not-a-date",
                }
            ],
            "pending": [],
        },
    )

    assert gateway(tmp_path)._actor_from_external_binding(digest) is None


def test_external_connector_health_is_non_secret_and_counts_state(tmp_path):
    write_contract(
        tmp_path,
        {
            "CHATGPT_NATIVE": {
                "principal": "CHATGPT_NATIVE_DELEGATE",
                "tools": ["get_head"],
                "scopes": ["get_head"],
                "deny": [],
                "seat": False,
            },
            "GENERIC_AGENT": {
                "principal": "GENERIC_AGENT_DELEGATE",
                "tools": ["get_head"],
                "scopes": ["get_head"],
                "deny": [],
                "seat": False,
            },
        },
    )
    write_state(
        tmp_path,
        {
            "bindings": [
                {
                    "fingerprint_sha256": "d" * 64,
                    "status": "ACTIVE",
                    "connector_id": "CHATGPT_NATIVE",
                    "principal": "CHATGPT_NATIVE_DELEGATE",
                },
                {
                    "fingerprint_sha256": "e" * 64,
                    "status": "GRACE",
                    "connector_id": "GENERIC_AGENT",
                    "principal": "GENERIC_AGENT_DELEGATE",
                },
            ],
            "pending": [{"status": "PENDING"}],
        },
    )

    health = gateway(tmp_path).external_connector_health()

    assert health == {
        "state_valid": True,
        "contract_valid": True,
        "binding_count": 2,
        "pending_count": 1,
        "active_binding_count": 2,
        "chatgpt_native_binding_active": True,
        "error": None,
        "profile_count": 2,
    }
    assert "fingerprint" not in json.dumps(health).lower()
    assert "delegate" not in json.dumps(health).lower()
