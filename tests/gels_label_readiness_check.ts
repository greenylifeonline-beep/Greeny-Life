import assert from "node:assert/strict";
import { evaluateGelsLabel } from "../lib/intelligence/gels-label-readiness";

const current = evaluateGelsLabel({ productId: "H001", market: "EU" });
assert.equal(current.status, "NOT_READY");
assert.ok(current.blockers.some((item) => item.startsWith("EAN13")));
assert.ok(current.blockers.some((item) => item.startsWith("COA")));

const complete = evaluateGelsLabel({ productId: "H001", market: "EU", batch: { batchNumber: "H001-20260812-A", productionDate: "2026-08-12", expiryDate: "2028-08-12", numericEan13: "6291041234567", qrUrl: "https://verify.greeny-life.example/batch/H001-20260812-A", coaEvidenceId: "COA-H001-20260812-A", officialMarketEvidenceIds: ["EU-LABEL-REVIEW-001"] } });
assert.equal(complete.status, "READY_FOR_REVIEW");
assert.equal(complete.blockers.length, 0);
assert.ok(complete.executionRule.includes("not print approval"));

assert.equal(evaluateGelsLabel({ productId: "MISSING", market: "EU" }).status, "NOT_READY");
console.log("GELS label readiness: PASS");