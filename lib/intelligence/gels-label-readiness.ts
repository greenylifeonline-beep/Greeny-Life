import productsSource from "@/canonical/data/master_products.json";

export type LabelReadiness = "READY_FOR_REVIEW" | "REVIEW_REQUIRED" | "NOT_READY";
export type GelsMarket = "EGYPT" | "GCC" | "EU" | "USA" | "ASIA";

type Product = {
  id: string; ref_id?: string; category: string; name?: { en?: string; ar?: string };
  global_specs?: { hs_code?: string; ean?: string; country_of_origin?: string; required_certificates?: string[] };
  traceability?: { batch_number?: string; production_date?: string; expiry_date?: string; factory_code?: string; qr_verification?: boolean };
  front_label?: { elements?: string[] };
  back_label?: { ingredients?: string[]; nutrition_facts?: unknown; description?: { en?: string; ar?: string }; storage?: string; warnings?: string[]; certifications?: string[] };
  side_panel?: Record<string, unknown>;
  packaging?: { b2c?: { sizes?: string[] }; retail?: string[] };
  markets?: Record<string, boolean>;
};

export interface BatchLabelEvidence {
  batchNumber?: string;
  productionDate?: string;
  expiryDate?: string;
  numericEan13?: string;
  qrUrl?: string;
  coaEvidenceId?: string;
  officialMarketEvidenceIds?: string[];
}

const products = (productsSource as { products: Product[] }).products;
const marketFlag: Record<GelsMarket, string> = { EGYPT: "egypt", GCC: "gcc", EU: "eu", USA: "usa", ASIA: "asia" };

function nonEmpty(value?: string) { return Boolean(value?.trim()); }
function isIsoDate(value?: string) { return Boolean(value && !Number.isNaN(new Date(value).valueOf())); }
function isEan13(value?: string) { return Boolean(value && /^\d{13}$/.test(value)); }

export function evaluateGelsLabel(input: { productId: string; market: GelsMarket; batch?: BatchLabelEvidence }) {
  const product = products.find((item) => item.id.toUpperCase() === input.productId.trim().toUpperCase());
  if (!product) return { status: "NOT_READY" as LabelReadiness, product: null, market: input.market, checks: [], blockers: ["Product is not in the canonical GELS product master."], warnings: [], executionRule: "No label can be generated, printed, or approved." };
  const batch = input.batch ?? {};
  const checks = [
    { id: "GELS_SCHEMA", passed: Boolean(product.ref_id), requirement: "GELS label reference ID" },
    { id: "PRODUCT_IDENTITY", passed: nonEmpty(product.name?.en) && nonEmpty(product.name?.ar), requirement: "Arabic and English product names" },
    { id: "FRONT_LABEL", passed: ["logo", "product_name", "net_weight", "origin_egypt", "qr_small"].every((element) => product.front_label?.elements?.includes(element)), requirement: "Required front-label elements" },
    { id: "BACK_LABEL", passed: Boolean(product.back_label?.ingredients?.length) && Boolean(product.back_label?.nutrition_facts) && nonEmpty(product.back_label?.storage) && Boolean(product.back_label?.warnings?.length), requirement: "Ingredients, nutrition, storage, and warnings" },
    { id: "SIDE_PANEL", passed: Boolean(product.side_panel && Object.keys(product.side_panel).length), requirement: "Category side-panel content" },
    { id: "ORIGIN_HS", passed: nonEmpty(product.global_specs?.country_of_origin) && nonEmpty(product.global_specs?.hs_code), requirement: "Origin country and HS code" },
    { id: "PACK_SIZE", passed: Boolean(product.packaging?.b2c?.sizes?.length || product.packaging?.retail?.length), requirement: "At least one packaging size" },
    { id: "BATCH", passed: nonEmpty(batch.batchNumber), requirement: "Actual batch number" },
    { id: "PRODUCTION_DATE", passed: isIsoDate(batch.productionDate), requirement: "Actual production date" },
    { id: "EXPIRY_DATE", passed: isIsoDate(batch.expiryDate), requirement: "Actual best-before or expiry date" },
    { id: "EAN13", passed: isEan13(batch.numericEan13), requirement: "Numeric EAN-13 validated for the printed SKU" },
    { id: "TRACEABILITY_QR", passed: nonEmpty(batch.qrUrl) && Boolean(product.traceability?.qr_verification), requirement: "QR verification URL tied to the batch" },
    { id: "COA", passed: nonEmpty(batch.coaEvidenceId), requirement: "Batch-linked certificate of analysis evidence ID" },
    { id: "MARKET_EVIDENCE", passed: Boolean(batch.officialMarketEvidenceIds?.length), requirement: "Current official market-label/compliance evidence" },
    { id: "MARKET_FIT", passed: input.market === "EGYPT" || product.markets?.[marketFlag[input.market]] === true, requirement: "Internal product market flag" },
  ];
  const blockers = checks.filter((check) => !check.passed && ["BATCH", "PRODUCTION_DATE", "EXPIRY_DATE", "EAN13", "TRACEABILITY_QR", "COA", "MARKET_EVIDENCE"].includes(check.id)).map((check) => `${check.id}: ${check.requirement} is missing or invalid.`);
  const warnings = checks.filter((check) => !check.passed && !blockers.some((blocker) => blocker.startsWith(check.id))).map((check) => `${check.id}: ${check.requirement} requires data-owner review.`);
  const status: LabelReadiness = blockers.length ? "NOT_READY" : warnings.length ? "REVIEW_REQUIRED" : "READY_FOR_REVIEW";
  return {
    status, product: { id: product.id, refId: product.ref_id ?? null, category: product.category, name: product.name?.en ?? product.id, internalEanReference: product.global_specs?.ean ?? null }, market: input.market,
    checks, blockers, warnings,
    sourceBoundaries: ["canonical/data/master_products.json", "BatchLabelEvidence supplied by caller"],
    executionRule: "This is a label-readiness assessment only. READY_FOR_REVIEW is not print approval, market authorization, customs clearance, or permission to ship. An authorized human must review final artwork, batch evidence, official market requirements, and print proof.",
  };
}