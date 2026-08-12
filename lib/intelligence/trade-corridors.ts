import { ControlledRuntimeOrchestrator } from "@/canonical/intelligence/runtime/controlled-runtime-orchestrator";

export const companies = {
  MASTERMIND: { name: "MasterMind AI", territory: "Decision intelligence", authority: ["analyze", "recommend", "govern", "orchestrate"], prohibited: ["commercial_counterparty", "payment_execution", "customs_filing", "title_transfer"] },
  GREENY_LIFE_EGYPT: { name: "Greeny-Life Egypt", territory: "Egypt", authority: ["production", "supplier_management", "origin_documents", "egypt_export_preparation"] },
  GREENS_NATURE_UAE: { name: "Greens Nature", territory: "UAE / GCC", authority: ["uae_import_review", "gcc_distribution_review", "settlement_review", "reexport_review"] },
  GREEN_LINES_NORWAY_EU: { name: "Green Lines", territory: "Norway / EU", authority: ["european_sourcing", "norway_eu_import_review", "destination_compliance_review", "distribution_review"] },
} as const;

export type CompanyId = keyof typeof companies;
const commercial = new Set<CompanyId>(["GREENY_LIFE_EGYPT", "GREENS_NATURE_UAE", "GREEN_LINES_NORWAY_EU"]);

const requirements: Record<string, string[]> = {
  "GREENY_LIFE_EGYPT:GREENS_NATURE_UAE": ["Egypt export authorization", "UAE importer authorization", "official UAE/GCC compliance evidence", "approved intercompany terms", "approved shipping and settlement"],
  "GREENY_LIFE_EGYPT:GREEN_LINES_NORWAY_EU": ["Egypt export authorization", "Norway/EU importer authorization", "official destination compliance evidence", "approved intercompany terms", "approved shipping and settlement"],
  "GREEN_LINES_NORWAY_EU:GREENY_LIFE_EGYPT": ["Norway/EU export authorization", "Egypt importer authorization", "official Egypt import evidence", "approved intercompany terms", "approved cold-chain shipping"],
  "GREEN_LINES_NORWAY_EU:GREENS_NATURE_UAE": ["Norway/EU export authorization", "UAE importer authorization", "official UAE compliance evidence", "approved intercompany terms", "approved cold-chain shipping"],
  "GREENS_NATURE_UAE:GREENY_LIFE_EGYPT": ["UAE export/re-export authorization", "Egypt importer authorization", "official Egypt import evidence", "approved intercompany terms", "approved shipping and settlement"],
  "GREENS_NATURE_UAE:GREEN_LINES_NORWAY_EU": ["UAE export/re-export authorization", "Norway/EU importer authorization", "official destination compliance evidence", "approved intercompany terms", "approved shipping and settlement"],
};

export function tradeGovernance() {
  return { policyStatus: "PROPOSED_PENDING_LEGAL_ENTITY_AND_AUTHORITY_APPROVAL", companies, corridors: Object.entries(requirements).map(([route, required]) => { const [originCompany, destinationCompany] = route.split(":"); return { originCompany, destinationCompany, required, automaticExecution: false }; }) };
}

export async function assessCorridor(originCompany: CompanyId, destinationCompany: CompanyId, tradeType: string, actor: string, productId?: string) {
  const key = `${originCompany}:${destinationCompany}`;
  const governance = await new ControlledRuntimeOrchestrator().execute({ operation: `trade-corridor:${tradeType}:${key}`, actor, riskLevel: "HIGH" });
  const blockers = [
    ...(originCompany === destinationCompany ? ["Origin and destination must be separate legal companies."] : []),
    ...(!commercial.has(originCompany) || !commercial.has(destinationCompany) ? ["MasterMind AI cannot be a commercial counterparty."] : []),
    ...(requirements[key] ? [] : ["No proposed corridor exists for this company pair."]),
    "Legal entity authorization and official import/export evidence are not connected to the runtime.",
    "Approved commercial terms, price, shipment quote, and payment/settlement terms are missing.",
  ];
  return { status: "REVIEW_REQUIRED", automaticExecution: false, governance, route: { originCompany, destinationCompany, tradeType, productId: productId ?? null }, requirements: requirements[key] ?? [], blockers, recommendedAction: "Hold. Complete evidence and obtain authorized human approval before shipment, invoice, customs filing, or payment." };
}
