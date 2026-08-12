import assert from "node:assert/strict";

import { shipmentTrackingReview } from "../lib/intelligence/shipment-tracking-review";

const review = shipmentTrackingReview("H001");
assert.equal(review.status, "REVIEW_REQUIRED");
assert.ok(review.records.length > 0);
assert.ok(review.summary.staleRecords > 0);
assert.ok(review.blockers.some((blocker) => blocker.includes("carrier API")));
assert.equal(review.executionRule.includes("does not release"), true);
console.log("Shipment tracking review: PASS");
