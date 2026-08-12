import productsSource from "@/canonical/data/master_products.json";
import suppliersSource from "@/canonical/data/suppliers.json";
import stockSource from "@/canonical/inventory/stock-levels.json";
import shipmentsSource from "@/canonical/logistics/shipments.json";
import { assessFreshness } from "@/lib/intelligence/operational-data-freshness";

export type FabricConsumer = "GREENY_LIFE_EGYPT_BRAIN" | "GREENS_NATURE_UAE_BRAIN" | "GREEN_LINES_NORWAY_EU_BRAIN" | "MASTERMIND_AI" | "TRAINING_FACTORY";
export type FabricDomain = "PRODUCT" | "SUPPLIER" | "INVENTORY" | "SHIPMENT";

type Product = { id: string; product_code: string; category: string; name?: { en?: string }; global_specs?: { hs_code?: string } };
type Supplier = { supplier_id: string; status: string; category: string[]; capabilities?: { export_ready?: boolean }; quality?: { audit_status?: string } };
type Stock = { product_id: string; warehouse_id: string; quantity: number; reorder_level: number; last_updated: string };
type Shipment = { shipment_id: string; product_id: string; status: string; destination_country: string; market: string; quantity: number; last_updated: string };

const products = (productsSource as { products: Product[] }).products;
const suppliers = (suppliersSource as { suppliers: Supplier[] }).suppliers;
const stock = (stockSource as { stock: Stock[] }).stock;
const shipments = (shipmentsSource as { shipments: Shipment[] }).shipments;

const policies: Record<FabricDomain, { owner: string; sensitivity: "INTERNAL" | "CONFIDENTIAL"; consumers: FabricConsumer[]; source: string }> = {
  PRODUCT: { owner: "GREENY_LIFE_EGYPT", sensitivity: "INTERNAL", consumers: ["GREENY_LIFE_EGYPT_BRAIN", "GREENS_NATURE_UAE_BRAIN", "GREEN_LINES_NORWAY_EU_BRAIN", "MASTERMIND_AI", "TRAINING_FACTORY"], source: "canonical/data/master_products.json" },
  SUPPLIER: { owner: "GREENY_LIFE_EGYPT", sensitivity: "CONFIDENTIAL", consumers: ["GREENY_LIFE_EGYPT_BRAIN", "MASTERMIND_AI", "TRAINING_FACTORY"], source: "canonical/data/suppliers.json" },
  INVENTORY: { owner: "GREENY_LIFE_EGYPT", sensitivity: "CONFIDENTIAL", consumers: ["GREENY_LIFE_EGYPT_BRAIN", "MASTERMIND_AI", "TRAINING_FACTORY"], source: "canonical/inventory/stock-levels.json" },
  SHIPMENT: { owner: "GREENY_LIFE_EGYPT", sensitivity: "CONFIDENTIAL", consumers: ["GREENY_LIFE_EGYPT_BRAIN", "MASTERMIND_AI", "TRAINING_FACTORY"], source: "canonical/logistics/shipments.json" },
};

function freshness(timestamps: string[]) {
  const values = timestamps.map((timestamp) => assessFreshness(timestamp));
  return { state: values.some((item) => item.state === "INVALID_TIMESTAMP") ? "INVALID_TIMESTAMP" : values.some((item) => item.state === "STALE_REFERENCE") ? "STALE_REFERENCE" : "RECENT_REFERENCE", count: values.length, automaticExecution: false };
}

export function dataFabricCatalog() {
  return {
    system: "Global Data Intelligence & Distribution Fabric",
    ownershipRule: "Data remains owned by its local operating company. The fabric produces read-only, purpose-limited context; it does not centralize authority or execute operations.",
    domains: (Object.entries(policies) as [FabricDomain, typeof policies[FabricDomain]][]).map(([domain, policy]) => ({ domain, ...policy })),
    quality: {
      PRODUCT: { count: products.length, freshness: freshness([(productsSource as { generated_at?: string }).generated_at ?? ""]) },
      SUPPLIER: { count: suppliers.length, freshness: freshness([(suppliersSource as { generated_at?: string }).generated_at ?? ""]) },
      INVENTORY: { count: stock.length, freshness: freshness(stock.map((item) => item.last_updated)) },
      SHIPMENT: { count: shipments.length, freshness: freshness(shipments.map((item) => item.last_updated)) },
    },
    executionRule: "Fabric output is internal reference context. It never authorizes offers, commitments, production, allocation, shipment, customs, payment, title transfer, policy changes, or data mutation.",
  };
}

export function distributeFabricContext(input: { consumer: FabricConsumer; productId?: string; domains?: FabricDomain[] }) {
  const requested = input.domains?.length ? [...new Set(input.domains)] : ["PRODUCT", "INVENTORY", "SHIPMENT"] as FabricDomain[];
  const denied = requested.filter((domain) => !policies[domain].consumers.includes(input.consumer));
  const allowed = requested.filter((domain) => policies[domain].consumers.includes(input.consumer));
  const key = input.productId?.trim().toUpperCase();
  const product = key ? products.find((item) => item.id.toUpperCase() === key) : undefined;
  const productStock = key ? stock.filter((item) => item.product_id === key) : [];
  const productShipments = key ? shipments.filter((item) => item.product_id === key) : [];
  const context: Record<string, unknown> = {};
  if (allowed.includes("PRODUCT")) context.product = product ? { id: product.id, code: product.product_code, category: product.category, name: product.name?.en ?? null, hsCode: product.global_specs?.hs_code ?? null } : key ? null : { count: products.length };
  if (allowed.includes("INVENTORY")) context.inventory = key ? { productId: key, quantity: productStock.reduce((sum, item) => sum + item.quantity, 0), reorderAlert: productStock.some((item) => item.quantity <= item.reorder_level), freshness: freshness(productStock.map((item) => item.last_updated)) } : { count: stock.length, freshness: freshness(stock.map((item) => item.last_updated)) };
  if (allowed.includes("SHIPMENT")) context.shipments = key ? { productId: key, count: productShipments.length, statuses: productShipments.map((item) => ({ status: item.status, destination: item.destination_country, market: item.market, quantity: item.quantity })), freshness: freshness(productShipments.map((item) => item.last_updated)) } : { count: shipments.length, freshness: freshness(shipments.map((item) => item.last_updated)) };
  if (allowed.includes("SUPPLIER")) context.suppliers = key ? { category: product?.category ?? null, candidates: suppliers.filter((item) => product ? item.category.some((category) => category.toLowerCase() === product.category.toLowerCase()) : false).map((item) => ({ id: item.supplier_id, status: item.status, exportReadyClaim: Boolean(item.capabilities?.export_ready), auditStatus: item.quality?.audit_status ?? "missing" })) } : { count: suppliers.length };
  return {
    consumer: input.consumer, productId: key ?? null, requestedDomains: requested, allowedDomains: allowed, deniedDomains: denied,
    status: denied.length ? "PARTIAL_CONTEXT_REVIEW_REQUIRED" : "READ_ONLY_CONTEXT_READY",
    context,
    policy: allowed.map((domain) => ({ domain, owner: policies[domain].owner, sensitivity: policies[domain].sensitivity, source: policies[domain].source })),
    blockers: [
      ...denied.map((domain) => `${input.consumer} is not authorized to receive ${domain} detail from ${policies[domain].owner}.`),
      ...(key && !product ? [`Product ${key} is not in the canonical product master.`] : []),
    ],
    audit: { purpose: "Need-to-know read-only decision context", requestedAt: new Date().toISOString(), version: "FABRIC-v1" },
    executionRule: "Distribution is a read-only context response. It does not alter ownership, grant authority, or authorize execution.",
  };
}