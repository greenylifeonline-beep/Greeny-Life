import assert from "node:assert/strict";
import { NextRequest } from "next/server";

process.env.APP_SESSION_SECRET = "test-secret-which-is-more-than-thirty-two-characters";

async function main() {
  const { GET } = await import("../app/api/decisions/export-readiness/route");

  const anonymous = await GET(new NextRequest(
    "http://localhost/api/decisions/export-readiness?productId=GL-001&destination=Norway",
  ));
  assert.equal(anonymous.status, 401, "Unauthenticated export-readiness reads must be denied.");
  const body = await anonymous.json() as { success?: boolean; data?: unknown };
  assert.equal(body.success, false);
  assert.equal(body.data, undefined, "Denied requests must not disclose a decision package.");

  const missingInput = await GET(new NextRequest("http://localhost/api/decisions/export-readiness"));
  assert.equal(missingInput.status, 401, "Authorization must run before decision-input validation.");
  console.log("export_readiness_authorization_check: PASS");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
