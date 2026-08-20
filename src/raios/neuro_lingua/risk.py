from dataclasses import dataclass

from .schema import RiskLevel


@dataclass(frozen=True)
class VerificationPlan:
    semantic_similarity: bool
    entity_lock: bool
    number_lock: bool
    terminology_lock: bool
    independent_verification: bool
    back_translation: bool


def verification_plan(risk: RiskLevel) -> VerificationPlan:

    if risk == RiskLevel.LOW:
        return VerificationPlan(
            semantic_similarity=False,
            entity_lock=False,
            number_lock=True,
            terminology_lock=False,
            independent_verification=False,
            back_translation=False,
        )

    if risk == RiskLevel.MEDIUM:
        return VerificationPlan(
            semantic_similarity=True,
            entity_lock=True,
            number_lock=True,
            terminology_lock=True,
            independent_verification=False,
            back_translation=False,
        )

    if risk == RiskLevel.HIGH:
        return VerificationPlan(
            semantic_similarity=True,
            entity_lock=True,
            number_lock=True,
            terminology_lock=True,
            independent_verification=True,
            back_translation=False,
        )

    return VerificationPlan(
        semantic_similarity=True,
        entity_lock=True,
        number_lock=True,
        terminology_lock=True,
        independent_verification=True,
        back_translation=True,
    )
