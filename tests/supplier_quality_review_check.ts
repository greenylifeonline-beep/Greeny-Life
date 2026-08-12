import assert from "node:assert/strict";

import { supplierQualityReview } from "../lib/intelligence/supplier-quality-review";

const honey = supplierQualityReview("H001");
assert.equal(honey.status, "NOT_READY");
assert.equal(honey.suppliers[0]?.id, "SUP-EGY-HONEY-001");
assert.ok(honey.blockers.some((blocker) => blocker.includes("audit status pending")));
assert.ok(honey.blockers.some((blocker) => blocker.includes("Certificate links")));

const spice = supplierQualityReview("S001");
assert.equal(spice.status, "NOT_READY");
assert.ok(spice.blockers.some((blocker) => blocker.includes("not active")));
assert.ok(spice.blockers.some((blocker) => blocker.includes("not marked export-ready")));
console.log("Supplier quality review: PASS");
