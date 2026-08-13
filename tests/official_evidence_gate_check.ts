import { assessOfficialExportEvidence, REQUIRED_EXPORT_EVIDENCE_GATES, type OfficialEvidenceRecord } from "../lib/intelligence/official-evidence-gate";
const today = new Date("2026-08-12T12:00:00.000Z");
const record = (overrides: Partial<OfficialEvidenceRecord> = {}): OfficialEvidenceRecord => ({
  id: "E-001", scope: { product: "honey", destination: "norway" }, authority: "official",
  verificationStatus: "verified_current", claimStatus: "supported", gates: [...REQUIRED_EXPORT_EVIDENCE_GATES],
  validTo: "2026-12-31", sourceUrl: "https://authority.example/evidence", ...overrides
});
function expect(value: unknown, message: string) { if (!value) throw new Error(message); }
expect(assessOfficialExportEvidence([], "honey", "norway", today).state === "NEEDS_VERIFICATION", "Missing evidence must fail closed.");
expect(assessOfficialExportEvidence([record({authority:"secondary"})], "honey", "norway", today).state === "REQUIRES_HUMAN_REVIEW", "Secondary source cannot authorize.");
expect(assessOfficialExportEvidence([record({validTo:"2026-01-01"})], "honey", "norway", today).state === "STALE", "Expired evidence must be explicitly stale and cannot authorize.");
expect(assessOfficialExportEvidence([record({claimStatus:"prohibited"})], "honey", "norway", today).state === "NO_GO", "Prohibition must win.");
expect(assessOfficialExportEvidence([record({claimStatus:"unknown"})], "honey", "norway", today).state === "REQUIRES_HUMAN_REVIEW", "An unknown claim cannot cover an evidence gate.");
expect(assessOfficialExportEvidence([record(), record({id:"E-002", claimStatus:"prohibited"})], "honey", "norway", today).state === "CONFLICT", "Current supported and prohibited evidence must never be silently resolved.");
expect(assessOfficialExportEvidence([record({gates:["country_eligibility"]})], "honey", "norway", today).state === "NEEDS_VERIFICATION", "Partial gates cannot authorize.");
expect(assessOfficialExportEvidence([record({sourceUrl:"not-a-url"})], "honey", "norway", today).state === "REQUIRES_HUMAN_REVIEW", "Evidence without a valid source URL cannot authorize.");
expect(assessOfficialExportEvidence([record({validTo:"2026-99-99"})], "honey", "norway", today).state === "REQUIRES_HUMAN_REVIEW", "Invalid validity dates cannot authorize.");expect(assessOfficialExportEvidence([record()], "honey", "norway", today).state === "SUPPORTED_BY_OFFICIAL_SOURCE", "Full evidence should be supported.");
console.log("official_evidence_gate_check: PASS");
