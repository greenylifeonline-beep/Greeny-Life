import assert from "node:assert/strict";
import { NextRequest } from "next/server";

process.env.APP_SESSION_SECRET = "test-secret-which-is-more-than-thirty-two-characters";

async function main() {
  const { GET, POST } = await import("../app/api/trade-corridors/route");
  const read = await GET(new NextRequest("http://localhost/api/trade-corridors"));
  assert.equal(read.status, 401, "Anonymous callers must not read trade governance.");
  const write = await POST(new NextRequest("http://localhost/api/trade-corridors", { method: "POST", body: JSON.stringify({ originCompany: "GREENY_LIFE_EGYPT", destinationCompany: "GREENS_NATURE_UAE", tradeType: "EXPORT", actor: "spoofed@example.test" }), headers: { "content-type": "application/json" } }));
  assert.equal(write.status, 401, "A caller-supplied actor must not create a trade-corridor assessment.");
  assert.equal((await write.json() as { data?: unknown }).data, undefined);
  console.log("trade_corridor_authorization_check: PASS");
}
main().catch((error) => { console.error(error); process.exitCode = 1; });