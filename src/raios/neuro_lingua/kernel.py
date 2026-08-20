"""NeuroLingua Semantic Kernel — public interpret/realize API.

No application code needs to know which model or vendor ran a step.
Providers are selected through capability contracts.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from raios.config import NeuroLinguaConfig, load_neuro_lingua_config
from raios.events import EventSink
from raios.knowledge_state import KnowledgeState
from raios.neuro_lingua.codeswitch import segment as segment_code_switch
from raios.neuro_lingua.concepts import ConceptRegistry, load_concept_registry
from raios.neuro_lingua.detection import HybridLanguageDetector
from raios.neuro_lingua.learning import (
    EvolutionInbox,
    FailureRecord,
    LearningGapClassifier,
)
from raios.neuro_lingua.packet import (
    CognitiveMeaningPacket,
    InterpretationResult,
    RenderedOutput,
)
from raios.neuro_lingua.pragmatics import PragmaticsAnalyzer, derive_intent
from raios.neuro_lingua.preservation import (
    extract_entities,
    extract_identifiers,
    extract_numbers,
    extract_terminology,
)
from raios.neuro_lingua.realization import SemanticRealizer
from raios.neuro_lingua.scandinavian import ScandinavianIsolator
from raios.neuro_lingua.training_policy import TrainingDecision, decide_training
from raios.neuro_lingua.types import (
    Confidence,
    ExecutionMetrics,
    InterpretationContext,
    Register,
)
from raios.neuro_lingua.verification import SemanticVerifier
from raios.observability import get_logger
from raios.providers import (
    Capability,
    LocalDeterministicProvider,
    NoCapableProvider,
    ProviderRegistry,
    ProviderRequest,
    ProviderUnavailable,
    SemanticProvider,
)
from raios.risk import RiskLevel
from raios.wal import CognitiveWAL, stable_event_id


class NeuroLingua:
    def __init__(
        self,
        config: NeuroLinguaConfig,
        *,
        registry: ConceptRegistry | None = None,
        providers: ProviderRegistry | None = None,
        wal: CognitiveWAL | None = None,
        extra_providers: list[SemanticProvider] | None = None,
    ) -> None:
        self.config = config
        self.logger = get_logger(repo_path=config.repo_root)
        self.concepts = registry or load_concept_registry(config.concepts_path)
        self.detector = HybridLanguageDetector()
        self.pragmatics = PragmaticsAnalyzer(config.pragmatics_path, self.concepts)
        self.isolator = ScandinavianIsolator(config.scandinavian_path)
        self.realizer = SemanticRealizer(self.concepts, self.isolator)
        self.verifier = SemanticVerifier(self.isolator)
        self.gap_classifier = LearningGapClassifier()
        self.providers = providers or ProviderRegistry([LocalDeterministicProvider()])
        if extra_providers:
            for provider in extra_providers:
                self.providers.register(provider)
        wal_sink = EventSink()
        self.wal = wal or CognitiveWAL(config.wal_path, sink=wal_sink)
        self.evolution = EvolutionInbox(EventSink(config.evolution_inbox_path))

    async def interpret(
        self,
        text: str,
        context: InterpretationContext | dict[str, Any] | None = None,
        target_locale: str | None = None,
    ) -> InterpretationResult:
        started = time.perf_counter()
        ctx = InterpretationContext.from_raw(context)
        metrics = ExecutionMetrics()
        warnings: list[str] = []

        detection = self.detector.detect(text, ctx)
        metrics.local_steps += 1
        metrics.tiers_used = list(detection.tiers_used)
        metrics.provider_calls += 1  # local deterministic capability

        if (
            "tier3_eligible" in detection.tiers_used
            and ctx.allow_llm
            and not ctx.offline
            and self.config.allow_llm_adjudication
        ):
            try:
                response = await self.providers.execute(
                    ProviderRequest(
                        capability=Capability.SEMANTIC_ADJUDICATION,
                        payload={"text": text, "detection": detection.to_dict()},
                        offline=False,
                        locale=detection.locale,
                    ),
                    allow_llm=True,
                )
                metrics.provider_calls += 1
                if response.used_llm:
                    metrics.llm_calls += 1
                else:
                    metrics.local_steps += 1
            except (NoCapableProvider, ProviderUnavailable) as exc:
                warnings.append(f"tier3_unavailable:{exc}")
                self._record_gap(
                    FailureRecord(
                        stage="language_identification",
                        message=str(exc),
                        code="NO_CAPABLE_PROVIDER",
                        capability=Capability.SEMANTIC_ADJUDICATION.value,
                        detection_locale=detection.locale,
                        detection_language=detection.language,
                    )
                )

        segments = segment_code_switch(text, detection)
        metrics.local_steps += 1

        concepts = self.concepts.bind(text, ctx)
        metrics.local_steps += 1
        pragmatics = self.pragmatics.analyze(text, concepts=concepts, context=ctx)
        intent = derive_intent(pragmatics, concepts)

        numbers = extract_numbers(text)
        identifiers = extract_identifiers(text, segments)
        entities = extract_entities(text)
        terminology = extract_terminology(segments, text)

        evidence = [f"tiers={detection.tiers_used}", f"concepts={len(concepts)}"]
        meaning_conf = _meaning_confidence(detection, concepts, pragmatics.action)

        packet = CognitiveMeaningPacket(
            source_text=text,
            detection=detection,
            segments=segments,
            concepts=concepts,
            pragmatics=pragmatics,
            numbers=numbers,
            entities=entities,
            identifiers=identifiers,
            terminology=terminology,
            register=pragmatics.register if pragmatics.register else Register.UNKNOWN,
            intent=intent,
            knowledge_state=KnowledgeState.DISCOVERED,
            risk_level=ctx.risk_level,
            evidence=evidence,
            provider_trace=["local.deterministic"],
            meaning_confidence=meaning_conf,
        )
        if target_locale:
            packet.evidence.append(f"requested_target={target_locale}")

        self._learn_from_interpretation(packet)
        metrics.latency_ms = round((time.perf_counter() - started) * 1000, 3)
        return InterpretationResult(meaning=packet, metrics=metrics, warnings=warnings)

    async def realize(
        self,
        meaning: CognitiveMeaningPacket,
        target_locale: str,
        context: InterpretationContext | dict[str, Any] | None = None,
    ) -> RenderedOutput:
        started = time.perf_counter()
        ctx = InterpretationContext.from_raw(context)
        metrics = ExecutionMetrics(local_steps=1, provider_calls=1)
        text, complete, warnings = self.realizer.realize(meaning, target_locale)
        report = self.verifier.verify(
            meaning,
            text,
            target_locale,
            risk_level=ctx.risk_level,
            allow_back_translation=self.config.allow_back_translation and ctx.risk_level is RiskLevel.CRITICAL,
        )
        if not report.passed:
            self._record_gap(
                FailureRecord(
                    stage="verification",
                    message="verification_failed",
                    verification_failed=True,
                    detection_locale=meaning.source_locale,
                    detection_language=meaning.detection.language,
                )
            )
        metrics.latency_ms = round((time.perf_counter() - started) * 1000, 3)
        leakage = report.leakage.leaked_tokens if report.leakage else []
        return RenderedOutput(
            text=text,
            target_locale=target_locale,
            meaning=meaning,
            realization_complete=complete and report.passed,
            verification=report.to_dict(),
            metrics=metrics,
            warnings=warnings,
            leakage=leakage,
        )

    def classify_failure(self, failure: FailureRecord):
        return self.gap_classifier.classify(failure)

    def training_decision(self, **kwargs: Any) -> TrainingDecision:
        return decide_training(**kwargs)

    def _learn_from_interpretation(self, packet: CognitiveMeaningPacket) -> None:
        if packet.detection.dialect:
            self.wal.append(
                "dialect_pattern",
                {
                    "locale": packet.detection.locale,
                    "dialect": packet.detection.dialect,
                    "packet_id": packet.packet_id,
                },
            )
        if packet.detection.code_switched:
            mapping = [{"index": s.index, "locale": s.locale, "text": s.text} for s in packet.segments]
            self.wal.append(
                "code_switch_mapping",
                {"packet_id": packet.packet_id, "segments": mapping},
            )
        for concept in packet.concepts:
            if concept.concept_id in {"system.regression", "pragmatics.politeness_softener"}:
                self.wal.append(
                    "idiom_interpretation",
                    {
                        "concept_id": concept.concept_id,
                        "surface": concept.surface,
                        "packet_id": packet.packet_id,
                    },
                )
        for span in packet.terminology:
            self.wal.append(
                "terminology_observation",
                {"surface": span.surface, "packet_id": packet.packet_id},
            )

    def record_user_correction(self, *, kind: str, payload: dict[str, Any]) -> None:
        allowed = {
            "user_correction",
            "terminology_correction",
            "translation_correction",
            "idiom_interpretation",
            "dialect_pattern",
            "code_switch_mapping",
        }
        if kind not in allowed:
            raise ValueError(f"Unsupported learning event {kind}")
        self.wal.append(kind, payload)

    def _record_gap(self, failure: FailureRecord) -> None:
        classification = self.gap_classifier.classify(failure)
        self.evolution.submit(
            classification,
            event_id=stable_event_id("learning_gap", {"stage": failure.stage, "message": failure.message}),
            payload={"stage": failure.stage, "message": failure.message},
        )


def _meaning_confidence(detection, concepts, action) -> Confidence:
    parts = [detection.language_confidence.value]
    if detection.dialect_confidence.sample_size:
        parts.append(detection.dialect_confidence.value)
    if concepts:
        parts.append(sum(c.confidence.value for c in concepts) / len(concepts))
    elif action:
        parts.append(0.6)
    else:
        parts.append(0.0)
    value = sum(parts) / len(parts)
    return Confidence(
        value=value,
        method="mean_of_measured_components",
        evidence=[c.concept_id for c in concepts],
        sample_size=len(parts),
        unavailable_tiers=list(detection.language_confidence.unavailable_tiers),
    )


def create_neuro_lingua(
    repo_root: Path | None = None,
    *,
    wal_path: Path | None = None,
    extra_providers: list[SemanticProvider] | None = None,
) -> NeuroLingua:
    config = load_neuro_lingua_config(repo_root)
    if wal_path is not None:
        config.wal_path = wal_path
        config.evolution_inbox_path = wal_path.parent / "evolution_inbox.jsonl"
    return NeuroLingua(config, extra_providers=extra_providers)


# Module-level default is lazy so imports stay side-effect free.
_default: NeuroLingua | None = None


def _default_kernel() -> NeuroLingua:
    global _default
    if _default is None:
        _default = create_neuro_lingua()
    return _default


async def interpret(
    text: str,
    context: InterpretationContext | dict[str, Any] | None = None,
    target_locale: str | None = None,
) -> InterpretationResult:
    return await _default_kernel().interpret(text=text, context=context, target_locale=target_locale)


async def realize(
    meaning: CognitiveMeaningPacket,
    target_locale: str,
    context: InterpretationContext | dict[str, Any] | None = None,
) -> RenderedOutput:
    return await _default_kernel().realize(meaning=meaning, target_locale=target_locale, context=context)
