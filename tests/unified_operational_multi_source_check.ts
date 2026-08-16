import assert from "node:assert/strict";

import {
  buildUnifiedOperationalResult,
} from "../lib/intelligence/unified-operational-orchestrator";


async function main() {

  const result =
    await buildUnifiedOperationalResult({
      productId: "H001",
      destination: "Norway",

      originCompany:
        "GREENY_LIFE_EGYPT",

      destinationCompany:
        "GREEN_LINES_NORWAY_EU",

      actor:
        "multi-source-test",

      traceCode:
        "BATCH-H001-001",

      customerId:
        "CUS-EU-011",
    });


  assert.equal(
    result.system,
    "RAIOS Unified Operational Orchestrator",
  );


  // ----------------------------------------------------------
  // Egypt source
  // ----------------------------------------------------------

  assert.equal(
    result.operationalSources
      .egypt.status,
    "AVAILABLE",
  );

  assert.ok(
    result.operationalSources
      .egypt.contribution,
  );


  // ----------------------------------------------------------
  // Commercial Context source
  // ----------------------------------------------------------

  assert.equal(
    result.operationalSources
      .commercialContext.source,
    "CANONICAL_CUSTOMER_DOMAIN",
  );

  assert.ok(
    result.operationalSources
      .commercialContext.contribution,
  );

  assert.ok(
    Array.isArray(
      result.operationalSources
        .commercialContext
        .contribution.evidence,
    ),
  );


  // ----------------------------------------------------------
  // Trade Corridor contribution
  // ----------------------------------------------------------

  assert.equal(
    result.operationalSources
      .tradeCorridor.source,
    "MASTERMIND_TRADE_CORRIDOR_AGENT",
  );

  assert.ok(
    result.operationalSources
      .tradeCorridor.contribution,
    "Trade Corridor must be present in the MasterMind result.",
  );

  assert.equal(
    result.operationalSources
      .tradeCorridor
      .contribution?.agent,
    "TRADE_CORRIDOR",
  );


  // ----------------------------------------------------------
  // MasterMind synthesis
  // ----------------------------------------------------------

  assert.equal(
    result.mastermind.system,
    "MasterMind AI",
  );

  assert.equal(
    result.mastermind.agents.length,
    7,
  );


  // ----------------------------------------------------------
  // Missing project brains remain non-blocking
  // ----------------------------------------------------------

  assert.equal(
    result.projectBrains.uae.availability,
    "UNAVAILABLE",
  );

  assert.equal(
    result.projectBrains.norway.availability,
    "UNAVAILABLE",
  );


  assert.equal(
    result.unifiedDecision
      .automaticExecution,
    false,
  );


  console.log(
    "GL-005 multi-source operational intelligence: PASS",
  );
}


main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});