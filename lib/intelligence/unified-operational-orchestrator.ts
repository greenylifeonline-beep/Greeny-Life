import {
  buildMasterMindDecisionPackage,
  type MasterMindRequest,
} from "./mastermind-agents";

import {
  greenyLifeEgyptBrainIdentity,
  greenyLifeEgyptOperationalView,
} from "./greeny-life-egypt-brain";

export type ProjectBrainAvailability =
  | "AVAILABLE"
  | "UNAVAILABLE"
  | "ERROR";

export interface UnifiedProjectBrainContribution {
  brainId: string;
  availability: ProjectBrainAvailability;
  verified: boolean;
  contribution: unknown | null;
  reason: string | null;
}

export interface UnifiedOperationalResult {
  system: "RAIOS Unified Operational Orchestrator";
  mode: "CONDITIONAL_CONVERGENCE";

  request: {
    productId: string;
    destination: string;
    actor: string;
  };

  projectBrains: {
    egypt: UnifiedProjectBrainContribution;
    uae: UnifiedProjectBrainContribution;
    norway: UnifiedProjectBrainContribution;
  };

  mastermind: Awaited<
    ReturnType<typeof buildMasterMindDecisionPackage>
  >;

  unifiedDecision: {
    status:
      Awaited<
        ReturnType<typeof buildMasterMindDecisionPackage>
      >["decision"]["status"];

    automaticExecution: boolean;
    blockers: string[];
  };
}

/**
 * First functional GL-005 vertical slice.
 *
 * Runtime truth:
 * - Egypt is the only verified project-brain runtime.
 * - UAE and Norway have no verified runtime bridge/source yet.
 *
 * Missing brains are represented explicitly and do not prevent
 * verified brains or MasterMind from contributing.
 */
export async function buildUnifiedOperationalResult(
  request: MasterMindRequest,
): Promise<UnifiedOperationalResult> {

  const egyptOperationalView =
    greenyLifeEgyptOperationalView(request.productId);

  const mastermind =
    await buildMasterMindDecisionPackage(request);

  return {
    system: "RAIOS Unified Operational Orchestrator",
    mode: "CONDITIONAL_CONVERGENCE",

    request: {
      productId: request.productId,
      destination: request.destination,
      actor: request.actor,
    },

    projectBrains: {
      egypt: {
        brainId: "GREENY_LIFE_EGYPT",
        availability: "AVAILABLE",
        verified: true,
        contribution: {
          identity: greenyLifeEgyptBrainIdentity,
          operationalView: egyptOperationalView,
        },
        reason: null,
      },

      uae: {
        brainId: "GREENS_NATURE_UAE",
        availability: "UNAVAILABLE",
        verified: false,
        contribution: null,
        reason: "NO_VERIFIED_RUNTIME_SOURCE_OR_BRIDGE",
      },

      norway: {
        brainId: "GREEN_LINES_NORWAY_EU",
        availability: "UNAVAILABLE",
        verified: false,
        contribution: null,
        reason: "NO_VERIFIED_RUNTIME_SOURCE_OR_BRIDGE",
      },
    },

    mastermind,

    unifiedDecision: {
      status: mastermind.decision.status,
      automaticExecution:
        mastermind.decision.automaticExecution,
      blockers: [...mastermind.blockers],
    },
  };
}