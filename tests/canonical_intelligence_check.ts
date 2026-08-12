import assert from "node:assert/strict";

import { runAuditEngine } from "../canonical/intelligence/intelligence/engines/audit-engine";
import { runIntegrityEngine } from "../canonical/intelligence/intelligence/engines/data-integrity-engine";

const audit = runAuditEngine();
assert.equal(audit.summary.sources_checked, 1);
assert.equal(audit.summary.products_checked, 15);
assert.equal(audit.summary.errors, 0);

const integrity = runIntegrityEngine();
assert.equal(integrity.summary.canonical_products, 15);
assert.equal(integrity.summary.unique_products, 15);
assert.equal(integrity.summary.errors, 0);
assert.equal(integrity.summary.health, "HEALTHY");

console.log("Canonical intelligence engines: PASS");
