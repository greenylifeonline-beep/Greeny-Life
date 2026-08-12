import assert from "node:assert/strict";

import { greenyLifeEgyptBrainIdentity, greenyLifeEgyptOperationalView } from "../lib/intelligence/greeny-life-egypt-brain";

const overview = greenyLifeEgyptOperationalView();
assert.equal(greenyLifeEgyptBrainIdentity.company, "GREENY_LIFE_EGYPT");
assert.equal(overview.operations.products, 15);
assert.equal(overview.operations.warehouses.length, 2);
assert.equal(overview.brain.escalatesTo, "MasterMind AI");
assert.equal(overview.escalation.executionRule.includes("explicit user approval"), true);

const productView = greenyLifeEgyptOperationalView("H001");
assert.equal(productView.selectedProduct?.id, "H001");
assert.ok(productView.sourceBoundaries.includes("canonical/inventory/stock-levels.json"));
console.log("Greeny-Life Egypt Brain: PASS");
