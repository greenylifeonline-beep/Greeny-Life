import assert from "node:assert/strict";

import { assessFreshness, operationalDataStatus } from "../lib/intelligence/operational-data-freshness";

assert.equal(assessFreshness("2026-08-12T11:00:00.000Z", new Date("2026-08-12T12:00:00.000Z")).state, "RECENT_REFERENCE");
assert.equal(assessFreshness("2026-08-07T00:00:00.000Z", new Date("2026-08-12T12:00:00.000Z")).state, "STALE_REFERENCE");
const review = operationalDataStatus({ stockUpdatedAt: ["2026-08-07T00:00:00.000Z"], supplierGeneratedAt: "2026-08-07T00:00:00.000Z", shipmentUpdatedAt: [] });
assert.equal(review.status, "REVIEW_REQUIRED");
assert.equal(review.executionRule.includes("never authorize"), true);
console.log("Operational data freshness: PASS");
