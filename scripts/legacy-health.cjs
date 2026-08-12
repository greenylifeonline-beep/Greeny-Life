const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const exists = (relativePath) => fs.existsSync(path.join(root, relativePath));
const readJson = (relativePath) => JSON.parse(fs.readFileSync(path.join(root, relativePath), "utf8").replace(/^\uFEFF/, ""));

const legacyBrainFiles = [
  "greenlines_brain/kernel.py",
  "greenlines_brain/evidence_gate.py",
  "greenlines_brain/decision.py",
  "greenlines_brain/dna/extracted_knowledge.json",
  "tests/test_evidence_gate.py",
];

const staleLegacyTargets = [
  "intelligence/index.ts",
  "intelligence/product-audit.ts",
  "intelligence/intelligence-test.ts",
  "intelligence/test/test-registry.ts",
  "intelligence/test/test-health.ts",
  "intelligence/test/test-cleanup.ts",
  "intelligence/test/test-duplicate-v2.ts",
  "intelligence/test/test-audit.ts",
  "intelligence/test/test-integrity.ts",
  "intelligence/gl-dos.ts",
];

const emptyLegacyLayers = {
  domain: 18,
  application: 18,
  database: 9,
};

function health() {
  const knowledge = exists("greenlines_brain/dna/extracted_knowledge.json")
    ? readJson("greenlines_brain/dna/extracted_knowledge.json")
    : null;
  return {
    system: "GREENY-LIFE legacy repair",
    status: legacyBrainFiles.every(exists) ? "REVIEW_REQUIRED" : "FAILED",
    activeRuntime: [
      "/api/decisions/export-readiness",
      "/api/commercial-changes",
      "/api/trade-corridors",
      "/api/portfolio/egyptian-exports",
    ],
    legacyEvidenceBrain: {
      status: "AVAILABLE_FAIL_CLOSED",
      filesPresent: Object.fromEntries(legacyBrainFiles.map((file) => [file, exists(file)])),
      knowledge: knowledge
        ? {
            entities: knowledge.entities?.length ?? 0,
            businessRules: knowledge.business_rules?.length ?? 0,
            evidence: knowledge.evidence?.length ?? 0,
            capabilities: knowledge.capabilities?.length ?? 0,
          }
        : null,
      rule: "Missing or non-current evidence must block execution and require verification.",
    },
    retiredCommands: staleLegacyTargets.filter((target) => !exists(target)),
    legacyLayers: {
      status: "SKELETONS_NOT_RUNTIME",
      emptyFiles: emptyLegacyLayers,
      totalEmptyFiles: Object.values(emptyLegacyLayers).reduce((total, count) => total + count, 0),
      activeReplacement: "lib/domain/order-workflow.ts and the Prisma-backed API routes",
      rule: "Empty historical files are retained as architectural evidence only; they cannot be claimed as executed business logic.",
    },
    repairRule: "Old source is retained as evidence or reusable code; only verified adapters enter the final runtime.",
  };
}

const mode = process.argv[2] ?? "--health";
if (mode === "--blocked-migration") {
  console.error("Migration is intentionally blocked: no legacy data migration runs without a reviewed mapping and approval.");
  process.exit(2);
}

console.log(JSON.stringify(health(), null, 2));
