export const supplierStatuses = ["PENDING_VERIFICATION", "ACTIVE", "INACTIVE", "REJECTED"] as const;
export const supplierVerificationStatuses = ["UNVERIFIED", "VERIFIED", "EXPIRED", "REJECTED"] as const;
export type SupplierStatus = typeof supplierStatuses[number];
export type SupplierVerificationStatus = typeof supplierVerificationStatuses[number];

export type SupplierMasterSnapshot = {
  status: string; verificationStatus: string; sourceUrl: string | null; sourceReference: string | null;
};
export type SupplierMasterEdit = {
  status?: SupplierStatus; verificationStatus?: SupplierVerificationStatus;
  sourceUrl?: string | null; sourceReference?: string | null; deactivationReason?: string | null;
};
/**
 * Separates the running supplier master from its canonical JSON inputs.
 * A human commercial owner is intentionally left unassigned until formally
 * nominated; the ADMIN role is the current operational steward only.
 */
export const supplierMasterAuthorityContract = Object.freeze({
  capability: "SUPPLIER_MASTER",
  operationalSystemOfRecord: "CURRENT_PRISMA_SUPPLIER",
  referenceInput: "canonical/data/suppliers.json",
  relationshipReferenceInput: "canonical/data/supplier-product-links.json",
  referenceInputRule: "REFERENCE_ONLY_REQUIRES_CONTROLLED_IMPORT_REVIEW",
  operationalStewardRole: "ADMIN",
  businessOwner: "UNASSIGNED_REQUIRES_COMMERCIAL_OWNER_DECISION",
  writeRule: "AUTHENTICATED_ADMIN_WITH_DURABLE_AUTHORIZATION_AUDIT",
  activationRule: "VERIFIED_EVIDENCE_AND_SOURCE_REQUIRED",
  removalRule: "DEACTIVATE_WITH_REASON_PRESERVE_LINKED_PRODUCT_HISTORY",
  recoveryRule: "RETAIN_VERSIONED_CANONICAL_INPUT_AND_AUDITED_CURRENT_RECORD_HISTORY",
} as const);

export function nullableText(value: unknown, supplied: boolean, field: string): string | null | undefined {
  if (!supplied) return undefined;
  if (value === null) return null;
  if (typeof value !== "string") throw new Error(`${field} must be text or null.`);
  const normalized = value.trim();
  return normalized.length ? normalized : null;
}

export function validateSupplierTransition(existing: SupplierMasterSnapshot, edit: SupplierMasterEdit) {
  const status = edit.status ?? existing.status;
  const verificationStatus = edit.verificationStatus ?? existing.verificationStatus;
  const sourceUrl = edit.sourceUrl === undefined ? existing.sourceUrl : edit.sourceUrl;
  const sourceReference = edit.sourceReference === undefined ? existing.sourceReference : edit.sourceReference;
  if (!supplierStatuses.includes(status as SupplierStatus)) throw new Error("status is invalid.");
  if (!supplierVerificationStatuses.includes(verificationStatus as SupplierVerificationStatus)) throw new Error("verificationStatus is invalid.");
  if (status === "ACTIVE" && (verificationStatus !== "VERIFIED" || (!sourceUrl && !sourceReference))) {
    throw new Error("ACTIVE requires VERIFIED evidence and a source URL or reference.");
  }
  if (status === "INACTIVE" && !edit.deactivationReason?.trim()) throw new Error("INACTIVE requires a deactivation reason.");
  return { status, verificationStatus, sourceUrl, sourceReference };
}