from raios.neuro_lingua.schema import (
    CognitiveMeaningPacket,
    Intent,
    LanguageProfile,
    SemanticPayload,
)


def test_cognitive_meaning_packet():

    packet = CognitiveMeaningPacket(
        source_text="متبوظش حاجة في المشروع",
        language=LanguageProfile(
            language="ar",
            locale="ar-EG",
            dialect="egyptian",
            confidence=0.99,
        ),
        intent=Intent(
            primary="request_action",
            subtype="safe_change",
        ),
        semantics=SemanticPayload(
            action="modify",
            target="project",
            goal="preserve_behavior",
        ),
        constraints=[
            "avoid_regression",
        ],
    )

    assert packet.language.locale == "ar-EG"
    assert "avoid_regression" in packet.constraints
