/**
 * Greeny-Life Intelligence Adapter
 *
 * Purpose:
 * - Execute registered intelligence capabilities
 * - Return derived findings
 * - Never mutate Master Data
 */

export interface IntelligenceRequest {
    capability: string;
    input: unknown;
    correlationId: string;
}

export interface IntelligenceResult {
    capability: string;
    correlationId: string;
    status: "SUCCESS" | "FAILED";
    findings: unknown[];
    executedAt: string;
}

export interface IntelligenceCapability {
    name: string;
    execute(input: unknown): Promise<unknown[]>;
}

export class IntelligenceAdapter {

    private readonly capabilities: Map<
        string,
        IntelligenceCapability
    >;

    constructor(
        capabilities: IntelligenceCapability[]
    ) {
        this.capabilities = new Map(
            capabilities.map(
                capability => [
                    capability.name,
                    capability
                ]
            )
        );
    }

    async execute(
        request: IntelligenceRequest
    ): Promise<IntelligenceResult> {

        const capability =
            this.capabilities.get(
                request.capability
            );

        if (!capability) {
            return {
                capability: request.capability,
                correlationId: request.correlationId,
                status: "FAILED",
                findings: [
                    {
                        code: "CAPABILITY_NOT_REGISTERED"
                    }
                ],
                executedAt:
                    new Date().toISOString()
            };
        }

        try {

            const findings =
                await capability.execute(
                    request.input
                );

            return {
                capability:
                    request.capability,

                correlationId:
                    request.correlationId,

                status: "SUCCESS",

                findings,

                executedAt:
                    new Date().toISOString()
            };

        } catch (error) {

            return {
                capability:
                    request.capability,

                correlationId:
                    request.correlationId,

                status: "FAILED",

                findings: [
                    {
                        code:
                            "INTELLIGENCE_EXECUTION_ERROR",

                        error:
                            error instanceof Error
                                ? error.message
                                : String(error)
                    }
                ],

                executedAt:
                    new Date().toISOString()
            };
        }
    }
}
