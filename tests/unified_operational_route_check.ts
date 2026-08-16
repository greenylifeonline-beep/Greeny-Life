import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

function main() {
  const routePath = path.join(
    process.cwd(),
    "app",
    "api",
    "mastermind",
    "unified-operation",
    "route.ts",
  );

  assert.ok(
    fs.existsSync(routePath),
    "Unified operation route must exist.",
  );

  const source =
    fs.readFileSync(routePath, "utf8");

  assert.match(
    source,
    /buildUnifiedOperationalResult/,
    "Route must call the real GL-005 orchestrator.",
  );

  assert.match(
    source,
    /\/api\/mastermind\/unified-operation/,
    "Route must authorize its exact API path.",
  );

  assert.match(
    source,
    /BUILD_UNIFIED_OPERATIONAL_RESULT/,
    "Route must use a dedicated authorization action.",
  );

  assert.match(
    source,
    /\["ADMIN",\s*"EXPORT"\]/,
    "Unified operation must preserve MasterMind ADMIN/EXPORT policy.",
  );

  assert.doesNotMatch(
    source,
    /greens-nature-uae-brain/,
    "Route must not invent a UAE runtime bridge.",
  );

  assert.doesNotMatch(
    source,
    /greenlines-norway-brain/,
    "Route must not invent a Norway runtime bridge.",
  );

  console.log(
    "unified_operational_route_check: PASS",
  );
}

main();