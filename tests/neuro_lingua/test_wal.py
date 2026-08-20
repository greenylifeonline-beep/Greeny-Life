import pytest

from raios.knowledge_state import KnowledgeState, assert_transition
from raios.wal import CognitiveWAL, stable_event_id


def test_wal_append_is_idempotent(tmp_path):
    wal = CognitiveWAL(tmp_path / "wal.jsonl")
    payload = {"surface": "الدنيا هتبوظ", "concept_id": "system.regression"}
    first, inserted_first = wal.append("idiom_interpretation", payload)
    second, inserted_second = wal.append("idiom_interpretation", payload)
    assert inserted_first is True
    assert inserted_second is False
    assert first.event_id == second.event_id
    replayed = wal.replay()
    assert len(replayed) == 1
    assert replayed[0].knowledge_state is KnowledgeState.DISCOVERED


def test_replay_from_disk_skips_duplicates(tmp_path):
    path = tmp_path / "wal.jsonl"
    wal = CognitiveWAL(path)
    wal.append("terminology_correction", {"term": "executor"})
    wal.append("terminology_correction", {"term": "executor"})
    again = CognitiveWAL(path)
    assert len(again.replay()) == 1


def test_cannot_append_canonical_directly(tmp_path):
    wal = CognitiveWAL(tmp_path / "wal.jsonl")
    with pytest.raises(ValueError, match="CANONICAL"):
        wal.append("dialect_pattern", {"locale": "ar-EG"}, knowledge_state=KnowledgeState.CANONICAL)


def test_promotion_requires_validated_then_evidence(tmp_path):
    wal = CognitiveWAL(tmp_path / "wal.jsonl")
    event, _ = wal.append("user_correction", {"field": "locale", "to": "ar-EG"})
    with pytest.raises(ValueError):
        wal.promote(event.event_id, KnowledgeState.CANONICAL, allow_canonical=True, validation_evidence={"ok": True})
    wal.promote(event.event_id, KnowledgeState.VALIDATED)
    with pytest.raises(ValueError, match="allow_canonical"):
        wal.promote(event.event_id, KnowledgeState.CANONICAL, validation_evidence={"ok": True})
    promoted = wal.promote(
        event.event_id,
        KnowledgeState.CANONICAL,
        allow_canonical=True,
        validation_evidence={"reviewer": "policy"},
    )
    assert promoted.knowledge_state is KnowledgeState.CANONICAL


def test_illegal_transition_helper():
    with pytest.raises(ValueError):
        assert_transition(KnowledgeState.DISCOVERED, KnowledgeState.CANONICAL)


def test_stable_event_id_is_deterministic():
    a = stable_event_id("x", {"b": 1, "a": 2})
    b = stable_event_id("x", {"a": 2, "b": 1})
    assert a == b
