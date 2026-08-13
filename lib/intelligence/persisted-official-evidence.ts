import type { OfficialEvidenceRecord } from "@/lib/intelligence/official-evidence-gate";

export type PersistedOfficialEvidenceRow = {
  evidenceKey: string;
  product: string;
  destination: string;
  authority: string;
  verificationStatus: string;
  claimStatus: string;
  validTo: Date | null;
  gates: unknown;
  sourceUrl: string | null;
};

const authorities = new Set<OfficialEvidenceRecord["authority"]>(["official", "secondary", "internal", "unknown"]);
const verificationStates = new Set<OfficialEvidenceRecord["verificationStatus"]>(["verified_current", "unverified", "expired", "unknown"]);
const claimStates = new Set<NonNullable<OfficialEvidenceRecord["claimStatus"]>>(["supported", "prohibited", "unknown"]);
const evidenceGates = new Set<OfficialEvidenceRecord["gates"][number]>(["country_eligibility", "establishment_listing", "official_certificate", "border_process", "importer_registration"]);

// Pure adapter: database values are normalized before the evidence gate sees them.
export function mapPersistedOfficialEvidence(row: PersistedOfficialEvidenceRow): OfficialEvidenceRecord {
  return {
    id: row.evidenceKey,
    scope: { product: row.product, destination: row.destination },
    authority: authorities.has(row.authority as OfficialEvidenceRecord["authority"]) ? row.authority as OfficialEvidenceRecord["authority"] : "unknown",
    verificationStatus: verificationStates.has(row.verificationStatus as OfficialEvidenceRecord["verificationStatus"]) ? row.verificationStatus as OfficialEvidenceRecord["verificationStatus"] : "unknown",
    claimStatus: claimStates.has(row.claimStatus as NonNullable<OfficialEvidenceRecord["claimStatus"]>) ? row.claimStatus as NonNullable<OfficialEvidenceRecord["claimStatus"]> : "unknown",
    validTo: row.validTo?.toISOString().slice(0, 10),
    gates: Array.isArray(row.gates) ? row.gates.filter((gate): gate is OfficialEvidenceRecord["gates"][number] => evidenceGates.has(String(gate) as OfficialEvidenceRecord["gates"][number])) : [],
    sourceUrl: row.sourceUrl ?? undefined,
  };
}