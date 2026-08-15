import assert from "node:assert/strict";

import { createAssetIntelligenceRequest, createE5ConflictReview, createE5MaintenanceCycle, createE5TreatmentApprovalPackage, createE5UnifiedMaintenanceCycle, createE6AssuranceReview, createMaintenancePlan, toolRegistry } from "../lib/intelligence/tool-registry";

const registry = toolRegistry();
assert.equal(registry.total, 39);
assert.equal(registry.counts.READ_ONLY_READY, 6);
assert.ok(registry.counts.ADAPTER_REQUIRED > 0);
assert.ok(registry.counts.BLOCKED_DIRECT_EXECUTION > 0);
assert.equal(registry.tools.find((tool) => tool.name === "analyze_duplication_reason")?.disposition, "READ_ONLY_READY");
assert.equal(registry.tools.find((tool) => tool.name === "run_deep_clean")?.disposition, "BLOCKED_DIRECT_EXECUTION");
assert.equal(registry.tools.find((tool) => tool.name === "build_inventory_system")?.disposition, "ADAPTER_REQUIRED");
assert.equal(registry.assetIntelligence.id, "E4-ASSET-INTELLIGENCE-CONTROL-PLANE");
assert.equal(registry.assetIntelligence.currentCapabilities.length, 14);
assert.equal(registry.assetIntelligence.externalCandidates.find((tool) => tool.name === "jscpd")?.status, "READ_ONLY_READY");
assert.equal(registry.assetIntelligence.externalCandidates.filter((tool) => tool.name !== "jscpd").every((tool) => tool.status === "NOT_INSTALLED_REVIEW_REQUIRED"), true);

const review = createAssetIntelligenceRequest({ scope: "MIXED", intent: "CLASSIFY", requestedBy: "test", assetPaths: ["canonical/data/suppliers.json"] });
assert.equal(review.status, "READ_ONLY_REVIEW_READY");
const treatment = createAssetIntelligenceRequest({ scope: "CODE", intent: "TREATMENT_PRECHECK", requestedBy: "test", assetPaths: ["legacy/tools/example.py"] });
assert.equal(treatment.status, "APPROVAL_REQUIRED");
const incomplete = createAssetIntelligenceRequest({ scope: "DATA", intent: "COMPARE", requestedBy: "", assetPaths: [] });
assert.equal(incomplete.status, "BLOCKED_INCOMPLETE_REQUEST");

const hardening = createMaintenancePlan({ capabilityId: "SUPPLIER_MASTER", intent: "HARDEN", requestedBy: "test", evidenceIds: ["DD-006"], currentComponentPaths: ["lib/supplier-master-policy.ts"] });
assert.equal(hardening.status, "APPROVAL_REQUIRED");
assert.equal(hardening.treatment, "HARDEN");
const unsafeMerge = createMaintenancePlan({ capabilityId: "COMMAND_ALIASES", intent: "CONSOLIDATE", requestedBy: "test", evidenceIds: ["E3-ALIAS-PROOF"], currentComponentPaths: ["package.json"] });
assert.equal(unsafeMerge.status, "TRACE_REQUIRED");
const extract = createMaintenancePlan({ capabilityId: "ANALYSIS", intent: "EXTRACT", requestedBy: "test", evidenceIds: ["E3-LEGACY-VALUE"], currentComponentPaths: ["lib/intelligence/tool-registry.ts"], legacyCandidatePaths: ["legacy/tools/analyze.py"] });
assert.equal(extract.treatment, "EXTRACT");
const cycle = createE5MaintenanceCycle({ capabilityId: "SUPPLIER_MASTER", intent: "HARDEN", requestedBy: "test", evidenceIds: ["DD-006"], currentComponentPaths: ["lib/supplier-master-policy.ts"], observedIssue: "Supplier ownership needs an explicit SOR contract." });
assert.equal(cycle.status, "REVIEW_READY");
assert.equal(cycle.plan.treatment, "HARDEN");
const incompleteCycle = createE5MaintenanceCycle({ capabilityId: "SUPPLIER_MASTER", intent: "HARDEN", requestedBy: "test", evidenceIds: ["DD-006"], currentComponentPaths: ["lib/supplier-master-policy.ts"], observedIssue: "" });
assert.equal(incompleteCycle.status, "BLOCKED_INCOMPLETE_OBSERVATION");
const approvalPackage = createE5TreatmentApprovalPackage({ action: "QUARANTINE", requestedBy: "test", owner: "E4_GOVERNANCE", systemOfRecord: "E3_E4_LEDGER", evidenceIds: ["E3-QUARANTINE-PROOF"], assets: [{ path: "legacy/unsafe.py", sha256: "a".repeat(64) }], recoveryPath: "archive/quarantine/manifest.json" });
assert.equal(approvalPackage.status, "PENDING_HUMAN_APPROVAL");
const unsafeRetirement = createE5TreatmentApprovalPackage({ action: "RETIREMENT", requestedBy: "test", owner: "E4_GOVERNANCE", systemOfRecord: "E3_E4_LEDGER", evidenceIds: ["E3-RETIREMENT-PROOF"], assets: [{ path: "legacy/old.py", sha256: "b".repeat(64) }], canonicalReplacement: "current/replacement.ts", recoveryPath: "archive/recovery/manifest.json" });
assert.equal(unsafeRetirement.status, "TRACE_REQUIRED");
const unified = createE5UnifiedMaintenanceCycle({ observation: { capabilityId: "SUPPLIER_MASTER", intent: "HARDEN", requestedBy: "test", evidenceIds: ["DD-006"], currentComponentPaths: ["lib/supplier-master-policy.ts"], observedIssue: "Supplier authority needs hardening." }, treatment: approvalPackage.status === "PENDING_HUMAN_APPROVAL" ? { action: "QUARANTINE", requestedBy: "test", owner: "E4_GOVERNANCE", systemOfRecord: "E3_E4_LEDGER", evidenceIds: ["E3-QUARANTINE-PROOF"], assets: [{ path: "legacy/unsafe.py", sha256: "a".repeat(64) }], recoveryPath: "archive/quarantine/manifest.json" } : undefined });
assert.equal(unified.status, "PENDING_HUMAN_APPROVAL");
const duplicate = createE5ConflictReview({ kind: "EXACT_DUPLICATE", subjectId: "duplicate:legacy-tool", requestedBy: "test", evidenceIds: ["E3-DUPLICATE-PROOF"], affectedPaths: ["legacy/a.ts", "current/a.ts"], canonicalReplacement: "current/a.ts", testsPassed: true });
assert.equal(duplicate.status, "APPROVAL_REQUIRED");
const evidenceConflict = createE5ConflictReview({ kind: "EVIDENCE_CONFLICT", subjectId: "claim:honey:no", requestedBy: "test", evidenceIds: ["E-001", "E-002"], affectedPaths: ["canonical/evidence/a.json", "canonical/evidence/b.json"], systemOfRecord: "OFFICIAL_EVIDENCE_REGISTRY" });
assert.equal(evidenceConflict.status, "REQUIRES_HUMAN_REVIEW");
const unprovenDuplicate = createE5ConflictReview({ kind: "NEAR_DUPLICATE", subjectId: "duplicate:near", requestedBy: "test", evidenceIds: ["E3-TRACE"], affectedPaths: ["a.ts", "b.ts"] });
assert.equal(unprovenDuplicate.status, "TRACE_REQUIRED");
const brainAssurance = createE6AssuranceReview({ requestedBy: "test", capabilityId: "BRAIN_REFERENCE", currentComponentPaths: ["lib/intelligence/tool-registry.ts"], evidence: [{ kind: "BRAIN_STATIC_REVIEW", evidenceId: "E5-BRAIN-STATIC-REVIEW", status: "REVIEW", summary: "Historical brain must remain unexecuted." }] });
assert.equal(brainAssurance.status, "EXTRACT_REVIEW_REQUIRED");
const cleanAssurance = createE6AssuranceReview({ requestedBy: "test", capabilityId: "CODE_QUALITY", currentComponentPaths: ["lib/http-input.ts"], evidence: [{ kind: "CODE_DUPLICATION", evidenceId: "E5-JSCPD", status: "PASS", summary: "No duplicate action is proposed." }] });
assert.equal(cleanAssurance.status, "ASSURANCE_RECORDED");

console.log("MasterMind tool registry: PASS");
