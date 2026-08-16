import {
  buildMasterMindDecisionPackage,
  type AgentFinding,
  type MasterMindRequest,
} from "./mastermind-agents";

import {
  greenyLifeEgyptBrainIdentity,
  greenyLifeEgyptOperationalView,
} from "./greeny-life-egypt-brain";

import {
  customerContext,
} from "./commercial-context-fabric";


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


export interface UnifiedOperationalSources {
  egypt: {
    source: "GREENY_LIFE_EGYPT_BRAIN";
    status: "AVAILABLE";
    contribution: unknown;
  };

  commercialContext: {
    source: "CANONICAL_CUSTOMER_DOMAIN";
    status: string;
    contribution: ReturnType<typeof customerContext>;
  };

  tradeCorridor: {
    source: "MASTERMIND_TRADE_CORRIDOR_AGENT";
    status: AgentFinding["status"] | "UNAVAILABLE";
    contribution: AgentFinding | null;
  };
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

  operationalSources: UnifiedOperationalSources;

  mastermind:
    Awaited<
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


export async function buildUnifiedOperationalResult(
  request: MasterMindRequest,
): Promise<UnifiedOperationalResult> {

  // ----------------------------------------------------------
  // Source 1: verified Egypt operational intelligence
  // ----------------------------------------------------------

  const egyptOperationalView =
    greenyLifeEgyptOperationalView(
      request.productId,
    );


  // ----------------------------------------------------------
  // Source 2: canonical commercial/customer context
  // ----------------------------------------------------------

  const commercialContext =
    customerContext({
      customerId:
        request.customerId,

      productId:
        request.productId,

      destination:
        request.destination,

      destinationCompany:
        request.destinationCompany,
    });


  // ----------------------------------------------------------
  // MasterMind runs ONCE.
  //
  // Important:
  // tradeCorridorAgent() invokes assessCorridor(), which invokes
  // ControlledRuntimeOrchestrator.
  //
  // GL-005 intentionally does NOT call assessCorridor() again.
  // ----------------------------------------------------------

  const mastermind =
    await buildMasterMindDecisionPackage(
      request,
    );


  const tradeCorridor =
    mastermind.agents.find(
      (agent) =>
        agent.agent === "TRADE_CORRIDOR",
    ) ?? null;


  return {
    system:
      "RAIOS Unified Operational Orchestrator",

    mode:
      "CONDITIONAL_CONVERGENCE",

    request: {
      productId:
        request.productId,

      destination:
        request.destination,

      actor:
        request.actor,
    },


    projectBrains: {
      egypt: {
        brainId:
          "GREENY_LIFE_EGYPT",

        availability:
          "AVAILABLE",

        verified:
          true,

        contribution: {
          identity:
            greenyLifeEgyptBrainIdentity,

          operationalView:
            egyptOperationalView,
        },

        reason:
          null,
      },


      uae: {
        brainId:
          "GREENS_NATURE_UAE",

        availability:
          "UNAVAILABLE",

        verified:
          false,

        contribution:
          null,

        reason:
          "NO_VERIFIED_RUNTIME_SOURCE_OR_BRIDGE",
      },


      norway: {
        brainId:
          "GREEN_LINES_NORWAY_EU",

        availability:
          "UNAVAILABLE",

        verified:
          false,

        contribution:
          null,

        reason:
          "NO_VERIFIED_RUNTIME_SOURCE_OR_BRIDGE",
      },
    },


    operationalSources: {

      egypt: {
        source:
          "GREENY_LIFE_EGYPT_BRAIN",

        status:
          "AVAILABLE",

        contribution:
          egyptOperationalView,
      },


      commercialContext: {
        source:
          "CANONICAL_CUSTOMER_DOMAIN",

        status:
          commercialContext.status,

        contribution:
          commercialContext,
      },


      tradeCorridor: {
        source:
          "MASTERMIND_TRADE_CORRIDOR_AGENT",

        status:
          tradeCorridor?.status ??
          "UNAVAILABLE",

        contribution:
          tradeCorridor,
      },
    },


    mastermind,


    unifiedDecision: {
      status:
        mastermind.decision.status,

      automaticExecution:
        mastermind.decision
          .automaticExecution,

      blockers:
        [...mastermind.blockers],
    },
  };
}