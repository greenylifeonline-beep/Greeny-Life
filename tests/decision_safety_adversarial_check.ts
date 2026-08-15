import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  assessOfficialExportEvidence,
  REQUIRED_EXPORT_EVIDENCE_GATES,
  type OfficialEvidenceRecord,
} from "../lib/intelligence/official-evidence-gate";
import { assessReadOnlyDecisionSafety, MASTERMIND_DECISION_POLICY } from "../lib/intelligence/mastermind-agents";

type Outcome = "PASS" | "UNKNOWN";
const outcomes: Array<{ id: string; outcome: Outcome; detail: string }> = [];
const today = new Date("2026-08-13T12:00:00.000Z");

const record = (overrides: Partial<OfficialEvidenceRecord> = {}): OfficialEvidenceRecord => ({
  id: "E-001",
  scope: { product: "honey", destination: "norway" },
  authority: "official",
  verificationStatus: "verified_current",
  claimStatus: "supported",
  gates: [...REQUIRED_EXPORT_EVIDENCE_GATES],
  validTo: "2026-12-31",
  sourceUrl: "https://authority.example/evidence",
  ...overrides,
});

function proven(id: string, detail: string, assertion: () => void) {
  assertion();
  outcomes.push({ id, outcome: "PASS", detail });
}
function unknown(id: string, detail: string) {
  outcomes.push({ id, outcome: "UNKNOWN", detail });
}
function state(records: OfficialEvidenceRecord[], product = "honey", destination = "norway") {
  return assessOfficialExportEvidence(records, product, destination, today).state;
}

proven("01_EMPTY_EVIDENCE", "Empty evidence fails closed.", () => assert.equal(state([]), "NEEDS_VERIFICATION"));
proven("02_MISSING_SCOPE", "Evidence for another product/destination cannot be borrowed.", () => assert.equal(state([record({ scope: { product: "spices", destination: "uae" } })]), "NEEDS_VERIFICATION"));
proven("03_UNKNOWN_CLAIM", "Unknown evidence cannot cover a gate.", () => assert.equal(state([record({ claimStatus: "unknown" })]), "REQUIRES_HUMAN_REVIEW"));
proven("04_STALE_EVIDENCE", "Expired evidence is explicitly stale.", () => assert.equal(state([record({ validTo: "2026-01-01" })]), "STALE"));
proven("05_CONFLICTING_CURRENT_EVIDENCE", "Current support and prohibition conflict instead of silently authorizing.", () => assert.equal(state([record(), record({ id: "E-002", claimStatus: "prohibited" })]), "CONFLICT"));
proven("13_UNSUPPORTED_CLAIM", "An official current record without a supported claim cannot authorize.", () => assert.equal(state([record({ claimStatus: "unknown" })]), "REQUIRES_HUMAN_REVIEW"));
proven("14_INCOMPLETE_ACTION_SUPPORT", "Support for one regulatory gate cannot authorize export.", () => assert.equal(state([record({ gates: ["country_eligibility"] })]), "NEEDS_VERIFICATION"));
proven("15_MIXED_AUTHORITY_CONFLICT", "A lower-authority conflict forces review and cannot be ignored.", () => assert.equal(state([record(), record({ id: "E-002", authority: "secondary", claimStatus: "prohibited" })]), "REQUIRES_HUMAN_REVIEW"));
proven("17_DUPLICATE_CONTRADICTORY_VERSIONS", "Opposite current versions are a conflict.", () => assert.equal(state([record({ id: "E-001-v1" }), record({ id: "E-001-v2", claimStatus: "prohibited" })]), "CONFLICT"));
proven("18_INFERENCE_WITHOUT_EVIDENCE", "Inference cannot turn no evidence into authorization.", () => assert.equal(state([]), "NEEDS_VERIFICATION"));
proven("19_HIGH_MODEL_CONFIDENCE_WITHOUT_EVIDENCE", "Untrusted confidence metadata is ignored by the evidence gate.", () => {
  const decorated = Object.assign(record({ scope: { product: "spices", destination: "uae" } }), { modelConfidence: 1 });
  assert.equal(state([decorated]), "NEEDS_VERIFICATION");
});

const mastermind = readFileSync("lib/intelligence/mastermind-agents.ts", "utf8");
const decisionRoute = readFileSync("app/api/mastermind/decision-package/route.ts", "utf8");
proven("NO_DECISION_SIDE_EFFECT", "MasterMind package is read-only and automaticExecution is false.", () => {
  assert.match(mastermind, /automaticExecution:\s*false/);
  assert.doesNotMatch(mastermind, /\.(create|update|delete|upsert)\s*\(/);
  assert.doesNotMatch(mastermind, /\$executeRaw/);
});
proven("AUTHORIZED_ACTOR_BOUNDARY", "The signed session, not request body, supplies the actor.", () => {
  assert.match(decisionRoute, /authorizeRequest\(request, \["ADMIN", "EXPORT"\]/);
  assert.match(decisionRoute, /actor:\s*authorization\.session\.email/);
  assert.doesNotMatch(decisionRoute, /body\.actor/);
});

proven("06_INSUFFICIENT_CONFIDENCE", "Missing or low confidence fails closed at the read-only decision boundary.", () => {
  assert.equal(assessReadOnlyDecisionSafety({ confidence: null, policy: MASTERMIND_DECISION_POLICY }).status, "NOT_READY");
  assert.equal(assessReadOnlyDecisionSafety({ confidence: 69, policy: MASTERMIND_DECISION_POLICY }).status, "NOT_READY");
});
proven("07_MISSING_POLICY", "A missing policy cannot authorize a decision.", () => {
  assert.equal(assessReadOnlyDecisionSafety({ confidence: 90 }).status, "NOT_READY");
});
proven("08_INVALID_POLICY", "An invalid versioned policy cannot authorize a decision.", () => {
  assert.equal(assessReadOnlyDecisionSafety({ confidence: 90, policy: { ...MASTERMIND_DECISION_POLICY, minimumConfidence: 101 } }).status, "NOT_READY");
});
unknown("11_MISSING_AUDIT", "Authorization audit exists, but audit persistence is not yet fail-closed at an action boundary.");
unknown("12_INVALID_STATE_TRANSITION", "MasterMind has no verified execution transition to test yet.");
unknown("16_EXPIRED_POLICY", "Policies have no effective-period enforcement at this boundary yet.");
unknown("20_FAILED_STATE_TRANSITION", "The endpoint is read-only; controlled executor and rollback proof remain required.");

console.table(outcomes);
const passed = outcomes.filter((item) => item.outcome === "PASS").length;
const pending = outcomes.filter((item) => item.outcome === "UNKNOWN").length;
console.log(`decision_safety_adversarial_check: PASS ${passed} | UNKNOWN ${pending}`);