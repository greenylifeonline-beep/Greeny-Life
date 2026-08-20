from pathlib import Path

import pytest
import yaml

from raios.neuro_lingua.concepts import (
    CanonicalRedefinitionError,
    ConceptCollisionError,
    ConceptRecord,
    detect_collisions,
    load_concept_registry,
)


def test_loads_unique_concept_ids(repo_root: Path):
    registry = load_concept_registry(repo_root / "configs/neuro_lingua/concepts.yaml")
    ids = registry.ids()
    assert len(ids) == len(set(ids))
    assert "action.resolve" in registry
    assert "pragmatics.politeness_softener" in registry
    assert "system.regression" in registry


def test_alias_collision_detected(tmp_path: Path):
    records = [
        ConceptRecord("a", "meaning a", {"en": ["shared"]}, {}, ["g"]),
        ConceptRecord("b", "meaning b", {"en": ["shared"]}, {}, ["g"]),
    ]
    collisions = detect_collisions(records)
    kinds = {c.kind for c in collisions}
    assert "alias_collision" in kinds


def test_canonical_redefinition_rejected(tmp_path: Path, repo_root: Path):
    src = yaml.safe_load((repo_root / "configs/neuro_lingua/concepts.yaml").read_text(encoding="utf-8"))
    src["scopes"] = [
        {
            "scope": "project",
            "concepts": [
                {
                    "concept_id": "action.resolve",
                    "canonical_meaning": "A totally different meaning",
                    "aliases": {},
                    "realizations": {"en": "nope"},
                }
            ],
        }
    ]
    path = tmp_path / "concepts.yaml"
    path.write_text(yaml.safe_dump(src), encoding="utf-8")
    with pytest.raises(CanonicalRedefinitionError):
        load_concept_registry(path)


def test_scope_may_customize_realization(tmp_path: Path, repo_root: Path):
    src = yaml.safe_load((repo_root / "configs/neuro_lingua/concepts.yaml").read_text(encoding="utf-8"))
    src["scopes"] = [
        {
            "scope": "project",
            "concepts": [
                {
                    "concept_id": "action.resolve",
                    "canonical_meaning": "Bring an open matter to a completed, handled state.",
                    "aliases": {},
                    "realizations": {"en": "close the ticket"},
                }
            ],
        }
    ]
    path = tmp_path / "concepts.yaml"
    path.write_text(yaml.safe_dump(src), encoding="utf-8")
    registry = load_concept_registry(path)
    assert registry.realization("action.resolve", "en") == "close the ticket"


def test_duplicate_concept_id_different_meaning_is_collision():
    records = [
        ConceptRecord("x", "one", {}, {}, []),
        ConceptRecord("x", "two", {}, {}, []),
    ]
    kinds = {c.kind for c in detect_collisions(records)}
    assert "canonical_meaning_conflict" in kinds


def test_loader_raises_on_alias_collision(tmp_path: Path):
    payload = {
        "concepts": [
            {
                "concept_id": "one",
                "canonical_meaning": "A",
                "aliases": {"en": ["same"]},
                "realizations": {"en": "A"},
            },
            {
                "concept_id": "two",
                "canonical_meaning": "B",
                "aliases": {"en": ["same"]},
                "realizations": {"en": "B"},
            },
        ]
    }
    path = tmp_path / "c.yaml"
    path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    with pytest.raises(ConceptCollisionError):
        load_concept_registry(path)
