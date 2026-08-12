import type { CompanyId } from "@/lib/intelligence/trade-corridors";

export type LocalBrainId = "GREENY_LIFE_EGYPT_BRAIN" | "GREENS_NATURE_UAE_BRAIN" | "GREEN_LINES_NORWAY_EU_BRAIN";
export type EscalationReason = "NEW_OPPORTUNITY" | "CROSS_COMPANY_TRADE" | "EXCEPTION_OR_ERROR" | "MATERIAL_COMMERCIAL_CHANGE" | "NEW_MARKET_OR_PRODUCT" | "HIGH_RISK_DECISION";

export const operatingBrains: Record<LocalBrainId, {
  company: CompanyId;
  name: string;
  territory: string;
  localAuthority: string[];
  examples: string[];
  cannotDecideAlone: string[];
}> = {
  GREENY_LIFE_EGYPT_BRAIN: {
    company: "GREENY_LIFE_EGYPT",
    name: "Greeny-Life Egypt Brain",
    territory: "Egypt",
    localAuthority: ["production planning", "packaging planning", "Egypt import and export preparation", "supplier and warehouse operations", "local opportunity detection"],
    examples: ["Egyptian natural products", "fish and technical assets from Norway/EU", "refrigerated trucks, cooling systems, engines, and spare parts when supported by a verified opportunity"],
    cannotDecideAlone: ["cross-company trade", "new market/product", "material price/supplier/shipping change", "regulatory exception", "payment or title transfer"],
  },
  GREENS_NATURE_UAE_BRAIN: {
    company: "GREENS_NATURE_UAE",
    name: "Greens Nature UAE Brain",
    territory: "UAE / GCC",
    localAuthority: ["UAE import preparation", "GCC distribution planning", "local customer and inventory operations", "re-export opportunity detection"],
    examples: ["UAE/GCC import, distribution, and re-export"],
    cannotDecideAlone: ["cross-company trade", "new market/product", "material price/supplier/shipping change", "regulatory exception", "payment or title transfer"],
  },
  GREEN_LINES_NORWAY_EU_BRAIN: {
    company: "GREEN_LINES_NORWAY_EU",
    name: "Green Lines Norway/EU Brain",
    territory: "Norway / EU",
    localAuthority: ["European sourcing", "local import/export/re-export preparation", "EU/Norway distribution planning", "destination compliance preparation", "local opportunity detection"],
    examples: ["seafood, machinery, technical assets, and verified European sourcing opportunities"],
    cannotDecideAlone: ["cross-company trade", "new market/product", "material price/supplier/shipping change", "regulatory exception", "payment or title transfer"],
  },
};

export const mastermindAuthority = {
  name: "MasterMind AI",
  role: "Primary decision intelligence and command authority",
  duties: ["route local-brain findings", "separate company/customer/option context", "compare alternatives", "request evidence", "create approval notification", "issue controlled command only after user approval"],
  prohibited: ["unapproved commercial execution", "payment execution", "customs filing", "legal title transfer", "self-modification"],
};

export function localBrainFor(company: CompanyId): LocalBrainId | null {
  return (Object.keys(operatingBrains) as LocalBrainId[]).find((id) => operatingBrains[id].company === company) ?? null;
}

export function escalationReasons(input: {
  originCompany: CompanyId;
  destinationCompany: CompanyId;
  eventType?: string;
  productId: string;
  destination: string;
}): EscalationReason[] {
  const reasons: EscalationReason[] = [];
  if (input.originCompany !== input.destinationCompany) reasons.push("CROSS_COMPANY_TRADE");
  const event = input.eventType?.trim().toUpperCase();
  if (event === "OPPORTUNITY") reasons.push("NEW_OPPORTUNITY");
  if (event === "ERROR" || event === "EXCEPTION") reasons.push("EXCEPTION_OR_ERROR");
  if (event === "PRICE" || event === "SUPPLIER" || event === "SHIPMENT" || event === "OFFER") reasons.push("MATERIAL_COMMERCIAL_CHANGE");
  if (event === "NEW_MARKET" || event === "NEW_PRODUCT") reasons.push("NEW_MARKET_OR_PRODUCT");
  if (!input.productId || !input.destination) reasons.push("HIGH_RISK_DECISION");
  return [...new Set(reasons)];
}

export function approvalNotification(input: {
  localBrain: LocalBrainId | null;
  escalation: EscalationReason[];
  recommendation: string;
  blockers: string[];
  alternatives: string[];
  proposedActions: string[];
}) {
  return {
    status: "PENDING_USER_APPROVAL",
    title: "MasterMind decision notification",
    from: input.localBrain ? operatingBrains[input.localBrain].name : "MasterMind AI",
    to: "User approval authority",
    escalation: input.escalation,
    recommendation: input.recommendation,
    alternatives: input.alternatives,
    blockers: input.blockers,
    proposedActions: input.proposedActions,
    editableFields: ["selectedAlternative", "priceAssumptions", "supplierChoice", "shipmentChoice", "destination", "requestedEvidence", "proposedActions"],
    executionRule: "Nothing executes until the user explicitly approves a reviewed and editable decision package.",
  };
}
