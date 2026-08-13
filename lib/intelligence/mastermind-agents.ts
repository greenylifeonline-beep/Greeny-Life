import { buildExportDecision } from "@/lib/intelligence/export-decision";
import { assetAssimilationRegistry, egyptianExportPortfolio } from "@/lib/intelligence/portfolio-and-assets";
import { assessCorridor, companies, type CompanyId } from "@/lib/intelligence/trade-corridors";
import { findLegacyBatch, legacyBatchRegistry } from "@/lib/intelligence/legacy-batch-traceability";
import { approvalNotification, escalationReasons, localBrainFor, mastermindAuthority } from "@/lib/intelligence/three-operating-brains";
import { customerContext } from "@/lib/intelligence/commercial-context-fabric";
import { commercialChangeReview } from "@/lib/intelligence/commercial-change-review";
import { prisma } from "@/lib/prisma";
import { assessOfficialExportEvidence, type OfficialEvidenceRecord } from "@/lib/intelligence/official-evidence-gate";

export type AgentStatus = "SUPPORTED" | "REVIEW_REQUIRED" | "NOT_READY";

export interface AgentFinding {
  agent: string;
  status: AgentStatus;
  summary: string;
  evidence: string[];
  blockers: string[];
  data: unknown;
}

export interface MasterMindRequest {
  productId: string;
  destination: string;
  originCompany: CompanyId;
  destinationCompany: CompanyId;
  actor: string;
  traceCode?: string;
  eventType?: string;
  customerId?: string;
}

const commercialCompanies = new Set<CompanyId>([
  "GREENY_LIFE_EGYPT",
  "GREENS_NATURE_UAE",
  "GREEN_LINES_NORWAY_EU",
]);

function statusFromExport(status: string): AgentStatus {
  return status === "NOT_READY" ? "NOT_READY" : "REVIEW_REQUIRED";
}

function mapOfficialEvidence(row: {
  evidenceKey: string; product: string; destination: string; authority: string;
  verificationStatus: string; claimStatus: string; validTo: Date | null; gates: unknown; sourceUrl: string | null;
}): OfficialEvidenceRecord {
  const validAuthorities = ["official", "secondary", "internal", "unknown"];
  const validVerificationStates = ["verified_current", "unverified", "expired", "unknown"];
  const validClaimStates = ["supported", "prohibited", "unknown"];
  const validGates = ["country_eligibility", "establishment_listing", "official_certificate", "border_process", "importer_registration"];
  return {
    id: row.evidenceKey,
    scope: { product: row.product, destination: row.destination },
    authority: validAuthorities.includes(row.authority) ? row.authority as OfficialEvidenceRecord["authority"] : "unknown",
    verificationStatus: validVerificationStates.includes(row.verificationStatus) ? row.verificationStatus as OfficialEvidenceRecord["verificationStatus"] : "unknown",
    claimStatus: validClaimStates.includes(row.claimStatus) ? row.claimStatus as OfficialEvidenceRecord["claimStatus"] : "unknown",
    validTo: row.validTo?.toISOString().slice(0, 10),
    gates: Array.isArray(row.gates) ? row.gates.filter((gate): gate is OfficialEvidenceRecord["gates"][number] => validGates.includes(String(gate))) : [],
    sourceUrl: row.sourceUrl ?? undefined,
  };
}

export async function evidenceComplianceAgent(productId: string, destination: string): Promise<AgentFinding> {
  const baseline = buildExportDecision(productId, destination);
  const stored = await prisma.officialEvidenceRegistry.findMany({ where: { product: productId.trim(), destination: destination.trim() }, orderBy: { updatedAt: "desc" } });
  const assessment = assessOfficialExportEvidence(stored.map(mapOfficialEvidence), productId, destination);
  const identityBlockers = baseline.findings
    .filter((item) => item.code === "PRODUCT_IDENTITY" || item.code === "SUPPLIER_LINK" || item.code === "MARKET")
    .filter((item) => item.state !== "SUPPORTED")
    .map((item) => item.message);
  return {
    agent: "EVIDENCE_COMPLIANCE",
    status: assessment.state === "SUPPORTED_BY_OFFICIAL_SOURCE" && !identityBlockers.length ? "REVIEW_REQUIRED" : "NOT_READY",
    summary: assessment.state === "SUPPORTED_BY_OFFICIAL_SOURCE" ? "Current official evidence covers regulatory gates; separate human and operational gates remain required." : "Official evidence is insufficient or blocked; export execution is not ready.",
    evidence: assessment.evidenceIds,
    blockers: [...identityBlockers, ...assessment.reasons, ...assessment.missingGates.map((gate) => `Official evidence gate missing: ${gate}`)],
    data: { baseline, assessment, persistedEvidenceCount: stored.length },
  };
}

export function productMarketAgent(productId: string, destination: string): AgentFinding {
  const portfolio = egyptianExportPortfolio();
  const product = portfolio.products.find((item) => item.id.toUpperCase() === productId.trim().toUpperCase());
  if (!product) {
    return { agent: "PRODUCT_MARKET", status: "NOT_READY", summary: "Product is absent from the canonical portfolio.", evidence: [portfolio.source], blockers: ["Canonical product identity is required."], data: null };
  }
  const destinationHint = destination.trim().toUpperCase();
  const marketEnabled = product.targetMarkets.some((market) => destinationHint.includes(market) || market.includes(destinationHint));
  return {
    agent: "PRODUCT_MARKET",
    status: marketEnabled ? "REVIEW_REQUIRED" : "NOT_READY",
    summary: marketEnabled ? "Product is internally marked for a related target market; external market evidence is still required." : "Destination is not represented in the product's internal target-market flags.",
    evidence: [portfolio.source, `Product ${product.id}`, `HS ${product.hsCode ?? "missing"}`],
    blockers: marketEnabled ? ["Internal market flags are not official market authorization."] : ["Market fit must be reviewed before commercial planning."],
    data: product,
  };
}

export async function tradeCorridorAgent(request: MasterMindRequest): Promise<AgentFinding> {
  if (!commercialCompanies.has(request.originCompany) || !commercialCompanies.has(request.destinationCompany)) {
    return { agent: "TRADE_CORRIDOR", status: "NOT_READY", summary: "MasterMind AI cannot be used as a commercial party.", evidence: ["TRADE-GOVERNANCE.md"], blockers: ["Origin and destination must be commercial companies."], data: null };
  }
  const assessment = await assessCorridor(request.originCompany, request.destinationCompany, "EXPORT", request.actor, request.productId);
  return {
    agent: "TRADE_CORRIDOR",
    status: assessment.status === "REVIEW_REQUIRED" ? "REVIEW_REQUIRED" : "NOT_READY",
    summary: assessment.recommendedAction,
    evidence: assessment.requirements,
    blockers: assessment.blockers,
    data: assessment,
  };
}

export function traceabilityAgent(traceCode?: string): AgentFinding {
  const registry = legacyBatchRegistry();
  if (!traceCode) {
    return { agent: "TRACEABILITY", status: "REVIEW_REQUIRED", summary: "No batch was supplied; traceability must be attached before shipment planning.", evidence: registry.sourceFiles, blockers: ["Provide a current ledger trace code or a historical batch reference."], data: { historicalBatchCount: registry.records.length } };
  }
  const legacy = findLegacyBatch(traceCode);
  if (!legacy) return { agent: "TRACEABILITY", status: "NOT_READY", summary: "Trace code is unknown to the consolidated historical registry.", evidence: registry.sourceFiles, blockers: ["Record a verified current traceability event before proceeding."], data: null };
  return {
    agent: "TRACEABILITY",
    status: "REVIEW_REQUIRED",
    summary: "Historical batch was found; its historic PASS label must be re-verified with current quality and custody evidence.",
    evidence: [legacy.source, legacy.batchCode, legacy.productId ?? "No product ID"],
    blockers: ["Historical batch status is not current quality or customs evidence."],
    data: legacy,
  };
}

export function systemLearningAgent(): AgentFinding {
  const assets = assetAssimilationRegistry();
  const active = assets.classes.ACTIVE_RUNTIME?.count ?? 0;
  const reusable = assets.classes.REUSABLE_SOURCE?.count ?? 0;
  return {
    agent: "SYSTEM_LEARNING",
    status: "REVIEW_REQUIRED",
    summary: "The system can identify reusable legacy assets, but it can only propose reviewed integrations; it cannot self-modify.",
    evidence: [assets.manifest, `${active} active runtime assets`, `${reusable} reusable source assets`],
    blockers: ["No automatic code, data, model, or policy modification is permitted."],
    data: { totalAssets: assets.totalAssets, classes: assets.classes },
  };
}

export function customerContextAgent(request: MasterMindRequest): AgentFinding {
  const context = customerContext(request);
  return {
    agent: "CUSTOMER_CONTEXT",
    status: context.status,
    summary: context.summary,
    evidence: context.evidence,
    blockers: context.blockers,
    data: context.data,
  };
}

export async function commercialChangeAgent(request: MasterMindRequest): Promise<AgentFinding> {
  const review = await commercialChangeReview(request.productId);
  return {
    agent: "COMMERCIAL_CHANGE_REVIEW",
    status: review.status,
    summary: review.summary,
    evidence: review.evidence,
    blockers: review.blockers,
    data: review.data,
  };
}

export async function buildMasterMindDecisionPackage(request: MasterMindRequest) {
  const agents = [
    await evidenceComplianceAgent(request.productId, request.destination),
    productMarketAgent(request.productId, request.destination),
    await tradeCorridorAgent(request),
    traceabilityAgent(request.traceCode),
    customerContextAgent(request),
    await commercialChangeAgent(request),
    systemLearningAgent(),
  ];
  const blockers = agents.flatMap((agent) => agent.blockers.map((blocker) => `${agent.agent}: ${blocker}`));
  const notReady = agents.some((agent) => agent.status === "NOT_READY");
  const localBrain = localBrainFor(request.originCompany);
  const escalation = escalationReasons(request);
  const recommendation = notReady ? "Hold. Complete missing evidence, traceability, and commercial approvals." : "Submit the complete decision package to an authorized human reviewer.";
  return {
    system: "MasterMind AI",
    mode: "READ_ONLY_DECISION_INTELLIGENCE",
    primaryAuthority: mastermindAuthority,
    operatingContext: localBrain ? { localBrain, definition: (await import("@/lib/intelligence/three-operating-brains")).operatingBrains[localBrain] } : null,
    escalation,
    authority: companies.MASTERMIND.authority,
    prohibited: companies.MASTERMIND.prohibited,
    decision: {
      status: notReady ? "NOT_READY" : "REQUIRES_HUMAN_REVIEW",
      automaticExecution: false,
      recommendedAction: recommendation,
    },
    request,
    agents,
    blockers,
    approvalNotification: approvalNotification({
      localBrain,
      escalation,
      recommendation,
      blockers,
      alternatives: ["Hold and collect evidence", "Choose a different verified supplier/route", "Defer or reject the opportunity"],
      proposedActions: ["Collect official evidence", "Validate commercial terms", "Submit revised package for user approval"],
    }),
    auditRule: "Local brains manage their own operating context. MasterMind AI is the primary decision authority and command router. Every agent is read-only; user approval is required before controlled operational execution.",
  };
}
