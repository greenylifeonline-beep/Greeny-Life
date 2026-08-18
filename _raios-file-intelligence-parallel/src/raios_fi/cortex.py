"""Main Qwen Cortex consumer. Output is PROPOSAL only. Never a raw repo dump."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from .config import FailClosed, which


@dataclass(frozen=True)
class CortexProposal:
    status: str
    knowledge_state: str
    query_plan: dict[str, Any]
    evidence_ids: list[str]
    rkg_micrograph: dict[str, Any]
    symbols: list[str]
    version_relations: list[dict[str, Any]]
    confidence: dict[str, Any]
    disagreements: list[dict[str, Any]]
    skills: list[str]
    model_used: bool
    text: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def synthesize_proposal(
    *,
    query_plan: dict[str, Any],
    evidence: list[dict[str, Any]],
    micrograph: dict[str, Any] | None = None,
    symbols: list[str] | None = None,
    version_relations: list[dict[str, Any]] | None = None,
    confidence: dict[str, Any] | None = None,
    disagreements: list[dict[str, Any]] | None = None,
    skills: list[str] | None = None,
    allow_model: bool = False,
) -> CortexProposal:
    if allow_model:
        if not evidence:
            raise FailClosed("QWEN_SYNTHESIS_REQUIRES_EXPLICIT_EVIDENCE_BUNDLE")
        if not which("ollama"):
            return CortexProposal(
                status="UNAVAILABLE",
                knowledge_state="PROPOSAL",
                query_plan=query_plan,
                evidence_ids=[str(e.get("file_id") or e.get("relative_path") or "") for e in evidence[:40]],
                rkg_micrograph=micrograph or {},
                symbols=list(symbols or [])[:40],
                version_relations=list(version_relations or [])[:40],
                confidence=confidence or {},
                disagreements=list(disagreements or []),
                skills=list(skills or ["file-intelligence"]),
                model_used=False,
                text=None,
            )
        raise FailClosed("QWEN_SYNTHESIS_NOT_EXECUTED_WITHOUT_GOVERNED_RUNTIME")
    return CortexProposal(
        status="SKIPPED",
        knowledge_state="PROPOSAL",
        query_plan=query_plan,
        evidence_ids=[str(e.get("file_id") or e.get("relative_path") or "") for e in evidence[:40]],
        rkg_micrograph=micrograph or {},
        symbols=list(symbols or [])[:40],
        version_relations=list(version_relations or [])[:40],
        confidence=confidence or {},
        disagreements=list(disagreements or []),
        skills=list(skills or ["file-intelligence"]),
        model_used=False,
        text=None,
    )
