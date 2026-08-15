import assert from "node:assert/strict";
import { NextRequest } from "next/server";

process.env.APP_SESSION_SECRET = "test-secret-which-is-more-than-thirty-two-characters";

async function main() {
  const { GET } = await import("../app/api/intelligence/data-fabric/route");
  const response = await GET(new NextRequest("http://localhost/api/intelligence/data-fabric?consumer=MASTERMIND_AI&domain=SUPPLIER&domain=INVENTORY"));
  assert.equal(response.status, 401, "Anonymous callers must not self-declare an internal Fabric consumer.");
  const body = await response.json() as { success?: boolean; data?: unknown };
  assert.equal(body.success, false);
  assert.equal(body.data, undefined);
  console.log("data_fabric_authorization_check: PASS");
}
main().catch((error) => { console.error(error); process.exitCode = 1; });