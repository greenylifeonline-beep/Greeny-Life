import fs from "fs";
import path from "path";
import { ENGINE_REGISTRY } from "../core/engine-registry";

const ROOT = process.cwd();

function checkEngineFiles() {
  return ENGINE_REGISTRY.map((engine) => {
    const file = path.join(ROOT, engine.location);
    return {
      name: engine.name,
      capability: engine.capability,
      version: engine.version,
      status: engine.status,
      location: engine.location,
      exists: fs.existsSync(file),
    };
  });
}

/** Read-only health. Does not write reports/ (locked) and does not invent missing engines. */
export function generateHealthReport() {
  const engines = checkEngineFiles();
  return {
    generated: new Date().toISOString(),
    system: "GREENY-LIFE",
    status: engines.every((engine) => engine.exists && engine.status === "ACTIVE")
      ? "HEALTHY"
      : "WARNING",
    engines,
    executionRule: "File presence is not runtime proof. Pair with tests/canonical_intelligence_check.ts and tests/task_orchestration_check.ts.",
  };
}
