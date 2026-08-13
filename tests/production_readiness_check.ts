import assert from "node:assert/strict";
import { productionReadinessReport } from "../lib/intelligence/production-readiness";

const report = productionReadinessReport();
assert.ok(["NOT_READY", "CONDITIONAL"].includes(report.overall));
assert.equal(report.gates.find((gate) => gate.id === "RC-01")?.status, "PASS");
assert.equal(report.gates.find((gate) => gate.id === "RC-02")?.status, "CONDITIONAL");
assert.equal(report.gates.find((gate) => gate.id === "RC-04")?.status, "FAIL");
assert.ok(report.gates.find((gate) => gate.id === "RC-04")?.gaps.some((gap) => gap.includes("backup and restore")));
assert.ok(report.nextRequired.some((gap) => gap.includes("backup and restore")));
console.log("Production readiness gate: PASS (production remains blocked by RC-04).");