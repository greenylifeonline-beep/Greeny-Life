from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME = ROOT / "RAIOS" / "V9" / "runtime"
if str(RUNTIME) not in sys.path:
    sys.path.insert(0, str(RUNTIME))

import evolution_daemon as ed


def test_internal_sufficient_requires_pass_three_evidence_and_no_contradiction():
    assert ed._internal_sufficient({
        "verification": {"status": "PASS", "evidence_count": 3},
        "contradictions": [],
    }) is True
    assert ed._internal_sufficient({
        "verification": {"status": "PASS", "evidence_count": 2},
        "contradictions": [],
    }) is False
    assert ed._internal_sufficient({
        "verification": {"status": "CONFLICT", "evidence_count": 5},
        "contradictions": [{"kind": "X"}],
    }) is False


def test_external_gap_research_is_discovered_not_canonical_and_cached(tmp_path, monkeypatch):
    monkeypatch.setattr(ed, "GAP_RESEARCH", tmp_path / "gap.json")

    class FakeCortex:
        def __init__(self):
            self.calls = []
        def search(self, query, **kwargs):
            self.calls.append((query, kwargs))
            return {
                "verification": {"status": "PASS", "evidence_count": 4},
                "sources": ["PUBLIC_WEB"],
                "results": [{"source": "PUBLIC_WEB", "excerpt": "candidate"}],
                "contradictions": [],
            }

    cortex = FakeCortex()
    family = {
        "family_id": "F-1",
        "geometry": {
            "tool": "vector-retrieval",
            "exception_type": "MissingCapability",
            "unresolved_flags": ["semantic-ranking"],
        },
    }
    internal = {"verification": {"status": "INSUFFICIENT", "evidence_count": 1}}
    first = ed._external_gap_research(cortex, family, internal)
    second = ed._external_gap_research(cortex, family, internal)

    assert len(cortex.calls) == 1
    assert cortex.calls[0][1]["public_allowed"] is True
    assert first["knowledge_state"] == "DISCOVERED"
    assert first["canonical"] is False
    assert first["promoted"] is False
    assert "EXTERNAL_ONLY_FOR_PROVEN_GAP" in first["law"]
    assert second["searched_at"] == first["searched_at"]


def test_safe_gap_query_drops_private_path_material():
    family = {
        "geometry": {
            "tool": "repo-search",
            "exception_type": "MissingFeature",
            "unresolved_flags": [r"C:\secret\repo", "public-ranking"],
        }
    }
    query = ed._safe_gap_query(family)
    assert query is not None
    assert "C:\secret" not in query
    assert "public-ranking" in query
