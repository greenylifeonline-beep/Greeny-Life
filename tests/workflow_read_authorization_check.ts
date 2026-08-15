import assert from "node:assert/strict";
import { NextRequest } from "next/server";

process.env.APP_SESSION_SECRET = "test-secret-which-is-more-than-thirty-two-characters";

async function main() {
  const { GET } = await import("../app/api/workflow/route");
  const response = await GET(new NextRequest("http://localhost/api/workflow?qty=12abc&price=5&tariff=10&shipping=2"));
  assert.equal(response.status, 401, "Authorization must run before calculator validation or calculation.");
  const body = await response.json() as { success?: boolean; calculation?: unknown };
  assert.equal(body.success, false);
  assert.equal(body.calculation, undefined);
  console.log("workflow_read_authorization_check: PASS");
}
main().catch((error) => { console.error(error); process.exitCode = 1; });