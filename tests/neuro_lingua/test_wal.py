from raios.neuro_lingua.wal import ExistingCognitiveWALWriter
from raios.neuro_lingua.schema import KnowledgeState


def test_wal_reuses_existing_cognitive_wal_and_starts_discovered():
    writer = ExistingCognitiveWALWriter()
    if writer.bus is None:
        result = writer.append_learning("nl0-unavailable", {"note": "offline"})
        assert result["status"] == "WAL_UNAVAILABLE"
        assert result["wal_appended"] is False
        return
    first = writer.append_learning(
        "nl0-dialect-pattern",
        {"pattern": "ar-EG vs ar-GULF", "confidence": 0.8},
        knowledge_state=KnowledgeState.DISCOVERED,
    )
    assert first["knowledge_state"] == "DISCOVERED"
    assert first["wal_path"].replace("\\", "/").endswith("RAIOS/V9/wal/cognitive-events.jsonl")
    event_id = first.get("event_id")
    replay = writer.bus.emit_event(
        writer.bus.build_event(
            event_type="LEARNING",
            actor="RAIOS.NEUROLINGUA",
            intent="nl0-dialect-pattern",
            event_id=event_id,
            success=True,
            metadata={"knowledge_state": "DISCOVERED", "subsystem": "neuro_lingua"},
        )
    )
    assert replay["status"] == "DUPLICATE_REJECTED"
    replayed = writer.bus.replay_wal()
    assert "already_processed" in replayed
    assert "processed_now" in replayed
    assert replayed["wal_events"] >= 1
