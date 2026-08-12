import assert from "node:assert/strict";

import { runGreenyLifeVerification } from "../lib/intelligence/greeny-life-verification";

async function main() {
  const report = await runGreenyLifeVerification();
  assert.equal(report.overall, "CONDITIONAL");
  assert.equal(report.maturity, "LEVEL_1_FUNCTIONAL");
  assert.equal(report.summary.failed, 0);
  assert.equal(report.summary.conditional, 1);
  assert.equal(report.summary.total, 7);
  assert.equal(report.qualityGates.evidenceFabrication, "FAIL_ON_ANY");
  assert.equal(report.traces.find((item) => item.scenarioId === "T05-UNKNOWN-PRODUCT")?.result, "PASS");
  assert.equal(report.traces.find((item) => item.scenarioId === "T10-CONTROLLED-LEARNING")?.result, "CONDITIONAL");
  console.log("Greeny-Life verification harness: PASS");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
