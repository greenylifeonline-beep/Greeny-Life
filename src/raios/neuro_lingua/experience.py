"""Self-learning equation. Not a second mind. No promotion. No WAL. No LLM dump."""
from __future__ import annotations

from typing import Any


WEIGHTS = {"E": 0.30, "R": 0.25, "V": 0.25, "G": 0.20}
LIVE_THRESHOLD = 0.20
PROMOTION_THRESHOLD = 0.98  # CORE_ELIGIBLE only; this runner never promotes
REPAIR_SAFETY_THRESHOLD = 0.75

LADDER = (
    "REJECTED",
    "DISCOVERED",
    "VALIDATED",
    "PRACTICED",
    "REPRODUCED",
    "PROVEN",
    "CORE_ELIGIBLE",
)

LAWS = (
    "EXPERIENCE_NE_KNOWLEDGE",
    "KNOWLEDGE_IS_VALIDATED_REPEATED_EVIDENCE",
    "PROOF_BEFORE_MEMORY",
    "REPRODUCTION_BEFORE_REPAIR",
    "MEASURED_CAPABILITY_BEFORE_AUTONOMY",
    "ONE_SUCCESS_NE_CAPABILITY",
    "LLM_SAVE_NE_LEARNING",
    "MS_NE_UNDERSTANDING_SPEED",
    "CORE_KNOWLEDGE_REQUIRES_C1",
    "CK_BELOW_THETA_NE_PROMOTE",
)


def clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def confidence(evidence: float, reproducibility: float, verification: float, generalization: float) -> float:
    e, r, v, g = clamp(evidence), clamp(reproducibility), clamp(verification), clamp(generalization)
    return round(WEIGHTS["E"] * e + WEIGHTS["R"] * r + WEIGHTS["V"] * v + WEIGHTS["G"] * g, 4)


def rung(ck: float, *, reproduced: bool) -> str:
    ck = clamp(ck)
    if ck < 0.40:
        return "REJECTED"
    if ck < 0.60:
        return "DISCOVERED"
    if ck < 0.75:
        return "VALIDATED"
    if not reproduced:
        return "PRACTICED"
    if ck < 0.90:
        return "REPRODUCED"
    if ck < 0.98:
        return "PROVEN"
    return "CORE_ELIGIBLE"


def may_store_as_memory(ck: float, *, verified: bool, reproduced: bool) -> bool:
    return verified and reproduced and ck >= 0.60


def may_promote(ck: float, *, verified: bool, reproduced: bool, owner_approved: bool) -> bool:
    return False if not owner_approved else bool(verified and reproduced and ck >= PROMOTION_THRESHOLD)


def may_repair(*, reproduced: bool, rollback_available: bool, safety: float) -> bool:
    return reproduced and rollback_available and clamp(safety) >= REPAIR_SAFETY_THRESHOLD


def route_path(*, complexity: float, risk: float, novelty: float, ck: float, deep_available: bool) -> dict[str, Any]:
    if ck > 0.92 and risk < LIVE_THRESHOLD:
        path = "FAST"
    elif complexity > 0.70 or novelty > 0.60:
        path = "DEEP"
    else:
        path = "STANDARD"
    available = True
    reason = "deterministic-neuro-lingua"
    if path == "DEEP" and not deep_available:
        available = False
        reason = "DEEP_PATH_UNAVAILABLE_NO_QWEN_OLLAMA"
        path = "FAST_FALLBACK"
    return {"path": path, "available": available, "reason": reason, "deep_available": deep_available}


def learning_score(
    observation: float,
    understanding: float,
    action: float,
    verification: float,
    retention: float,
    generalization: float,
) -> float:
    factors = (
        clamp(observation),
        clamp(understanding),
        clamp(action),
        clamp(verification),
        clamp(retention),
        clamp(generalization),
    )
    if any(v <= 0 for v in factors):
        return 0.0
    product = 1.0
    for value in factors:
        product *= value
    return round(product, 6)


def usi(*, correctness: float, generalization: float, reusability: float, time_s: float, error_cycles: int) -> float:
    numer = clamp(correctness) * clamp(generalization) * clamp(reusability)
    denom = max(float(time_s), 1e-6) * max(int(error_cycles), 1)
    return round(numer / denom, 6)


def experience(
    *,
    observation: Any,
    context: Any,
    reasoning: Any,
    action: Any,
    verification: Any,
    feedback: Any,
    evidence: float,
    reproducibility: float,
    verification_score: float,
    generalization: float,
    reproduced: bool,
    verified: bool,
) -> dict[str, Any]:
    ck = confidence(evidence, reproducibility, verification_score, generalization)
    rank = rung(ck, reproduced=reproduced)
    return {
        "schema": "raios.experience.v1",
        "E_t": {
            "O": observation,
            "C": context,
            "R": reasoning,
            "A": action,
            "V": verification,
            "F": feedback,
        },
        "Ck": ck,
        "weights": dict(WEIGHTS),
        "rung": rank,
        "reproduced": reproduced,
        "verified": verified,
        "knowledge": False,
        "promoted": False,
        "canonical": False,
        "gl005_proven": False,
        "may_store_memory": may_store_as_memory(ck, verified=verified, reproduced=reproduced),
        "may_promote": False,
        "may_repair": may_repair(reproduced=reproduced, rollback_available=True, safety=verification_score),
        "law": list(LAWS),
        "identity": "Experience is not knowledge. Knowledge = Validated(Repeated(Evidence)).",
    }


def bind_from_proof(proof: dict[str, Any]) -> dict[str, Any]:
    cycle = proof.get("cycle") or {}
    gates = {g.get("gate"): g.get("status") for g in proof.get("gates") or []}
    live_ok = all(gates.get(name) == "PASS_CANDIDATE" for name in ("execution", "real_io", "live_guard"))
    existence_fail = gates.get("existence") == "FAIL"
    gl_blocked = gates.get("gl005_proof") in {"BLOCKED", "FAIL", "UNPROVEN"}
    reproduced = bool((cycle.get("replay") or {}).get("proof_rerunnable")) and live_ok
    evidence = 0.55 if live_ok else 0.25
    if existence_fail:
        evidence = min(evidence, 0.45)
    verification_score = 0.55 if live_ok else 0.2
    if gl_blocked:
        verification_score = min(verification_score, 0.5)
    reproducibility = 0.7 if reproduced else 0.2
    generalization = 0.25
    rec = experience(
        observation=cycle.get("observe"),
        context={"meeting": proof.get("meeting_id"), "case": proof.get("case")},
        reasoning=cycle.get("reason"),
        action=cycle.get("act_shadow"),
        verification=cycle.get("verify"),
        feedback={"gl005_status": proof.get("gl005_status"), "existence_fail": existence_fail},
        evidence=evidence,
        reproducibility=reproducibility,
        verification_score=verification_score,
        generalization=generalization,
        reproduced=reproduced,
        verified=live_ok and not existence_fail,
    )
    rec["gates"] = gates
    rec["path"] = route_path(
        complexity=0.4,
        risk=0.85 if gl_blocked else 0.3,
        novelty=0.2,
        ck=rec["Ck"],
        deep_available=False,
    )
    rec["failure_receipt"] = None
    if existence_fail or gates.get("gl005_proof") == "FAIL":
        rec["failure_receipt"] = {
            "case_id": proof.get("case"),
            "expected": "claimed scripts exist and GL-005 authenticated mutation",
            "actual": f"existence={gates.get('existence')} gl005={gates.get('gl005_proof')}",
            "reproducible": True,
            "promotion_status": "REJECTED",
            "root_cause": "NAMED_SCRIPT_NE_EXISTING_SCRIPT" if existence_fail else "AUTH_GATE_OR_UNPROVEN",
        }
    return rec
