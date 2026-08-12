import assert from "node:assert/strict";

import { initialOwnership, validateTraceRecord } from "../lib/domain/trade-traceability";

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
assert.match(
  validateTraceRecord({ ...raw, recordType: "PLAN_REEXPORT", parentTraceCode: "RAW-EU-0001", destinationParty: "MASTERMIND" }).join(" "),
  /MasterMind/,
);

console.log("Trade traceability rules: PASS");
