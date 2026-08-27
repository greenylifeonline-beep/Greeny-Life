"""Official a2a-sdk AgentCard construction. Seats are not public agents."""

from __future__ import annotations

from google.protobuf.json_format import MessageToDict
from a2a.types import AgentCapabilities, AgentCard
from a2a.utils.constants import PROTOCOL_VERSION_CURRENT, TransportProtocol

from .capability import CAPABILITY_NOOP, public_skill_subset
from .extensions import ap2_hook, semantic_extension
from .failclosed import SEAT_IDENTITY_NOT_PUBLIC_AGENT, FailClosed
from .flags import A2A_PUBLIC_LISTENER_ENABLED
from .secrets_guard import scan_mapping

FORBIDDEN_PUBLIC_AGENTS = frozenset(
    {
        "C1",
        "C2-KAGGLE-CONTROL",
        "C2-PRIMARY-EXECUTOR",
        "C2-ESTATE-RECON",
        "C6-AG-REMOTE-RECON",
        "C7-CLOUD-SANDBOX",
        # Legacy view labels that can still appear as proposed identities.
        "C2A",
        "C2B",
    }
)

PUBLIC_AGENT_NAME = "RAIOS Foundation Agent"
PUBLIC_AGENT_ID = "raios.foundation.agent"


def _skill(card: AgentCard, subset: dict) -> None:
    sk = card.skills.add()
    sk.id = subset["id"]
    sk.name = subset["name"]
    sk.description = subset["description"]
    sk.tags.extend(subset.get("tags") or [])
    sk.input_modes.extend(subset.get("input_modes") or [])
    sk.output_modes.extend(subset.get("output_modes") or [])


def build_public_card() -> AgentCard:
    if A2A_PUBLIC_LISTENER_ENABLED:
        raise FailClosed("PUBLIC_LISTENER_DISABLED")
    card = AgentCard()
    card.name = PUBLIC_AGENT_NAME
    card.description = "RAIOS federated interoperability edge (foundation). Not a public internet listener."
    card.version = "1.0.0"
    iface = card.supported_interfaces.add()
    iface.url = "http://127.0.0.1/a2a"
    iface.protocol_binding = TransportProtocol.JSONRPC.value
    iface.protocol_version = PROTOCOL_VERSION_CURRENT
    card.default_input_modes.append("application/json")
    card.default_output_modes.append("application/json")
    caps = AgentCapabilities()
    caps.streaming = False
    caps.push_notifications = False
    caps.extended_agent_card = True
    ext = caps.extensions.add()
    sem = semantic_extension(required=False)
    ext.uri = str(sem["uri"])
    ext.description = str(sem["description"])
    ext.required = False
    ap2 = caps.extensions.add()
    hook = ap2_hook()
    ap2.uri = str(hook["uri"])
    ap2.description = str(hook["description"])
    ap2.required = False
    card.capabilities.CopyFrom(caps)
    _skill(card, public_skill_subset(CAPABILITY_NOOP))
    return card


def build_extended_card() -> AgentCard:
    card = build_public_card()
    extra = card.skills.add()
    extra.id = "raios.foundation.high_risk_mutate"
    extra.name = "raios.foundation.high_risk_mutate"
    extra.description = "Authenticated capability detail. Authority gate required. Not independently executable."
    extra.tags.extend(["raios", "authenticated", "high-risk"])
    return card


def card_as_dict(card: AgentCard) -> dict:
    data = MessageToDict(card, preserving_proto_field_name=True)
    scan_mapping(data)
    assert_card_not_operational_seat(data)
    return data


def reject_seat_as_agent(name: str) -> None:
    if (name or "").strip() in FORBIDDEN_PUBLIC_AGENTS:
        raise FailClosed(SEAT_IDENTITY_NOT_PUBLIC_AGENT, name)


def assert_card_not_operational_seat(card: dict) -> None:
    published = {
        str(card.get("name") or ""),
        str(card.get("id") or ""),
        PUBLIC_AGENT_ID,
    }
    for skill in card.get("skills") or []:
        if isinstance(skill, dict):
            published.add(str(skill.get("id") or ""))
            published.add(str(skill.get("name") or ""))
    for value in published:
        if value in FORBIDDEN_PUBLIC_AGENTS:
            raise FailClosed(SEAT_IDENTITY_NOT_PUBLIC_AGENT, value)
