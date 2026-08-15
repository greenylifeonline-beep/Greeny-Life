/**
 * Greeny-Life GL-DOS Governance Gate
 *
 * No controlled execution should pass
 * without governance authorization.
 */

export type GovernanceDecision =
    | "AUTHORIZED"
    | "DENIED"
    | "REVIEW_REQUIRED";

export interface GovernanceRequest {
    operation: string;
    actor: string;
    correlationId: string;
    riskLevel: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
}

export interface GovernanceResult {
    decision: GovernanceDecision;
    correlationId: string;
    reason: string;
    evaluatedAt: string;
}

export class GLDOSGovernanceGate {

    evaluate(
        request: GovernanceRequest
    ): GovernanceResult {

        if (
            request.riskLevel === "CRITICAL"
        ) {
            return {
                decision: "DENIED",
                correlationId:
                    request.correlationId,
                reason:
                    "CRITICAL operations require explicit human authorization.",
                evaluatedAt:
                    new Date().toISOString()
            };
        }

        if (
            request.riskLevel === "HIGH"
        ) {
            return {
                decision: "REVIEW_REQUIRED",
                correlationId:
                    request.correlationId,
                reason:
                    "HIGH risk operation requires governance review.",
                evaluatedAt:
                    new Date().toISOString()
            };
        }

        return {
            decision: "AUTHORIZED",
            correlationId:
                request.correlationId,
            reason:
                "Operation passed GL-DOS baseline governance checks.",
            evaluatedAt:
                new Date().toISOString()
        };
    }
}
