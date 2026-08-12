import assert from "node:assert/strict";

import { customerContext, commercialContextSummary } from "../lib/intelligence/commercial-context-fabric";

const aligned = customerContext({
  customerId: "CUS-GCC-001",
  productId: "H001",
  destination: "UAE",
  destinationCompany: "GREENS_NATURE_UAE",
});
assert.equal(aligned.status, "SUPPORTED");
assert.equal(aligned.data?.recommendedOperatingCompany, "GREENS_NATURE_UAE");

const mismatch = customerContext({
  customerId: "CUS-GCC-001",
  productId: "H001",
  destination: "Norway",
  destinationCompany: "GREEN_LINES_NORWAY_EU",
});
assert.equal(mismatch.status, "REVIEW_REQUIRED");
assert.ok(mismatch.blockers.some((blocker) => blocker.includes("does not match")));

assert.equal(commercialContextSummary().customerCount, 30);
console.log("Commercial context fabric: PASS");
