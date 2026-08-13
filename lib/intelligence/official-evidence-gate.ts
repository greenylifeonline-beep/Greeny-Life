export type EvidenceGateState =
  | "NEEDS_VERIFICATION"
  | "SUPPORTED_BY_OFFICIAL_SOURCE"
  | "REQUIRES_HUMAN_REVIEW"
  | "STALE"
  | "CONFLICT"
  | "NO_GO";
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

export function isOfficialEvidenceSourceUrl(value?: string): boolean {
  try {
    const url = new URL(value ?? "");
    return (url.protocol === "https:" || url.protocol === "http:") && Boolean(url.hostname);
  } catch {
    return false;
  }
}

function isValidIsoDate(value: string): boolean {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return false;
  const [year, month, day] = value.split("-").map(Number);
  const parsed = new Date(Date.UTC(year, month - 1, day));
  return parsed.getUTCFullYear() === year && parsed.getUTCMonth() === month - 1 && parsed.getUTCDate() === day;
}
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
  const invalidDateEvidence = scoped.filter((item) => Boolean(item.validTo) && !isValidIsoDate(item.validTo!));
  if (invalidDateEvidence.length) return {
    state: "REQUIRES_HUMAN_REVIEW", evidenceIds: scoped.map((entry) => entry.id), missingGates: [...REQUIRED_EXPORT_EVIDENCE_GATES],
    reasons: invalidDateEvidence.map((item) => `${item.id} has an invalid validity date and cannot authorize a decision.`),
  };
  const currentOfficial = scoped.filter((item) =>
    item.authority === "official" &&
    item.verificationStatus === "verified_current" &&
    !(item.validTo && new Date(item.validTo + "T23:59:59.999Z") < today),
  );
  const hasSupportedCurrentEvidence = currentOfficial.some((item) => item.claimStatus === "supported");
  const hasProhibitedCurrentEvidence = currentOfficial.some((item) => item.claimStatus === "prohibited");
  if (hasSupportedCurrentEvidence && hasProhibitedCurrentEvidence) return {
    state: "CONFLICT", evidenceIds: scoped.map((entry) => entry.id), missingGates: [],
    reasons: ["Current official evidence contains both supported and prohibited claims for this scenario."],
  };
  if (hasProhibitedCurrentEvidence) return {
    state: "NO_GO", evidenceIds: scoped.map((entry) => entry.id), missingGates: [],
    reasons: ["Current official evidence explicitly prohibits this scenario."],
  };
  const staleEvidence = scoped.filter((item) =>
    item.verificationStatus === "expired" ||
    Boolean(item.validTo && new Date(item.validTo + "T23:59:59.999Z") < today),
  );
  if (staleEvidence.length) return {
    state: "STALE", evidenceIds: scoped.map((entry) => entry.id), missingGates: [...REQUIRED_EXPORT_EVIDENCE_GATES],
    reasons: staleEvidence.map((item) => `${item.id} is expired or marked expired and cannot authorize a decision.`),
  };
  for (const item of scoped) {
    if (item.authority !== "official") { reasons.push(item.id + " is not an official source."); continue; }
    if (item.verificationStatus !== "verified_current") { reasons.push(item.id + " is not verified current."); continue; }
    if (!isOfficialEvidenceSourceUrl(item.sourceUrl)) { reasons.push(item.id + " lacks a valid HTTP(S) source URL and cannot authorize a decision."); continue; }
    if (item.claimStatus !== "supported") { reasons.push(item.id + " does not contain an explicit supported claim."); continue; }
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
