import assert from "node:assert/strict";
import { NextRequest } from "next/server";

process.env.APP_SESSION_SECRET = "test-secret-which-is-more-than-thirty-two-characters";

async function main() {
  const { createSession } = await import("../lib/auth");
  const { authorizeRequest } = await import("../lib/authz");
  const token = createSession({ userId: "audit-user", email: "admin@example.test", role: "ADMIN" });
  const signedRequest = () => new NextRequest("http://localhost/api/protected", { headers: { cookie: `gl_session=${token}` } });

  const allowed = await authorizeRequest(signedRequest(), ["ADMIN"], "/api/protected", "WRITE", {
    auditWriter: async () => true,
  });
  assert.equal(allowed.response, null, "Authorized request with durable audit must proceed.");

  const blocked = await authorizeRequest(signedRequest(), ["ADMIN"], "/api/protected", "WRITE", {
    auditWriter: async () => false,
  });
  assert.equal(blocked.response?.status, 503, "Authorized request without durable audit must fail closed.");
  assert.equal(blocked.session?.email, "admin@example.test");

  const denied = await authorizeRequest(new NextRequest("http://localhost/api/protected"), ["ADMIN"], "/api/protected", "WRITE", {
    auditWriter: async () => false,
  });
  assert.equal(denied.response?.status, 401, "Missing authentication must remain denied even when audit storage is unavailable.");
  console.log("Authorization audit fail-closed: PASS");
}

main().catch((error) => { console.error(error); process.exitCode = 1; });
