"""Skill compiler. Prompt templates are not skills. Zero-LLM conversion when justified."""
from __future__ import annotations

from typing import Any

from .config import FailClosed, deterministic_id, utc_now
from .event_bus import EventBus
from .ledger import Ledger
from .schemas import SkillRecord

PROGRESSION = (
    "MODEL_REASONING",
    "REPEATED_PATTERN",
    "MICRO_SKILL",
    "VALIDATED_SKILL",
    "DETERMINISTIC_TOOL",
    "ZERO_LLM_EXECUTION",
)

ZERO_LLM_CANDIDATES = (
    "file_existence",
    "hash_verification",
    "git_state",
    "json_validation",
    "schema_checks",
    "ollama_health",
    "model_inventory",
    "failure_classification",
    "report_integrity",
    "dependency_inspection",
    "encoding_safe_subprocess",
)


class SkillCompiler:
    def __init__(self, ledger: Ledger, bus: EventBus) -> None:
        self.ledger = ledger
        self.bus = bus

    def compile(self, source: dict[str, Any]) -> dict[str, Any]:
        if source.get("prompt_template") and not source.get("procedure"):
            raise FailClosed("PROMPT_TEMPLATE_IS_NOT_A_SKILL")
        required = (
            "interface",
            "preconditions",
            "inputs",
            "outputs",
            "procedure",
            "invariants",
            "negative_controls",
            "tests",
            "rollback",
            "failure_modes",
            "provenance",
        )
        missing = [k for k in required if k not in source]
        if missing:
            raise FailClosed("SKILL_MISSING:" + ",".join(missing))
        skill_id = deterministic_id("skill", source["interface"], str(source["procedure"]))
        rec = SkillRecord(
            skill_id=skill_id,
            interface=source["interface"],
            preconditions=list(source["preconditions"]),
            inputs=list(source["inputs"]),
            outputs=list(source["outputs"]),
            procedure=list(source["procedure"]),
            invariants=list(source["invariants"]),
            negative_controls=list(source["negative_controls"]),
            tests=list(source["tests"]),
            rollback=dict(source["rollback"]),
            failure_modes=list(source["failure_modes"]),
            provenance=dict(source["provenance"]),
            version=str(source.get("version") or "0.1.0"),
            confidence=float(source.get("confidence") or 0.4),
            transfer_evidence=list(source.get("transfer_evidence") or []),
            kind=str(source.get("kind") or "MICRO_SKILL"),
            prompt_template_is_skill=False,
            zero_llm=bool(source.get("zero_llm")),
            active=False,
        )
        dumped = rec.model_dump()
        dumped["created_at"] = utc_now()
        dumped["canonical"] = False
        self.ledger.put("skills", "skill_id", skill_id, dumped, extra={"kind": dumped["kind"]})
        self.bus.emit("SKILL_CANDIDATE", "skill_compiler", {"skill_id": skill_id, "kind": dumped["kind"]})
        return dumped

    def promote(self, skill_id: str, nxt: str, *, governed: bool = False) -> dict[str, Any]:
        rec = self.ledger.get("skills", skill_id)
        if not rec:
            raise FailClosed("SKILL_UNKNOWN")
        if nxt not in PROGRESSION:
            raise FailClosed(f"UNKNOWN_SKILL_KIND:{nxt}")
        if nxt in {"VALIDATED_SKILL", "DETERMINISTIC_TOOL", "ZERO_LLM_EXECUTION"} and not rec.get("transfer_evidence"):
            raise FailClosed("SKILL_REQUIRES_TRANSFER_EVIDENCE")
        if nxt == "ZERO_LLM_EXECUTION" and not rec.get("zero_llm"):
            raise FailClosed("ZERO_LLM_NOT_JUSTIFIED")
        if not governed and nxt in {"DETERMINISTIC_TOOL", "ZERO_LLM_EXECUTION"}:
            raise FailClosed("NO_CANONICAL_AUTO_PROMOTION")
        rec["kind"] = nxt
        rec["active"] = False
        self.ledger.put("skills", "skill_id", skill_id, rec, extra={"kind": nxt})
        if nxt == "VALIDATED_SKILL":
            self.bus.emit("SKILL_VALIDATED", "skill_compiler", {"skill_id": skill_id})
        return rec

    def zero_llm_candidate(self, name: str, model_accuracy: float, det_accuracy: float, tests_pass: bool, transfer_pass: bool) -> dict[str, Any]:
        if name not in ZERO_LLM_CANDIDATES:
            raise FailClosed(f"UNKNOWN_ZERO_LLM:{name}")
        eligible = det_accuracy >= model_accuracy and tests_pass and transfer_pass
        return {
            "name": name,
            "eligible": eligible,
            "promoted": False,
            "reason": None if eligible else "GATES_INCOMPLETE",
            "zero_llm_conversion_rate_delta": 1.0 if eligible else 0.0,
        }
