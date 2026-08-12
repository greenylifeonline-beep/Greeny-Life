import productsSource from "@/canonical/data/master_products.json";
import suppliersSource from "@/canonical/data/suppliers.json";
import certificatesSource from "@/canonical/data/certificates.json";
import stockSource from "@/canonical/inventory/stock-levels.json";
import warehousesSource from "@/canonical/inventory/warehouses.json";
import shipmentsSource from "@/canonical/logistics/shipments.json";
import { canonicalIntegrityReview } from "@/lib/intelligence/canonical-integrity-adapter";
import { operationalDataStatus } from "@/lib/intelligence/operational-data-freshness";
import { supplierQualityReview } from "@/lib/intelligence/supplier-quality-review";
import { shipmentTrackingReview } from "@/lib/intelligence/shipment-tracking-review";

export const greenyLifeEgyptBrainIdentity = {
  id: "GREENY_LIFE_EGYPT_BRAIN",
  name: "Greeny-Life Egypt Brain",
  company: "GREENY_LIFE_EGYPT",
  mode: "READ_ONLY_OPERATIONAL_INTELLIGENCE",
  mandate: ["production and packaging visibility", "Egypt supplier and inventory context", "export and import preparation", "shipment monitoring", "local opportunity detection"],
  escalatesTo: "MasterMind AI",
  prohibited: ["commercial commitment", "price approval", "supplier activation", "shipment release", "payment", "customs filing", "self-modification"],
} as const;

type Product = { id: string; product_code: string; category: string; name?: { en?: string; ar?: string } };
type Supplier = { supplier_id: string; name: string; category: string[]; status: string; capabilities: { production?: boolean; private_label?: boolean; export_ready?: boolean }; quality?: { audit_status?: string } };
type Stock = { product_id: string; warehouse_id: string; quantity: number; reorder_level: number; last_updated: string };
type Warehouse = { id: string; name: string; location: string; capacity: number };
type Shipment = { shipment_id: string; product_id: string; status: string; market: string; destination_country: string; quantity: number; tracking_code: string; last_updated: string };
type Certificate = { certificate_id: string; name: string; applicable_to: string[] };

const products = (productsSource as { products: Product[] }).products;
const suppliers = (suppliersSource as { suppliers: Supplier[] }).suppliers;
const stock = (stockSource as { stock: Stock[] }).stock;
const warehouses = (warehousesSource as { warehouses: Warehouse[] }).warehouses;
const shipments = (shipmentsSource as { shipments: Shipment[] }).shipments;
const certificates = (certificatesSource as { certificates: Certificate[] }).certificates;

function categoryMatches(productCategory: string, supplierCategories: string[]) {
  const product = productCategory.toLowerCase();
  return supplierCategories.some((category) => product.includes(category.toLowerCase()) || category.toLowerCase().includes(product));
}

export function greenyLifeEgyptOperationalView(productId?: string) {
  const integrity = canonicalIntegrityReview();
  const selectedProduct = productId ? products.find((product) => product.id.toUpperCase() === productId.trim().toUpperCase()) : undefined;
  const supplierQuality = selectedProduct ? supplierQualityReview(selectedProduct.id) : null;
  const productStock = selectedProduct ? stock.filter((item) => item.product_id === selectedProduct.id) : stock;
  const lowStock = productStock.filter((item) => item.quantity <= item.reorder_level);
  const relatedSuppliers = selectedProduct ? suppliers.filter((supplier) => categoryMatches(selectedProduct.category, supplier.category)) : suppliers;
  const exportReadySuppliers = relatedSuppliers.filter((supplier) => supplier.status === "active" && supplier.capabilities.export_ready);
  const candidateOrUnaudited = relatedSuppliers.filter((supplier) => supplier.status !== "active" || supplier.quality?.audit_status !== "approved");
  const selectedShipments = selectedProduct ? shipments.filter((shipment) => shipment.product_id === selectedProduct.id) : shipments;
  const shipmentTracking = shipmentTrackingReview(selectedProduct?.id);
  const operationalData = operationalDataStatus({
    stockUpdatedAt: productStock.map((item) => item.last_updated),
    supplierGeneratedAt: (suppliersSource as { generated_at?: string }).generated_at,
    shipmentUpdatedAt: selectedShipments.map((shipment) => shipment.last_updated),
  });
  const activeShipmentStatuses = new Set(["PACKED", "SHIPPED", "AT_PORT", "IN_TRANSIT", "CUSTOMS_CLEARANCE"]);
  const activeShipments = selectedShipments.filter((shipment) => activeShipmentStatuses.has(shipment.status));
  const warehouseById = new Map(warehouses.map((warehouse) => [warehouse.id, warehouse]));

  const blockers = [
    ...integrity.blockers,
    ...operationalData.blockers,
    ...(supplierQuality?.blockers ?? []),
    ...shipmentTracking.blockers,
    ...(selectedProduct && !productStock.length ? [`No stock record exists for ${selectedProduct.id}.`] : []),
    ...lowStock.map((item) => `${item.product_id} is at or below its reorder level in ${warehouseById.get(item.warehouse_id)?.name ?? item.warehouse_id}.`),
    ...candidateOrUnaudited.map((supplier) => `${supplier.name} is ${supplier.status} with audit status ${supplier.quality?.audit_status ?? "missing"}; it is not approved for automatic use.`),
  ];
  const warnings = [
    ...(activeShipments.length ? [`${activeShipments.length} active historical shipment record(s) require current carrier/document verification before any operational reliance.`] : []),
    "Canonical operational records are internal reference data; they do not prove current stock, supplier authorization, certificate validity, or customs eligibility.",
  ];

  return {
    brain: greenyLifeEgyptBrainIdentity,
    status: blockers.length ? "REVIEW_REQUIRED" : "OBSERVATION_READY",
    selectedProduct: selectedProduct ? { id: selectedProduct.id, code: selectedProduct.product_code, category: selectedProduct.category, name: selectedProduct.name?.en ?? selectedProduct.id } : null,
    operations: {
      canonicalIntegrity: integrity,
      operationalData,
      supplierQuality,
      shipmentTracking,
      products: products.length,
      warehouses: warehouses.map(({ id, name, location, capacity }) => ({ id, name, location, capacity })),
      stock: productStock.map((item) => ({ ...item, warehouse: warehouseById.get(item.warehouse_id)?.name ?? item.warehouse_id })),
      lowStockCount: lowStock.length,
      suppliers: relatedSuppliers.map((supplier) => ({ id: supplier.supplier_id, name: supplier.name, status: supplier.status, exportReady: Boolean(supplier.capabilities.export_ready), auditStatus: supplier.quality?.audit_status ?? "missing" })),
      approvedExportReadySupplierCount: exportReadySuppliers.length,
      activeShipments: activeShipments.map(({ shipment_id, status, market, destination_country, quantity, tracking_code, last_updated }) => ({ shipmentId: shipment_id, status, market, destinationCountry: destination_country, quantity, trackingCode: tracking_code, lastUpdated: last_updated })),
      certificateCatalog: certificates.length,
    },
    blockers,
    warnings,
    opportunities: selectedProduct && productStock.some((item) => item.quantity > item.reorder_level) ? [`Inventory exists for ${selectedProduct.id}; MasterMind may evaluate a verified commercial opportunity.`] : [],
    escalation: {
      to: "MasterMind AI",
      when: ["new market or product", "cross-company trade", "supplier/price/shipment change", "stock exception", "quality or compliance gap"],
      executionRule: "Greeny-Life Egypt Brain reports and proposes. MasterMind assembles the decision package; explicit user approval is required before controlled execution.",
    },
    sourceBoundaries: [
      "canonical/data/master_products.json",
      "canonical/data/suppliers.json",
      "canonical/data/certificates.json",
      "canonical/inventory/warehouses.json",
      "canonical/inventory/stock-levels.json",
      "canonical/logistics/shipments.json",
    ],
  };
}
