import fs from "fs";
import path from "path";
import { prisma } from "@/lib/prisma";
import { assessOfficialExportEvidence, type EvidenceGateAssessment } from "@/lib/intelligence/official-evidence-gate";
import { mapPersistedOfficialEvidence, type PersistedOfficialEvidenceRow } from "@/lib/intelligence/persisted-official-evidence";

type EvidenceState = "SUPPORTED" | "MISSING" | "SELF_DECLARED";
type DecisionStatus = "REQUIRES_HUMAN_REVIEW" | "NOT_READY";

interface ProductRecord {
  id: string;
  product_code: string;
  category: string;
  name?: { en?: string; ar?: string };
  global_specs?: { hs_code?: string; required_certificates?: string[] };
}

interface SupplierRecord {
  supplier_id: string;
  name: string;
  country: string;
  capabilities?: { export_ready?: boolean };
}

interface Finding {
  code: string;
  state: EvidenceState;
  message: string;
  source: string;
}

type CommercialChangeForReadiness = {
  domain: string;
  status: string;
  effectiveFrom: Date | null;
  effectiveTo: Date | null;
  payload: unknown;
};

type CommercialReadiness = {
  supported: boolean;
  missingDomains: string[];
  conflictingDomains: string[];
  reasons: string[];
};

const requiredCommercialDomains = ["PRICE", "SHIPMENT", "OFFER"] as const;

function commercialRecordMatchesDestination(payload: unknown, destinationKey: string): boolean {
  if (typeof payload !== "object" || payload === null || Array.isArray(payload)) return false;
  const destination = (payload as Record<string, unknown>).destination;
  return typeof destination === "string" && destination.trim().toLowerCase() === destinationKey;
}

// Pure, fail-closed evaluator for records that already exist in CommercialChange.
// It does not approve a price, quote, shipment, or offer, and it never writes data.
export function assessCommercialReadiness(
  changes: CommercialChangeForReadiness[],
  destination: string,
  now = new Date(),
): CommercialReadiness {
  const destinationKey = destination.trim().toLowerCase();
  const currentApprovedDomains = changes
    .filter((change) =>
      change.status === "APPROVED" &&
      (!change.effectiveFrom || change.effectiveFrom <= now) &&
      (!change.effectiveTo || change.effectiveTo >= now) &&
      commercialRecordMatchesDestination(change.payload, destinationKey),
    )
    .map((change) => change.domain.trim().toUpperCase());
  const activeDomainCounts = new Map<string, number>();
  for (const domain of currentApprovedDomains) activeDomainCounts.set(domain, (activeDomainCounts.get(domain) ?? 0) + 1);
  const supportedDomains = new Set(currentApprovedDomains);
  const missingDomains = requiredCommercialDomains.filter((domain) => !supportedDomains.has(domain));
  const conflictingDomains = requiredCommercialDomains.filter((domain) => (activeDomainCounts.get(domain) ?? 0) > 1);
  const reasons = [
    ...missingDomains.map((domain) => `No current approved ${domain} commercial record is attached to this product.`),
    ...conflictingDomains.map((domain) => `More than one current approved ${domain} commercial record is attached to this product; a human must resolve the canonical record.`),
  ];
  return {
    supported: missingDomains.length === 0 && conflictingDomains.length === 0,
    missingDomains,
    conflictingDomains,
    reasons,
  };
}

function readJson<T>(relativePath: string): T {
  return JSON.parse(fs.readFileSync(path.join(process.cwd(), relativePath), "utf8")) as T;
}

export function buildExportDecision(productId: string, destination: string) {
  const productMaster = readJson<{ products: ProductRecord[] }>("canonical/data/master_products.json");
  const supplierMaster = readJson<{ suppliers: SupplierRecord[] }>("canonical/data/suppliers.json");
  const supplierLinks = readJson<{ links: Array<{ product_id: string; supplier_id: string; status: string }> }>("canonical/data/supplier-product-links.json");
  const markets = readJson<{ target_markets: Array<{ country: string; region: string; priority: number; status: string }>; export_requirements: Record<string, string[]> }>("canonical/business/markets.json");
  const globalSpecs = readJson<{ required_certificates: string[] }>("canonical/business/global_specs.json");
  const productKey = productId.trim().toUpperCase();
  const destinationKey = destination.trim().toLowerCase();
  const product = productMaster.products.find((item) => item.id.toUpperCase() === productKey);
  const market = markets.target_markets.find((item) => item.country.toLowerCase() === destinationKey);
  const link = supplierLinks.links.find((item) => item.product_id.toUpperCase() === productKey && item.status === "active");
  const supplier = link ? supplierMaster.suppliers.find((item) => item.supplier_id === link.supplier_id) : undefined;
  const findings: Finding[] = [];

  if (!product) {
    findings.push({ code: "PRODUCT_IDENTITY", state: "MISSING", message: "Product is not in the canonical product master.", source: "canonical/data/master_products.json" });
  } else {
    findings.push({ code: "PRODUCT_IDENTITY", state: "SUPPORTED", message: `Canonical product ${product.id} was found.`, source: "canonical/data/master_products.json" });
    findings.push({ code: "PRODUCT_DOCUMENTS", state: "SELF_DECLARED", message: "Product document flags require document-level verification.", source: "canonical/data/master_products.json" });
  }
  if (!supplier) {
    findings.push({ code: "SUPPLIER_LINK", state: "MISSING", message: "No active canonical supplier relationship exists for this product.", source: "canonical/data/supplier-product-links.json" });
  } else {
    findings.push({ code: "SUPPLIER_LINK", state: "SUPPORTED", message: `Active supplier relationship: ${supplier.supplier_id}.`, source: "canonical/data/supplier-product-links.json" });
    findings.push({ code: "SUPPLIER_EXPORT_READINESS", state: supplier.capabilities?.export_ready ? "SELF_DECLARED" : "MISSING", message: supplier.capabilities?.export_ready ? "Supplier declares export readiness; official approval is still required." : "Supplier does not declare export readiness.", source: "canonical/data/suppliers.json" });
  }
  if (!market || market.status !== "active") {
    findings.push({ code: "MARKET", state: "MISSING", message: "Destination is absent or not active in the canonical market registry.", source: "canonical/business/markets.json" });
  } else {
    findings.push({ code: "MARKET", state: "SUPPORTED", message: `Market ${market.country} is active in the internal registry.`, source: "canonical/business/markets.json" });
    findings.push({ code: "MARKET_REQUIREMENTS", state: "SELF_DECLARED", message: "Internal market requirements are reference data, not current official regulatory verification.", source: "canonical/business/markets.json" });
  }
  findings.push({ code: "OFFICIAL_REGULATORY_EVIDENCE", state: "MISSING", message: "No current, source-linked official regulatory evidence is connected to this runtime decision.", source: "Evidence registry: not connected" });
  findings.push({ code: "COMMERCIAL_TERMS", state: "MISSING", message: "No approved current price, offer, shipping quotation, or payment terms are attached.", source: "Commercial change registry / operational data" });

  const missing = findings.filter((finding) => finding.state === "MISSING");
  const status: DecisionStatus = missing.length ? "NOT_READY" : "REQUIRES_HUMAN_REVIEW";
  const confidence = Math.max(0, 100 - missing.length * 20 - findings.filter((finding) => finding.state === "SELF_DECLARED").length * 8);
  return {
    decision: { status, confidence, automaticExecution: false, recommendedAction: status === "NOT_READY" ? "Do not execute export; complete missing evidence and commercial approvals." : "Submit the evidence package for authorized human review." },
    context: {
      product: product ? { id: product.id, code: product.product_code, name: product.name?.en, category: product.category, hsCode: product.global_specs?.hs_code } : null,
      supplier: supplier ? { id: supplier.supplier_id, name: supplier.name, country: supplier.country } : null,
      destination: market ? { country: market.country, region: market.region, priority: market.priority } : { country: destination },
      requiredCertificates: product?.global_specs?.required_certificates ?? globalSpecs.required_certificates,
    },
    findings,
    nextEvidence: missing.map((finding) => ({ code: finding.code, required: finding.message })),
  };
}

// Current-system integration only. Legacy code is neither imported nor executed.
// The returned package remains review-only even when every read gate is satisfied.
export async function buildPersistedExportDecision(productId: string, destination: string) {
  const baseline = buildExportDecision(productId, destination);
  const [storedEvidence, commercialChanges] = await Promise.all([
    prisma.officialEvidenceRegistry.findMany({ where: { product: productId.trim(), destination: destination.trim() }, orderBy: { updatedAt: "desc" } }),
    prisma.commercialChange.findMany({
      where: {
        subjectId: productId.trim(),
        status: "APPROVED",
        domain: { in: [...requiredCommercialDomains] },
      },
      orderBy: { updatedAt: "desc" },
    }),
  ]);
  const officialEvidence: EvidenceGateAssessment = assessOfficialExportEvidence(
    storedEvidence.map((row) => mapPersistedOfficialEvidence(row as PersistedOfficialEvidenceRow)),
    productId,
    destination,
  );
  const commercial = assessCommercialReadiness(commercialChanges, destination);
  const findings = baseline.findings.filter((finding) =>
    finding.code !== "OFFICIAL_REGULATORY_EVIDENCE" && finding.code !== "COMMERCIAL_TERMS",
  );
  findings.push({
    code: "OFFICIAL_REGULATORY_EVIDENCE",
    state: officialEvidence.state === "SUPPORTED_BY_OFFICIAL_SOURCE" ? "SUPPORTED" : "MISSING",
    message: officialEvidence.reasons.join(" "),
    source: "OfficialEvidenceRegistry",
  });
  findings.push({
    code: "COMMERCIAL_TERMS",
    state: commercial.supported ? "SUPPORTED" : "MISSING",
    message: commercial.supported
      ? "Current approved PRICE, SHIPMENT and OFFER records exist for this product and destination."
      : commercial.reasons.join(" "),
    source: "CommercialChange",
  });
  const missing = findings.filter((finding) => finding.state === "MISSING");
  const status: DecisionStatus = missing.length ? "NOT_READY" : "REQUIRES_HUMAN_REVIEW";
  const confidence = Math.max(0, 100 - missing.length * 20 - findings.filter((finding) => finding.state === "SELF_DECLARED").length * 8);
  return {
    ...baseline,
    decision: {
      status,
      confidence,
      automaticExecution: false,
      recommendedAction: status === "NOT_READY"
        ? "Do not execute export; resolve missing official evidence, commercial approvals, quality and operational requirements."
        : "Submit the complete package to an authorized human reviewer. No export is executed by this decision.",
    },
    findings,
    nextEvidence: missing.map((finding) => ({ code: finding.code, required: finding.message })),
    persistedEvidence: {
      source: "OfficialEvidenceRegistry",
      recordCount: storedEvidence.length,
      assessment: officialEvidence,
    },
    commercialReadiness: {
      source: "CommercialChange",
      approvedRecordCount: commercialChanges.length,
      ...commercial,
    },
  };
}
