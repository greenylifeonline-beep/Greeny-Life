import { readFileSync } from "node:fs";
const source = readFileSync("app/api/decisions/official-evidence-review/route.ts", "utf8");
function expect(value: unknown, message: string) { if (!value) throw new Error(message); }
expect(source.includes("prisma.officialEvidenceRegistry.findMany"), "Review route must read persisted evidence.");
expect(!source.includes("body.evidence"), "Review route must not accept caller-supplied evidence.");
expect(source.includes("automaticExecution: false"), "Review route must not execute automatically.");
console.log("official_evidence_review_route_check: PASS");