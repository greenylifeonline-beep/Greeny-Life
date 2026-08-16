import assert from "node:assert/strict";
import { NextRequest } from "next/server";

process.env.APP_SESSION_SECRET =
  "test-secret-which-is-more-than-thirty-two-characters";

async function main() {

  const { createSession } =
    await import("../lib/auth");

  const { POST } =
    await import(
      "../app/api/mastermind/unified-operation/route"
    );

  const token =
    createSession({
      userId: "gl005-admin-test",
      email: "admin@example.test",
      role: "ADMIN",
    });

  const request =
    new NextRequest(
      "http://localhost/api/mastermind/unified-operation",
      {
        method: "POST",

        headers: {
          "content-type": "application/json",
          cookie: `gl_session=${token}`,
        },

        body: JSON.stringify({
          productId: "H001",
          destination: "Norway",
          originCompany: "GREENY_LIFE_EGYPT",
          destinationCompany:
            "GREEN_LINES_NORWAY_EU",
          traceCode: "BATCH-H001-001",
          customerId: "CUS-EU-011",
        }),
      },
    );

  const response =
    await POST(request);

  assert.equal(
    response.status,
    201,
    "Authorized ADMIN request must complete successfully.",
  );

  const payload =
    await response.json() as {
      success?: boolean;

      data?: {
        system?: string;

        mode?: string;

        request?: {
          actor?: string;
          productId?: string;
          destination?: string;
        };

        projectBrains?: {
          egypt?: {
            availability?: string;
            verified?: boolean;
            contribution?: unknown;
          };

          uae?: {
            availability?: string;
            verified?: boolean;
            contribution?: unknown;
          };

          norway?: {
            availability?: string;
            verified?: boolean;
            contribution?: unknown;
          };
        };

        mastermind?: {
          system?: string;
          mode?: string;
          agents?: unknown[];
          decision?: {
            automaticExecution?: boolean;
          };
        };

        unifiedDecision?: {
          automaticExecution?: boolean;
          blockers?: string[];
        };
      };
    };

  assert.equal(
    payload.success,
    true,
    "Successful authorized request must return success=true.",
  );

  assert.ok(
    payload.data,
    "Successful request must return unified operational data.",
  );

  assert.equal(
    payload.data.system,
    "RAIOS Unified Operational Orchestrator",
  );

  assert.equal(
    payload.data.mode,
    "CONDITIONAL_CONVERGENCE",
  );

  // Actor must come from signed session, never request body.
  assert.equal(
    payload.data.request?.actor,
    "admin@example.test",
  );

  // Egypt is a real participating project brain.
  assert.equal(
    payload.data.projectBrains?.egypt?.availability,
    "AVAILABLE",
  );

  assert.equal(
    payload.data.projectBrains?.egypt?.verified,
    true,
  );

  assert.ok(
    payload.data.projectBrains?.egypt?.contribution,
    "Egypt must contribute real operational intelligence.",
  );

  // UAE and Norway remain honest incomplete capabilities.
  assert.equal(
    payload.data.projectBrains?.uae?.availability,
    "UNAVAILABLE",
  );

  assert.equal(
    payload.data.projectBrains?.uae?.verified,
    false,
  );

  assert.equal(
    payload.data.projectBrains?.uae?.contribution,
    null,
  );

  assert.equal(
    payload.data.projectBrains?.norway?.availability,
    "UNAVAILABLE",
  );

  assert.equal(
    payload.data.projectBrains?.norway?.verified,
    false,
  );

  assert.equal(
    payload.data.projectBrains?.norway?.contribution,
    null,
  );

  // MasterMind must actually participate.
  assert.equal(
    payload.data.mastermind?.system,
    "MasterMind AI",
  );

  assert.equal(
    payload.data.mastermind?.mode,
    "READ_ONLY_DECISION_INTELLIGENCE",
  );

  assert.equal(
    payload.data.mastermind?.agents?.length,
    7,
  );

  // GL-005 must preserve non-automatic execution.
  assert.equal(
    payload.data.mastermind?.decision?.automaticExecution,
    false,
  );

  assert.equal(
    payload.data.unifiedDecision?.automaticExecution,
    false,
  );

  assert.ok(
    Array.isArray(
      payload.data.unifiedDecision?.blockers,
    ),
  );

  console.log(
    "unified_operational_authenticated_success_check: PASS",
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});