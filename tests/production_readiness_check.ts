import assert from "node:assert/strict";
import { productionReadinessReport } from "../lib/intelligence/production-readiness";

const report = productionReadinessReport();
assert.equal(report.overall, "NOT_READY");
assert.equal(report.gates.find((gate) => gate.id === "RC-01")?.status, "PASS");
assert.equal(report.gates.find((gate) => gate.id === "RC-02")?.status, "FAIL");
assert.equal(report.gates.find((gate) => gate.id === "RC-04")?.status, "FAIL");
assert.ok(report.nextRequired.some((gap) => gap.includes("authentication")));
console.log("Production readiness gate: PASS");