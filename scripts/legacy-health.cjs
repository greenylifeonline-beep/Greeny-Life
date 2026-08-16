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
      "/api/auth/login",
      "/api/auth/logout",
      "/api/auth/session",
      "/api/brains/greeny-life-egypt",
      "/api/commercial-changes",
      "/api/data-control",
      "/api/decisions/export-readiness",
      "/api/decisions/official-evidence-review",
      "/api/evidence/official",
      "/api/intelligence/asset-registry",
      "/api/intelligence/data-fabric",
      "/api/intelligence/gels-label-readiness",
      "/api/intelligence/production-readiness",
      "/api/learning/evaluations",
      "/api/learning/outcomes",
      "/api/learning/training-cases",
      "/api/mastermind/commercial-context",
      "/api/mastermind/decision-package",
      "/api/mastermind/operating-model",
      "/api/mastermind/tools",
      "/api/portfolio/egyptian-exports",
      "/api/products",
      "/api/sales-orders",
      "/api/suppliers",
      "/api/tasks",
      "/api/traceability",
      "/api/trade-corridors",
      "/api/workflow",
      "/api/workflow/approvals",
    ],
    missingBrainRoutes: [
      "/api/brains/greens-nature-uae",
      "/api/brains/greenlines-norway",
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
