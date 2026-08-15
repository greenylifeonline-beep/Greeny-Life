import assert from "node:assert/strict";

const { evaluateImportData } = require("../scripts/data-import-preflight.cjs") as {
  evaluateImportData: (input: { suppliers: unknown[]; links: unknown[]; products: unknown[]; customers: unknown[]; orders: unknown[] }) => { blocked: boolean; decision: string; integrity: { invalidOrderTotals: Array<{ orderId: string }> }; warnings: { historicalPriceVariations: unknown[] }; remediation: { candidateCount: number; candidates: Array<{ status: string; action: string }> } };
};

const base = {
  suppliers: [{ supplier_id: "S-1" }],
  links: [{ supplier_id: "S-1", product_id: "P-1" }],
  products: [{ id: "P-1" }],
  customers: [{ customer_id: "C-1" }],
};

const historicalVariation = evaluateImportData({ ...base, orders: [
  { order_id: "O-1", customer_id: "C-1", product_id: "P-1", quantity: 2, unit_price: 10, total_price: 20 },
  { order_id: "O-2", customer_id: "C-1", product_id: "P-1", quantity: 2, unit_price: 15, total_price: 30 },
] });
assert.equal(historicalVariation.blocked, false);
assert.equal(historicalVariation.decision, "IMPORT_REVIEW_REQUIRED_APPROVED_COMMERCIAL_CATALOGUE");
assert.equal(historicalVariation.warnings.historicalPriceVariations.length, 1);

const invalidTotal = evaluateImportData({ ...base, orders: [
  { order_id: "O-3", customer_id: "C-1", product_id: "P-1", quantity: 2, unit_price: 10, total_price: 19 },
] });
assert.equal(invalidTotal.blocked, true);
assert.equal(invalidTotal.decision, "IMPORT_BLOCKED_INVALID_REFERENCES_OR_TOTALS");
assert.deepEqual(invalidTotal.integrity.invalidOrderTotals.map((item) => item.orderId), ["O-3"]);
assert.equal(invalidTotal.remediation.candidateCount, 1);
assert.equal(invalidTotal.remediation.candidates[0].status, "REVIEW_REQUIRED");
assert.equal(invalidTotal.remediation.candidates[0].action.includes("No automatic correction"), true);

console.log("data_import_preflight_check: PASS");
