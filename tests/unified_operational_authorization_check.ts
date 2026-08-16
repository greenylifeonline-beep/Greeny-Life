import assert from "node:assert/strict";
import { NextRequest } from "next/server";

process.env.APP_SESSION_SECRET =
  "test-secret-which-is-more-than-thirty-two-characters";

async function main() {
  const { POST } =
    await import(
      "../app/api/mastermind/unified-operation/route"
    );

  const response =
    await POST(
      new NextRequest(
        "http://localhost/api/mastermind/unified-operation",
        {
          method: "POST",
          headers: {
            "content-type": "application/json",
          },
          body: JSON.stringify({
            productId: "H001",
            destination: "Norway",
            originCompany: "GREENY_LIFE_EGYPT",
            destinationCompany:
              "GREEN_LINES_NORWAY_EU",
          }),
        },
      ),
    );

  assert.equal(
    response.status,
    401,
    "Anonymous callers must not execute unified operational intelligence.",
  );

  const payload =
    await response.json() as {
      success?: boolean;
      data?: unknown;
    };

  assert.equal(
    payload.data,
    undefined,
    "Unauthorized callers must receive no unified operational data.",
  );

  console.log(
    "unified_operational_authorization_check: PASS",
  );
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});