/**
 * Greeny-Life Controlled Runtime Orchestrator
 *
 * Execution flow:
 *
 * REQUEST
 *    ↓
 * CONTEXT
 *    ↓
 * MASTER DATA
 *    ↓
 * INTELLIGENCE
 *    ↓
 * BRAIN DECISION
 *    ↓
 * GL-DOS GOVERNANCE
 *    ↓
 * CONTROLLED EXECUTION
 *    ↓
 * TRACE
 *    ↓
 * REPORT
 */

import crypto from "crypto";

import {
    GLDOSGovernanceGate
} from "../adapters/gl-dos-governance-gate";

export interface RuntimeRequest {
    operation: string;
    actor: string;
    riskLevel:
        | "LOW"
        | "MEDIUM"
        | "HIGH"
        | "CRITICAL";

    input?: unknown;
}

export interface RuntimeResult {
    correlationId: string;
    status:
        | "AUTHORIZED"
        | "DENIED"
        | "REVIEW_REQUIRED";

    governanceReason: string;

    executedAt: string;
}

export class ControlledRuntimeOrchestrator {

    private readonly governance:
        GLDOSGovernanceGate;

    constructor() {

        this.governance =
            new GLDOSGovernanceGate();
    }

    async execute(
        request: RuntimeRequest
    ): Promise<RuntimeResult> {

        const correlationId =
            crypto
                .randomUUID();

        const governanceResult =
            this.governance.evaluate({
                operation:
                    request.operation,

                actor:
                    request.actor,

                correlationId,

                riskLevel:
                    request.riskLevel
            });

        return {

            correlationId,

            status:
                governanceResult.decision,

            governanceReason:
                governanceResult.reason,

            executedAt:
                new Date()
                    .toISOString()
        };
    }
}
