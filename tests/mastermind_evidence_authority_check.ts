import { readFileSync } from "node:fs";
const agent = readFileSync("lib/intelligence/mastermind-agents.ts", "utf8");
const route = readFileSync("app/api/mastermind/decision-package/route.ts", "utf8");
function expect(value: unknown, message: string) { if (!value) throw new Error(message); }
expect(agent.includes("prisma.officialEvidenceRegistry.findMany"), "MasterMind must read persisted official evidence.");
expect(agent.includes("assessOfficialExportEvidence"), "MasterMind must use the official evidence gate.");
expect(route.includes("authorizeRequest"), "Decision package route must require authorization.");
expect(route.includes("actor: authorization.session.email"), "Decision actor must come from signed session.");
expect(!route.includes("body.actor"), "Caller must not supply the decision actor.");
console.log("mastermind_evidence_authority_check: PASS");