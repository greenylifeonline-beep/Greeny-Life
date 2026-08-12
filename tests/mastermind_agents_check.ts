import assert from "node:assert/strict";

import { buildMasterMindDecisionPackage } from "../lib/intelligence/mastermind-agents";

async function main() {
  const decision = await buildMasterMindDecisionPackage({
    productId: "H001",
    destination: "Norway",
    originCompany: "GREENY_LIFE_EGYPT",
    destinationCompany: "GREEN_LINES_NORWAY_EU",
    actor: "test-reviewer",
    traceCode: "BATCH-H001-001",
  });

  assert.equal(decision.system, "MasterMind AI");
  assert.equal(decision.mode, "READ_ONLY_DECISION_INTELLIGENCE");
  assert.equal(decision.decision.automaticExecution, false);
  assert.equal(decision.agents.length, 5);
  assert.equal(decision.decision.status, "NOT_READY");
  assert.ok(decision.blockers.some((blocker) => blocker.startsWith("EVIDENCE_COMPLIANCE:")));
  console.log("MasterMind agents: PASS");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
