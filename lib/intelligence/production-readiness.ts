import fs from "node:fs";
import path from "node:path";

export type GateStatus = "PASS" | "CONDITIONAL" | "FAIL";
export interface ReadinessGate { id: string; area: string; status: GateStatus; evidence: string[]; gaps: string[]; requiredBeforeProduction: boolean; }

function exists(relative: string) { return fs.existsSync(path.join(process.cwd(), relative)); }
function fileIncludes(relative: string, pattern: RegExp) { try { return pattern.test(fs.readFileSync(path.join(process.cwd(), relative), "utf8")); } catch { return false; } }

export function productionReadinessReport() {
  const authPresent = exists("app/api/auth") || exists("lib/auth.ts") || exists("middleware.ts");
  const migrationPresent = exists("prisma/migrations") && fs.readdirSync(path.join(process.cwd(), "prisma/migrations")).some((item) => item !== "migration_lock.toml");
  const backupPresent = exists("scripts/backup-postgres.ps1") && exists("scripts/restore-postgres.ps1");
  const dockerPresent = exists("Dockerfile") && (exists("docker-compose.yml") || exists("compose.yml") || exists("compose.yaml"));
  const envExample = exists(".env.example");
  const ciPresent = exists(".github/workflows/govern.yml");
  const healthPresent = exists("app/api/health/route.ts");
  const controlledWrites = fileIncludes("canonical/intelligence/adapters/gl-dos-governance-gate.ts", /No operational write is automatically authorized/);
  const gates: ReadinessGate[] = [
    { id: "RC-01", area: "Build and controlled writes", status: controlledWrites ? "PASS" : "FAIL", evidence: ["canonical/intelligence/adapters/gl-dos-governance-gate.ts"], gaps: controlledWrites ? [] : ["Controlled-write governance evidence is absent."], requiredBeforeProduction: true },
    { id: "RC-02", area: "Authentication and authorization", status: authPresent ? "CONDITIONAL" : "FAIL", evidence: authPresent ? ["Authentication entrypoint detected"] : [], gaps: authPresent ? ["Role enforcement and session security require independent proof."] : ["No authentication, session, or API authorization implementation was detected."], requiredBeforeProduction: true },
    { id: "RC-03", area: "Database migration discipline", status: migrationPresent ? "CONDITIONAL" : "FAIL", evidence: migrationPresent ? ["prisma/migrations"] : ["prisma/schema.prisma only"], gaps: migrationPresent ? ["Migration replay and JSON-to-PostgreSQL reconciliation must be tested."] : ["No committed Prisma migration history was detected."], requiredBeforeProduction: true },
    { id: "RC-04", area: "Backups and restore", status: backupPresent ? "CONDITIONAL" : "FAIL", evidence: backupPresent ? ["scripts/backup-postgres.ps1", "scripts/restore-postgres.ps1"] : [], gaps: backupPresent ? ["A restore drill must be recorded."] : ["No PostgreSQL backup and restore scripts were detected."], requiredBeforeProduction: true },
    { id: "RC-05", area: "Infrastructure and secrets", status: dockerPresent && envExample ? "CONDITIONAL" : "FAIL", evidence: [dockerPresent ? "Docker deployment files" : "", envExample ? ".env.example" : ""].filter(Boolean), gaps: [!dockerPresent ? "No Dockerfile and Compose deployment definition detected." : "", !envExample ? "No safe .env.example contract detected." : ""].filter(Boolean), requiredBeforeProduction: true },
    { id: "RC-06", area: "Monitoring and health", status: healthPresent ? "CONDITIONAL" : "FAIL", evidence: healthPresent ? ["app/api/health/route.ts"] : [], gaps: healthPresent ? ["External alerting and dashboard evidence are still required."] : ["No application health endpoint was detected."], requiredBeforeProduction: true },
    { id: "RC-07", area: "Continuous verification", status: ciPresent ? "CONDITIONAL" : "FAIL", evidence: ciPresent ? [".github/workflows/govern.yml"] : [], gaps: ciPresent ? ["CI must run type checks, tests, and production build on every release candidate."] : ["No governed CI workflow was detected."], requiredBeforeProduction: true },
    { id: "RC-08", area: "Operational intelligence safety", status: "CONDITIONAL", evidence: ["Greeny-Life verification harness", "GELS readiness validator", "Data Intelligence Fabric"], gaps: ["Canonical operational data is reference data; live integrations, formal UAT, and evidence refresh are still required."], requiredBeforeProduction: true },
  ];
  const requiredFailures = gates.filter((gate) => gate.requiredBeforeProduction && gate.status === "FAIL");
  return {
    system: "GREENY-LIFE Production Readiness Gate",
    releaseDefinition: "v1.0 is a controlled, human-approved export/import operating workflow; it is not autonomous commercial execution.",
    overall: requiredFailures.length ? "NOT_READY" : "CONDITIONAL",
    gates,
    nextRequired: requiredFailures.flatMap((gate) => gate.gaps),
    rule: "The system must not be declared production-ready while any required gate is FAIL. CONDITIONAL gates require documented evidence and an authorized go-live review.",
  };
}