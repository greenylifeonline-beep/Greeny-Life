import assert from "node:assert/strict";
import { writeRolePolicy } from "../lib/authz";
assert.deepEqual(writeRolePolicy.productMaster, ["ADMIN"]);
assert.ok(writeRolePolicy.salesOrder.includes("SALES"));
assert.ok(writeRolePolicy.traceability.includes("WAREHOUSE"));
assert.equal(writeRolePolicy.evaluation.includes("EXPORT"), false);
console.log("API authorization policy: PASS");