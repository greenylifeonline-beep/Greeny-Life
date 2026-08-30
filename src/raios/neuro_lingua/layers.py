"""Four-layer NeuroLingua. Auto-wiring. No Cognitive WAL. No spaCy add."""
from __future__ import annotations

from typing import Any

from .ops_compile import auto_compile

LAYERS = ("L1", "L2", "L3", "L4")

LAYER_SPEC = {
    "L1": {
        "name": "FAST_LINGUISTIC_CPU",
        "must": [
            "language_id",
            "dialect_id",
            "tokenization",
            "ner",
            "dates",
            "money",
            "units",
            "codes",
            "regex",
            "normalization",
            "morphology",
        ],
        "live_here": ["language_id", "dialect_id", "tokenization", "codes", "regex", "normalization"],
        "absent_here": ["morphology", "dedicated_dates", "dedicated_money", "dedicated_units"],
        "packages_added": [],
        "reuse": ["language.py", "dialect.py", "protected.py", "code_switch.py"],
    },
    "L2": {
        "name": "SEMANTIC_NLP",
        "must": [
            "embeddings",
            "semantic_similarity",
            "intent",
            "relation_extraction",
            "terminology_mapping",
            "cross_lingual_alignment",
            "entity_linking",
            "domain_concept_mapping",
        ],
        "live_here": ["intent", "terminology_mapping", "domain_concept_mapping"],
        "absent_here": ["embeddings", "vector_similarity"],
        "packages_added": [],
        "reuse": ["concepts.py", "customer.py", "ops_compile.py"],
    },
    "L3": {
        "name": "DEEP_LANGUAGE_BRAIN",
        "must": ["deep_interpretation", "ambiguity", "pragmatics", "reasoning", "generation", "multilingual_transfer"],
        "live_here": [],
        "hold_here": ["main_cortex_via_model_gateway"],
        "absent_here": ["live_cortex_generate"],
        "packages_added": [],
        "reuse": ["governor.py", "router.py", "qwen_runtime.py", "cortex.py"],
        "law": ["NO_HARD_MODEL_FAMILY", "MODEL_GATEWAY_ONLY", "HOLD_NE_THROW"],
    },
    "L4": {
        "name": "NEUROLINGUA_COMPILER",
        "must": ["human_language", "canonical_meaning", "reasoning_representation", "target_language"],
        "live_here": ["human_language", "canonical_meaning", "target_language"],
        "packages_added": [],
        "reuse": ["ops_compile.py", "realize.py"],
    },
}


def classify_layer(layer_id: str, *, tested: bool = False, proven: bool = False) -> dict[str, Any]:
    spec = LAYER_SPEC[layer_id]
    if proven:
        status = "PROVEN"
    elif tested:
        status = "TESTED"
    elif spec.get("live_here"):
        status = "CONNECTED"
    elif spec.get("hold_here"):
        status = "STUB" if layer_id == "L3" else "FILE_ONLY"
    else:
        status = "ABSENT"
    if layer_id == "L3":
        status = "HOLD" if not proven else "PROVEN"
    return {
        "layer": layer_id,
        "name": spec["name"],
        "status": status,
        "live_capabilities": spec.get("live_here") or [],
        "absent_capabilities": spec.get("absent_here") or [],
        "packages_added": [],
        "proven": bool(proven),
        "gl005_proven": False,
    }


def auto_pipeline(text: str, *, target_locale: str | None = None) -> dict[str, Any]:
    """Normal path: one call, no manual layer invocation, no WAL."""
    return auto_compile(text, target_locale=target_locale)
