import assert from "node:assert/strict";
import { NextRequest } from "next/server";

process.env.APP_SESSION_SECRET = "test-secret-which-is-more-than-thirty-two-characters";

async function main() {
  const { GET } = await import("../app/api/mastermind/commercial-context/route");
  const response = await GET(new NextRequest("http://localhost/api/mastermind/commercial-context"));
  assert.equal(response.status, 401, "Anonymous callers must not read customer, opportunity, and market-ownership context.");
  assert.equal((await response.json() as { data?: unknown }).data, undefined);
  console.log("commercial_context_authorization_check: PASS");
}
main().catch((error) => { console.error(error); process.exitCode = 1; });