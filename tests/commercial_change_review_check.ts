import assert from "node:assert/strict";

import { commercialChangeReview } from "../lib/intelligence/commercial-change-review";

async function main() {
  const review = await commercialChangeReview("H001");
  assert.equal(review.data.subjectId, "H001");
  assert.equal(review.data.executionRule.includes("proposal"), true);
  assert.ok(["REVIEW_REQUIRED", "NOT_READY"].includes(review.status));
  console.log("Commercial change review: PASS");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
