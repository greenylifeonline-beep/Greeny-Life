export type EvidenceGateState = "NEEDS_VERIFICATION" | "SUPPORTED_BY_OFFICIAL_SOURCE" | "REQUIRES_HUMAN_REVIEW" | "NO_GO";
export type OfficialEvidenceGate = "country_eligibility" | "establishment_listing" | "official_certificate" | "border_process" | "importer_registration";
export interface OfficialEvidenceRecord {
  id: string;
  scope: { product: string; destination: string };
  authority: "official" | "secondary" | "internal" | "unknown";
  verificationStatus: "verified_current" | "unverified" | "expired" | "unknown";
  validTo?: string;
  claimStatus?: "supported" | "prohibited" | "unknown";
  gates: OfficialEvidenceGate[];
  sourceUrl?: string;
}
export interface EvidenceGateAssessment {
  state: EvidenceGateState;
  evidenceIds: string[];
  missingGates: OfficialEvidenceGate[];
  reasons: string[];
}
export const REQUIRED_EXPORT_EVIDENCE_GATES: OfficialEvidenceGate[] = [
  "country_eligibility", "establishment_listing", "official_certificate", "border_process", "importer_registration"
];
export function assessOfficialExportEvidence(
  evidence: OfficialEvidenceRecord[], product: string, destination: string, today = new Date()
): EvidenceGateAssessment {
  const scoped = evidence.filter((item) =>
    item.scope.product.trim().toLowerCase() === product.trim().toLowerCase() &&
    item.scope.destination.trim().toLowerCase() === destination.trim().toLowerCase()
  );
  if (!scoped.length) return {
    state: "NEEDS_VERIFICATION", evidenceIds: [], missingGates: [...REQUIRED_EXPORT_EVIDENCE_GATES],
    reasons: ["No evidence is explicitly scoped to this product and destination."]
  };
  const reasons: string[] = [];
  const covered = new Set<OfficialEvidenceGate>();
  for (const item of scoped) {
    if (item.authority !== "official") { reasons.push(item.id + " is not an official source."); continue; }
    if (item.verificationStatus !== "verified_current") { reasons.push(item.id + " is not verified current."); continue; }
    if (item.validTo && new Date(item.validTo + "T23:59:59.999Z") < today) { reasons.push(item.id + " is expired."); continue; }
    if (item.claimStatus === "prohibited") return {
      state: "NO_GO", evidenceIds: scoped.map((entry) => entry.id), missingGates: [],
      reasons: [item.id + " explicitly prohibits this scenario."]
    };
    item.gates.forEach((gate) => covered.add(gate));
  }
  const missingGates = REQUIRED_EXPORT_EVIDENCE_GATES.filter((gate) => !covered.has(gate));
  if (reasons.length) return { state: "REQUIRES_HUMAN_REVIEW", evidenceIds: scoped.map((entry) => entry.id), missingGates, reasons };
  if (missingGates.length) return {
    state: "NEEDS_VERIFICATION", evidenceIds: scoped.map((entry) => entry.id), missingGates,
    reasons: ["Official evidence exists, but required decision gates are incomplete."]
  };
  return {
    state: "SUPPORTED_BY_OFFICIAL_SOURCE", evidenceIds: scoped.map((entry) => entry.id),
    missingGates: [], reasons: ["All required gates have current official evidence."]
  };
}