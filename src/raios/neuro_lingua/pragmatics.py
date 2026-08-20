"""Minimum pragmatic interpretation layer.

Literal semantic content is separated from conversational markers.
``إذا ما عليك أمر`` is a politeness softener, never a logical condition.
Egyptian ``الدنيا هتبوظ`` binds to system.regression only when domain context
supports that reading — via the concept registry, not a phrase dictionary.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from raios.neuro_lingua.concepts import ConceptRegistry
from raios.neuro_lingua.types import (
    BoundConcept,
    InterpretationContext,
    PragmaticFrame,
    Register,
)


def _load_marker_table(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return list(payload.get("markers") or [])


class PragmaticsAnalyzer:
    def __init__(self, markers_path: Path, registry: ConceptRegistry) -> None:
        self.markers = _load_marker_table(markers_path)
        self.registry = registry

    def analyze(
        self,
        text: str,
        *,
        concepts: list[BoundConcept],
        context: InterpretationContext | None = None,
    ) -> PragmaticFrame:
        ctx = context or InterpretationContext()
        frame = PragmaticFrame()
        bound_ids = {item.concept_id for item in concepts}

        if "pragmatics.politeness_softener" in bound_ids:
            frame.politeness_marker = True
            frame.not_logical_condition.append("إذا ما عليك أمر")
            frame.flags["politeness_marker"] = True

        if "action.resolve" in bound_ids:
            frame.action = "resolve"
        elif "action.inspect" in bound_ids:
            frame.action = "inspect"

        if "deadline.today" in bound_ids:
            frame.deadline = "today"

        if "system.regression" in bound_ids:
            frame.flags["system_regression"] = True

        # Marker table supplies additional evidence, still concept-backed.
        for marker in self.markers:
            patterns = marker.get("patterns") or []
            if not any(pattern and pattern in text for pattern in patterns):
                continue
            required = marker.get("requires_domain")
            if required and ctx.domain not in required:
                continue
            concept_id = marker.get("concept_id")
            flag = marker.get("flag")
            if marker.get("not_logical_condition"):
                frame.politeness_marker = True
                for pattern in patterns:
                    if pattern in text and pattern not in frame.not_logical_condition:
                        frame.not_logical_condition.append(pattern)
            if flag == "deadline_today":
                frame.deadline = frame.deadline or "today"
            if flag == "action_resolve":
                frame.action = frame.action or "resolve"
            if flag == "action_inspect" and frame.action is None:
                frame.action = "inspect"
            if concept_id == "system.regression" and ctx.domain in (required or []):
                frame.flags["system_regression"] = True

        frame.register = _guess_register(text, ctx, frame)
        return frame


def _guess_register(text: str, ctx: InterpretationContext, frame: PragmaticFrame) -> Register:
    if ctx.domain in {"software", "engineering", "devops"}:
        return Register.TECHNICAL
    if frame.politeness_marker:
        return Register.FORMAL
    if any(tok in text for tok in ("مش", "ايه", "كده", "ikke", "inte")):
        return Register.INFORMAL
    return Register.NEUTRAL


def derive_intent(frame: PragmaticFrame, concepts: list[BoundConcept]) -> str | None:
    ids = {c.concept_id for c in concepts}
    if frame.action == "resolve" and frame.deadline == "today":
        return "resolve_by_today"
    if "software.deploy" in ids:
        return "deploy_request"
    if "system.regression" in ids:
        return "report_system_regression"
    if "software.report" in ids:
        return "report_generation_issue"
    if frame.action:
        return frame.action
    if ids:
        return "concept_bearing_utterance"
    return None
