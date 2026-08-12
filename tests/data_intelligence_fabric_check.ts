import assert from "node:assert/strict";
import { dataFabricCatalog, distributeFabricContext } from "../lib/intelligence/data-intelligence-fabric";

const catalog = dataFabricCatalog();
assert.equal(catalog.domains.length, 4);
assert.equal(catalog.quality.PRODUCT.count, 15);
assert.ok(catalog.executionRule.includes("never authorizes"));

const mastermind = distributeFabricContext({ consumer: "MASTERMIND_AI", productId: "H001", domains: ["PRODUCT", "INVENTORY", "SHIPMENT"] });
assert.equal(mastermind.status, "READ_ONLY_CONTEXT_READY");
assert.equal(mastermind.deniedDomains.length, 0);
assert.equal((mastermind.context.product as { id: string }).id, "H001");

const uae = distributeFabricContext({ consumer: "GREENS_NATURE_UAE_BRAIN", productId: "H001", domains: ["PRODUCT", "SUPPLIER"] });
assert.equal(uae.status, "PARTIAL_CONTEXT_REVIEW_REQUIRED");
assert.ok(uae.deniedDomains.includes("SUPPLIER"));
assert.equal("suppliers" in uae.context, false);
assert.ok(uae.executionRule.includes("does not alter ownership"));
console.log("Data intelligence fabric: PASS");