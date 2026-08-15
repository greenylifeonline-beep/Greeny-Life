import assert from "node:assert/strict";
import { NextRequest } from "next/server";

process.env.APP_SESSION_SECRET = "test-secret-which-is-more-than-thirty-two-characters";

async function main() {
  const { GET } = await import("../app/api/brains/greeny-life-egypt/route");
  const response = await GET(new NextRequest("http://localhost/api/brains/greeny-life-egypt?productId=H001"));
  assert.equal(response.status, 401, "Anonymous callers must not receive the Egypt operational view.");
  assert.equal((await response.json() as { data?: unknown }).data, undefined);
  console.log("greeny_life_egypt_brain_authorization_check: PASS");
}
main().catch((error) => { console.error(error); process.exitCode = 1; });