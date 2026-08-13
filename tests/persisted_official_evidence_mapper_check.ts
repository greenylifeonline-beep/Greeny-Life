import assert from "node:assert/strict";
import { mapPersistedOfficialEvidence } from "../lib/intelligence/persisted-official-evidence";

const mapped = mapPersistedOfficialEvidence({
  evidenceKey: "EV-1", product: "H001", destination: "Norway", authority: "official",
  verificationStatus: "verified_current", claimStatus: "supported", validTo: new Date("2026-12-31T00:00:00.000Z"),
  gates: ["country_eligibility", "invalid_gate"], sourceUrl: "https://authority.example/evidence",
});
assert.equal(mapped.authority, "official");
assert.equal(mapped.verificationStatus, "verified_current");
assert.equal(mapped.claimStatus, "supported");
assert.deepEqual(mapped.gates, ["country_eligibility"]);
assert.equal(mapped.validTo, "2026-12-31");
assert.equal(mapped.sourceUrl, "https://authority.example/evidence");
const unknown = mapPersistedOfficialEvidence({
  evidenceKey: "EV-2", product: "H001", destination: "Norway", authority: "fabricated",
  verificationStatus: "fabricated", claimStatus: "fabricated", validTo: null, gates: "not-an-array", sourceUrl: null,
});
assert.equal(unknown.authority, "unknown");
assert.equal(unknown.verificationStatus, "unknown");
assert.equal(unknown.claimStatus, "unknown");
assert.deepEqual(unknown.gates, []);
assert.equal(unknown.sourceUrl, undefined);
console.log("persisted_official_evidence_mapper_check: PASS");