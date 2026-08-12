import suppliersSource from "@/canonical/data/suppliers.json";
import supplierLinksSource from "@/canonical/data/supplier-product-links.json";
import certificateLinksSource from "@/canonical/data/product-certificate-links.json";

type Supplier = {
  supplier_id: string;
  name: string;
  status: string;
  capabilities: { export_ready?: boolean };
  quality?: { audit_status?: string };
  certifications?: string[];
};
type SupplierLink = { supplier_id: string; product_id: string; relationship_type: string; status: string };
type CertificateLink = { product_id: string; certificate_id: string; status: string };

const suppliers = (suppliersSource as { suppliers: Supplier[] }).suppliers;
const supplierLinks = (supplierLinksSource as { links: SupplierLink[] }).links;
const certificateLinks = (certificateLinksSource as { links: CertificateLink[] }).links;

export function supplierQualityReview(productId: string) {
  const links = supplierLinks.filter((link) => link.product_id === productId && link.status === "active");
  const mappedSuppliers = links.flatMap((link) => {
    const supplier = suppliers.find((item) => item.supplier_id === link.supplier_id);
    return supplier ? [{ supplier, link }] : [];
  });
  const requiredCertificates = certificateLinks.filter((link) => link.product_id === productId && link.status === "required");
  const blockers = [
    ...(links.length === 0 ? [`No active canonical supplier-product link exists for ${productId}.`] : []),
    ...mappedSuppliers.filter(({ supplier }) => supplier.status !== "active").map(({ supplier }) => `${supplier.name} is ${supplier.status}, not active.`),
    ...mappedSuppliers.filter(({ supplier }) => !supplier.capabilities.export_ready).map(({ supplier }) => `${supplier.name} is not marked export-ready.`),
    ...mappedSuppliers.filter(({ supplier }) => supplier.quality?.audit_status !== "approved").map(({ supplier }) => `${supplier.name} has audit status ${supplier.quality?.audit_status ?? "missing"}; a current approved audit is required.`),
    ...(requiredCertificates.length ? ["Certificate links describe required documents only; they do not prove a current certificate issued to the supplier, product, batch, or destination."] : ["No required-certificate links were found for this product."]),
  ];
  const eligibleOnReference = mappedSuppliers.filter(({ supplier }) => supplier.status === "active" && supplier.capabilities.export_ready && supplier.quality?.audit_status === "approved");
  return {
    status: eligibleOnReference.length ? "REVIEW_REQUIRED" as const : "NOT_READY" as const,
    productId,
    sourceBoundaries: [
      "canonical/data/suppliers.json",
      "canonical/data/supplier-product-links.json",
      "canonical/data/product-certificate-links.json",
    ],
    suppliers: mappedSuppliers.map(({ supplier, link }) => ({
      id: supplier.supplier_id,
      name: supplier.name,
      relationshipType: link.relationship_type,
      status: supplier.status,
      exportReady: Boolean(supplier.capabilities.export_ready),
      auditStatus: supplier.quality?.audit_status ?? "missing",
      declaredCertifications: supplier.certifications ?? [],
    })),
    requiredCertificateIds: requiredCertificates.map((link) => link.certificate_id),
    blockers,
    executionRule: "This review never selects, activates, contracts with, or purchases from a supplier. A current supplier audit and scoped, verified certificate evidence are required before a human can approve a commercial action.",
  };
}
