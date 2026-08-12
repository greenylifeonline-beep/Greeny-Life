import assert from "node:assert/strict";

import { initialOwnership, validateTraceRecord } from "../lib/domain/trade-traceability";
import { findLegacyBatch, legacyBatchRegistry } from "../lib/intelligence/legacy-batch-traceability";

const raw = {
  recordType: "RECEIVE_RAW_MATERIAL" as const,
  traceCode: "RAW-EU-0001",
  sourceParty: "External European Supplier",
  holderCompany: "GREENY_LIFE_EGYPT",
  materialName: "Raw botanical material",
  batchCode: "SUP-LOT-0001",
  quantity: 250,
  unit: "kg",
  originCountry: "Norway",
  actor: "test-operator",
};
assert.deepEqual(validateTraceRecord(raw), []);
assert.equal(initialOwnership(raw)[0].legalTitleTransferred, false);
assert.match(initialOwnership(raw)[0].note, /customs filing/);

assert.match(
  validateTraceRecord({ ...raw, recordType: "TRANSFORM_OR_PACKAGE", parentTraceCode: undefined })[0],
  /parentTraceCode/,
);

const legacy = legacyBatchRegistry();
assert.equal(legacy.records.length, 15);
assert.equal(legacy.status, "HISTORICAL_REFERENCE_NOT_CURRENT_EVIDENCE");
assert.deepEqual(legacy.inconsistencies, []);
assert.deepEqual(findLegacyBatch("BATCH-H001-001"), {
  batchCode: "BATCH-H001-001",
  productId: "H001",
  productName: "Wildflower Honey",
  originCountry: "Egypt",
  traceability: "ENABLED",
  qualityCheck: "PASSED",
  source: "OPERATIONS_EXPORT_FLOW_V1",
});
assert.match(
  validateTraceRecord({ ...raw, recordType: "PLAN_REEXPORT", parentTraceCode: "RAW-EU-0001", destinationParty: "MASTERMIND" }).join(" "),
  /MasterMind/,
);

console.log("Trade traceability rules: PASS");
