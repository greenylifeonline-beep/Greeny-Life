import assert from "node:assert/strict";

import {
  buildUnifiedOperationalResult,
} from "../lib/intelligence/unified-operational-orchestrator";

async function main() {

  const result =
    await buildUnifiedOperationalResult({
      productId: "H001",
      destination: "Norway",
      originCompany: "GREENY_LIFE_EGYPT",
      destinationCompany: "GREEN_LINES_NORWAY_EU",
      actor: "gl005-test-reviewer",
      traceCode: "BATCH-H001-001",
      customerId: "CUS-EU-011",
    });

  // Unified orchestrator is actually running.
  assert.equal(
    result.system,
    "RAIOS Unified Operational Orchestrator",
  );

  assert.equal(
    result.mode,
    "CONDITIONAL_CONVERGENCE",
  );

  // Egypt contributes real verified runtime intelligence.
  assert.equal(
    result.projectBrains.egypt.availability,
    "AVAILABLE",
  );

  assert.equal(
    result.projectBrains.egypt.verified,
    true,
  );

  assert.ok(
    result.projectBrains.egypt.contribution,
  );

  // Missing project brains remain explicit.
  assert.equal(
    result.projectBrains.uae.availability,
    "UNAVAILABLE",
  );

  assert.equal(
    result.projectBrains.uae.contribution,
    null,
  );

  assert.equal(
    result.projectBrains.norway.availability,
    "UNAVAILABLE",
  );

  assert.equal(
    result.projectBrains.norway.contribution,
    null,
  );

  // Their absence does NOT stop MasterMind.
  assert.equal(
    result.mastermind.system,
    "MasterMind AI",
  );

  assert.equal(
    result.mastermind.mode,
    "READ_ONLY_DECISION_INTELLIGENCE",
  );

  assert.equal(
    result.mastermind.agents.length,
    7,
  );

  // Unified result preserves real MasterMind decision truth.
  assert.equal(
    result.unifiedDecision.status,
    result.mastermind.decision.status,
  );

  assert.equal(
    result.unifiedDecision.automaticExecution,
    false,
  );

  assert.deepEqual(
    result.unifiedDecision.blockers,
    result.mastermind.blockers,
  );

  // No missing brain silently becomes fabricated data.
  assert.equal(
    result.projectBrains.uae.verified,
    false,
  );

  assert.equal(
    result.projectBrains.norway.verified,
    false,
  );

  console.log(
    "GL-005 unified operational orchestrator: PASS",
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});