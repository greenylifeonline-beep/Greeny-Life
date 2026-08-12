import assert from "node:assert/strict";

import { toolRegistry } from "../lib/intelligence/tool-registry";

const registry = toolRegistry();
assert.equal(registry.total, 39);
assert.equal(registry.counts.READ_ONLY_READY, 6);
assert.ok(registry.counts.ADAPTER_REQUIRED > 0);
assert.ok(registry.counts.BLOCKED_DIRECT_EXECUTION > 0);
assert.equal(registry.tools.find((tool) => tool.name === "analyze_duplication_reason")?.disposition, "READ_ONLY_READY");
assert.equal(registry.tools.find((tool) => tool.name === "run_deep_clean")?.disposition, "BLOCKED_DIRECT_EXECUTION");
assert.equal(registry.tools.find((tool) => tool.name === "build_inventory_system")?.disposition, "ADAPTER_REQUIRED");

console.log("MasterMind tool registry: PASS");
