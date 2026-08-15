import assert from "node:assert/strict";
import { NextRequest } from "next/server";

process.env.APP_SESSION_SECRET = "test-secret-which-is-more-than-thirty-two-characters";

async function main() {
  const { GET } = await import("../app/api/suppliers/route");
  const response = await GET(new NextRequest("http://localhost/api/suppliers"));
  assert.equal(response.status, 401, "Anonymous callers must not receive supplier-master records.");
  const body = await response.json() as { success?: boolean; data?: unknown };
  assert.equal(body.success, false);
  assert.equal(body.data, undefined);
  console.log("supplier_read_authorization_check: PASS");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});