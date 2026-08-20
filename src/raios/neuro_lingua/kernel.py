from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .code_switch import segment_code_switch
from .concepts import load_concept_registry, resolve_concepts
from .dialect import resolve_dialect
from .gaps import classify_gap
from .governor import CognitiveResourceGovernor
from .language import identify_language, normalize_text
from .pipeline import StageResult, run_stage
from .pragmatics import analyze_pragmatics, analyze_register
from .protected import extract_protected_tokens
from .provider_contracts import CapabilityRequirement
from .realize import realize_meaning
from .router import ProviderRouter
from .schema import (
    CognitiveMeaningPacket,
    Intent,
    KnowledgeState,
    LanguageProfile,
    RegisterProfile,
    RiskLevel,
    SemanticPayload,
    StageTrace,
)
from .training import decide_training
from .verify import verify_realization
from .wal import ExistingCognitiveWALWriter


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "configs" / "neuro_lingua").exists():
            return parent
    return Path.cwd()


@dataclass
class InterpretResult:
    meaning: CognitiveMeaningPacket
    stages: list[StageResult] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class RealizeResult:
    text: str
    target_locale: str
    verification: dict[str, Any]
    stages: list[StageResult] = field(default_factory=list)
    meaning: CognitiveMeaningPacket | None = None


class NeuroLingua:
    def __init__(
        self,
        *,
        concept_path: str | Path | None = None,
        wal: ExistingCognitiveWALWriter | None = None,
        router: ProviderRouter | None = None,
        governor: CognitiveResourceGovernor | None = None,
    ):
        root = _repo_root()
        self.concept_path = Path(concept_path or root / "configs" / "neuro_lingua" / "concepts.yaml")
        self.registry = load_concept_registry(self.concept_path)
        self.wal = wal or ExistingCognitiveWALWriter()
        self.governor = governor or CognitiveResourceGovernor()
        self.router = router or ProviderRouter(governor=self.governor)

    async def interpret(
        self,
        text: str,
        context: dict[str, Any] | None = None,
        target_locale: str | None = None,
    ) -> InterpretResult:
        context = dict(context or {})
        stages: list[StageResult] = []

        norm = run_stage("INPUT_NORMALIZATION", "deterministic", lambda: normalize_text(text))
        stages.append(norm)
        working = str(norm.payload.get("text") or text)

        lid = run_stage("LANGUAGE_IDENTIFICATION", "deterministic+local-lid", lambda: identify_language(working))
        stages.append(lid)
        languages = list(lid.payload.get("languages") or [])

        dialect = run_stage(
            "DIALECT_LOCALE_RESOLUTION",
            "hybrid-classifier",
            lambda: resolve_dialect(working, languages),
        )
        stages.append(dialect)
        dialect_row = dialect.payload.get("dialect") or {}
        primary_locale = dialect_row.get("profile") or (languages[0].get("locale") if languages else None) or "und"

        switched = run_stage(
            "CODE_SWITCH_SEGMENTATION",
            "deterministic",
            lambda: segment_code_switch(working, primary_locale),
        )
        stages.append(switched)

        protected = run_stage(
            "PROTECTED_TOKEN_EXTRACTION",
            "deterministic",
            lambda: extract_protected_tokens(working),
        )
        stages.append(protected)

        register = run_stage(
            "REGISTER_ANALYSIS",
            "heuristic",
            lambda: analyze_register(working, primary_locale),
        )
        stages.append(register)

        prag = run_stage(
            "PRAGMATICS_ANALYSIS",
            "concept+heuristic",
            lambda: analyze_pragmatics(working, context),
        )
        stages.append(prag)

        concepts = run_stage(
            "CONCEPT_RESOLUTION",
            "concept-registry",
            lambda: resolve_concepts(working, self.registry),
        )
        stages.append(concepts)

        admission = self.governor.admit("SEMANTIC_INTERPRETATION")
        routed = self.router.route(
            CapabilityRequirement(
                capability="SEMANTIC_INTERPRETATION",
                languages=(primary_locale,),
                offline_required=True,
            )
        )
        semantic = run_stage(
            "SEMANTIC_INTERPRETATION",
            routed["provider"],
            lambda: self._semantic_from_stages(working, prag.payload, concepts.payload, admission.admitted),
        )
        stages.append(semantic)

        action = prag.payload.get("action") or semantic.payload.get("action") or "unknown"
        constraints: list[str] = []
        if prag.payload.get("domain_warning") == "risk_of_regression" or "متبوظش" in working or "regression" in working.lower():
            constraints.append("avoid_regression")
        if "production" in working.lower() or "produksjon" in working.lower() or "produktion" in working.lower():
            constraints.append("avoid_regression")

        intent_primary = "request_action" if action in {"resolve", "inspect", "remove"} else "unknown"
        lang_profiles = []
        for row in languages:
            lang_profiles.append(
                LanguageProfile(
                    language=row.get("language") or "und",
                    locale=row.get("locale"),
                    dialect=dialect_row.get("profile") if row.get("language") == "ar" else row.get("locale"),
                    confidence=row.get("confidence"),
                    parent=dialect_row.get("parent") if row.get("language") == "ar" else row.get("language"),
                    evidence=list(row.get("evidence") or []),
                    alternatives=list(dialect_row.get("alternatives") or []),
                )
            )
        if dialect_row.get("profile") and not any(p.locale == dialect_row.get("profile") for p in lang_profiles):
            lang_profiles.insert(
                0,
                LanguageProfile(
                    language="ar" if str(dialect_row.get("profile")).startswith("ar") else str(dialect_row.get("parent") or "und"),
                    locale=dialect_row.get("profile"),
                    dialect=dialect_row.get("profile"),
                    confidence=dialect_row.get("confidence"),
                    parent=dialect_row.get("parent"),
                    evidence=list(dialect_row.get("evidence") or []),
                    alternatives=list(dialect_row.get("alternatives") or []),
                ),
            )

        from .schema import ConfidenceAtom, ConfidenceProvenance

        packet = CognitiveMeaningPacket(
            source_text=text,
            source_locale=primary_locale,
            detected_languages=lang_profiles,
            code_switch_segments=list(switched.payload.get("segments") or []),
            language=lang_profiles[0] if lang_profiles else LanguageProfile(language="und"),
            speech_register=RegisterProfile(**(register.payload.get("register") or {})),
            intent=Intent(primary=intent_primary, subtype=action),
            semantics=SemanticPayload(
                action=action,
                target=context.get("target"),
                goal="preserve_behavior" if "avoid_regression" in constraints else None,
                propositions=[{
                    "action": action,
                    "deadline": getattr(prag.payload.get("temporal"), "deadline", None),
                }],
            ),
            constraints=constraints,
            entities=[{"text": tok.text, "kind": tok.kind} for tok in (protected.payload.get("tokens") or [])],
            preserved_tokens=list(protected.payload.get("tokens") or []),
            pragmatics=prag.payload.get("pragmatics"),
            temporal=prag.payload.get("temporal"),
            modality=prag.payload.get("modality"),
            terminology=list(concepts.payload.get("matches") or []),
            context_refs=[str(v) for v in context.values() if v is not None],
            risk=RiskLevel.MEDIUM if constraints else RiskLevel.LOW,
            confidence=ConfidenceProvenance(
                language=ConfidenceAtom(value=lid.confidence, source="deterministic+local-lid"),
                dialect=ConfidenceAtom(value=dialect.confidence, source="hybrid-classifier"),
                semantic=ConfidenceAtom(value=semantic.confidence, source="deterministic-semantic"),
                pragmatics=ConfidenceAtom(value=prag.confidence, source="concept+heuristic"),
            ),
            evidence=[item for stage in stages for item in stage.evidence],
            provider_trace=[StageTrace(**stage.as_trace()) for stage in stages],
            knowledge_state=KnowledgeState.DISCOVERED,
            metadata={
                "target_locale": target_locale,
                "governor": admission.reason,
                "routing": routed,
                "registry_status": self.registry.get("status"),
            },
        )
        packet.propositions = list(packet.semantics.propositions)
        packet.actions = [{"action": action}]
        return InterpretResult(meaning=packet, stages=stages, metrics=self.router.metrics())

    def _semantic_from_stages(self, text: str, prag: dict[str, Any], concepts: dict[str, Any], cortex_admitted: bool) -> dict[str, Any]:
        warnings = []
        if not cortex_admitted:
            warnings.append("MAIN_CORTEX_DENIED_DETERMINISTIC_FALLBACK")
        return {
            "status": "OK",
            "confidence": 0.72 if prag.get("action") else None,
            "evidence": list(prag.get("evidence") or []) + list(concepts.get("evidence") or []),
            "action": prag.get("action"),
            "fallback_used": not cortex_admitted,
            "warnings": warnings,
        }

    async def realize(
        self,
        meaning: CognitiveMeaningPacket,
        target_locale: str,
        context: dict[str, Any] | None = None,
    ) -> RealizeResult:
        stages: list[StageResult] = []
        realized = run_stage(
            "SEMANTIC_REALIZATION",
            f"deterministic-realizer:{target_locale}",
            lambda: realize_meaning(meaning, target_locale, context),
        )
        stages.append(realized)
        text = str(realized.payload.get("text") or "")
        verified = run_stage(
            "RISK_BASED_VERIFICATION",
            "deterministic-verifier",
            lambda: verify_realization(meaning, text, target_locale),
        )
        stages.append(verified)
        return RealizeResult(
            text=text,
            target_locale=target_locale,
            verification=verified.payload,
            stages=stages,
            meaning=meaning,
        )

    async def record_observation(self, intent: str, payload: dict[str, Any]) -> dict[str, Any]:
        return self.wal.append_learning(intent, payload, knowledge_state=KnowledgeState.DISCOVERED)


_default: NeuroLingua | None = None


def _client() -> NeuroLingua:
    global _default
    if _default is None:
        _default = NeuroLingua()
    return _default


async def interpret(text: str, context: dict[str, Any] | None = None, target_locale: str | None = None) -> InterpretResult:
    return await _client().interpret(text=text, context=context, target_locale=target_locale)


async def realize(meaning: CognitiveMeaningPacket, target_locale: str, context: dict[str, Any] | None = None) -> RealizeResult:
    return await _client().realize(meaning=meaning, target_locale=target_locale, context=context)
