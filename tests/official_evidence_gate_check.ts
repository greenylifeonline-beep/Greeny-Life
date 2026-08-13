import { assessOfficialExportEvidence, REQUIRED_EXPORT_EVIDENCE_GATES, type OfficialEvidenceRecord } from "../lib/intelligence/official-evidence-gate";
const today = new Date("2026-08-12T12:00:00.000Z");
const record = (overrides: Partial<OfficialEvidenceRecord> = {}): OfficialEvidenceRecord => ({
  id: "E-001", scope: { product: "honey", destination: "norway" }, authority: "official",
  verificationStatus: "verified_current", claimStatus: "supported", gates: [...REQUIRED_EXPORT_EVIDENCE_GATES],
  validTo: "2026-12-31", ...overrides
});
function expect(value: unknown, message: string) { if (!value) throw new Error(message); }
expect(assessOfficialExportEvidence([], "honey", "norway", today).state === "NEEDS_VERIFICATION", "Missing evidence must fail closed.");
expect(assessOfficialExportEvidence([record({authority:"secondary"})], "honey", "norway", today).state === "REQUIRES_HUMAN_REVIEW", "Secondary source cannot authorize.");
expect(assessOfficialExportEvidence([record({validTo:"2026-01-01"})], "honey", "norway", today).state === "REQUIRES_HUMAN_REVIEW", "Expired evidence cannot authorize.");
expect(assessOfficialExportEvidence([record({claimStatus:"prohibited"})], "honey", "norway", today).state === "NO_GO", "Prohibition must win.");
expect(assessOfficialExportEvidence([record({gates:["country_eligibility"]})], "honey", "norway", today).state === "NEEDS_VERIFICATION", "Partial gates cannot authorize.");
expect(assessOfficialExportEvidence([record()], "honey", "norway", today).state === "SUPPORTED_BY_OFFICIAL_SOURCE", "Full evidence should be supported.");
console.log("official_evidence_gate_check: PASS");