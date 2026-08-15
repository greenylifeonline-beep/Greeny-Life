import fs from "node:fs";
import path from "node:path";

export type ToolDisposition = "READ_ONLY_READY" | "ADAPTER_REQUIRED" | "BLOCKED_DIRECT_EXECUTION";

export type AssetReviewScope = "CODE" | "DATA" | "DOCUMENT" | "ARCHIVE" | "MIXED";
export type AssetReviewIntent = "CLASSIFY" | "COMPARE" | "CONSOLIDATE_PROOF" | "TREATMENT_PRECHECK";

export interface AssetIntelligenceRequest {
  scope: AssetReviewScope;
  intent: AssetReviewIntent;
  requestedBy: string;
  assetPaths: string[];
}

interface LegacyCapability {
  name: string;
  type: "EXECUTION" | "BUILD" | "ANALYSIS" | "GENERATION" | "INTEGRATION" | "VALIDATION";
  source_line: number;
  confidence: string;
  legacy_origin: string;
}

const blocked = new Set([
  "run_consolidation", "run_deep_clean", "run_unified_cleanup", "run_continuous_evolution_cycle",
  "execute_full_pipeline", "run_scheduler_mode", "run_periodic_monitoring", "run_daily_audit",
]);
const adapterRequired = new Set([
  "build_supplier_master", "build_certificate_master", "build_els", "build_customer_domain",
  "build_analytics_layer", "build_logistics_system", "build_finance_system", "build_inventory_system",
  "build_crm_system", "build_packaging_visual_engine", "generate_dynamic_packaging",
  "generate_gels_labels_with_visuals", "integrate_business_assets", "run_asset_classifier",
  "run_canonical_validation", "run_master_data_audit", "run_deep_packaging_audit",
  "run_integrity_analysis", "run_arch_guard", "run_govern_kit", "run_ouro_loop",
  "run_sonarqube_scan", "run_security_scan", "run_performance_test", "run_documentation_agent",
]);

function readCapabilities(): LegacyCapability[] {
  const file = path.join(process.cwd(), "greenlines_brain", "dna", "extracted_knowledge.json");
  const source = JSON.parse(fs.readFileSync(file, "utf8")) as { capabilities?: LegacyCapability[] };
  return source.capabilities ?? [];
}

function disposition(capability: LegacyCapability): ToolDisposition {
  if (blocked.has(capability.name)) return "BLOCKED_DIRECT_EXECUTION";
  if (capability.type === "ANALYSIS" || capability.type === "VALIDATION") return "READ_ONLY_READY";
  if (adapterRequired.has(capability.name)) return "ADAPTER_REQUIRED";
  return "ADAPTER_REQUIRED";
}

function purpose(name: string) {
  const names: Record<string, string> = {
    analyze_visual_brand: "Analyze legacy brand and visual-identity references.",
    analyze_packaging_policies: "Analyze packaging rules and policy references.",
    analyze_ui_structure: "Analyze application structure without changing it.",
    analyze_inventory: "Analyze inventory sources without creating movements.",
    analyze_duplication_reason: "Analyze the cause and evidence of duplicate assets.",
    validate_global_specs: "Validate HS-code, EAN, and certificate reference fields.",
  };
  return names[name] ?? "Historical capability retained for reviewed integration.";
}

/**
 * This is deliberately a request/plan boundary, not a filesystem executor.
 * Any caller in the Current system can ask E4 for a review, but an action
 * still needs the evidence, recovery and human-approval gates recorded by E4.
 */
export function createAssetIntelligenceRequest(request: AssetIntelligenceRequest) {
  const paths = [...new Set(request.assetPaths.map((item) => item.trim()).filter(Boolean))];
  const valid = Boolean(request.requestedBy.trim()) && paths.length > 0;
  if (!valid) {
    return {
      status: "BLOCKED_INCOMPLETE_REQUEST" as const,
      reason: "A requester identity and at least one explicit asset path are required.",
      allowedActions: ["Provide the missing reviewed request fields."],
    };
  }

  const destructive = request.intent === "TREATMENT_PRECHECK";
  return {
    status: destructive ? "APPROVAL_REQUIRED" as const : "READ_ONLY_REVIEW_READY" as const,
    request: { ...request, assetPaths: paths },
    routedTo: "E4 Asset Intelligence Control Plane",
    stages: ["classify", "lineage", "current comparison", "duplicate/value proof", "decision"],
    allowedActions: destructive
      ? ["Prepare an evidence-only treatment manifest; do not move, archive, retire, or delete."]
      : ["Produce an evidence-backed read-only review."],
    prohibitions: ["NO_RAW_LEGACY_EXECUTION", "NO_AUTOMATIC_MERGE", "NO_AUTOMATIC_MOVE", "NO_AUTOMATIC_ARCHIVE", "NO_AUTOMATIC_DELETE"],
  };
}


export type MaintenanceIntent = "REPAIR" | "HARDEN" | "CONSOLIDATE" | "EXTRACT" | "ARCHIVE_PRECHECK";
export type MaintenanceTreatment = "EXTEND" | "HARDEN" | "CONSOLIDATE" | "EXTRACT" | "ARCHIVE_PRECHECK" | "TRACE_REQUIRED";

export interface MaintenancePlanRequest {
  capabilityId: string;
  intent: MaintenanceIntent;
  requestedBy: string;
  evidenceIds: string[];
  currentComponentPaths: string[];
  legacyCandidatePaths?: string[];
  canonicalReplacement?: string;
  recoveryPath?: string;
}

const distinctPaths = (paths: string[]) => [...new Set(paths.map((item) => item.trim()).filter(Boolean))];

/**
 * E4's repair and consolidation paths are deliberately planners, not mutation
 * engines. They force a request to name the existing Current component, the
 * evidence, and (where relevant) the canonical replacement and recovery path.
 */
export function createMaintenancePlan(request: MaintenancePlanRequest) {
  const current = distinctPaths(request.currentComponentPaths);
  const legacy = distinctPaths(request.legacyCandidatePaths ?? []);
  const evidence = distinctPaths(request.evidenceIds);
  const base = {
    request: { ...request, capabilityId: request.capabilityId.trim(), requestedBy: request.requestedBy.trim(), evidenceIds: evidence, currentComponentPaths: current, legacyCandidatePaths: legacy },
    routedTo: "E4 Asset Intelligence Control Plane",
    stages: ["trace existing component", "prove dependency/caller impact", "define tests", "prepare rollback/recovery", "human approval", "apply separately", "verify"],
    prohibitions: ["NO_AUTOMATIC_CODE_MUTATION", "NO_AUTOMATIC_MERGE", "NO_RAW_LEGACY_EXECUTION", "NO_AUTOMATIC_ARCHIVE", "NO_AUTOMATIC_DELETE"],
  };
  if (!base.request.capabilityId || !base.request.requestedBy || !evidence.length) {
    return { ...base, status: "BLOCKED_INCOMPLETE_REQUEST" as const, treatment: "TRACE_REQUIRED" as const, reason: "Capability, requester, and at least one evidence ID are required." };
  }
  if ((request.intent === "REPAIR" || request.intent === "HARDEN") && !current.length) {
    return { ...base, status: "TRACE_REQUIRED" as const, treatment: "TRACE_REQUIRED" as const, reason: "No existing Current component was named; E4 cannot authorize a new component." };
  }
  if (request.intent === "CONSOLIDATE" && (current.length < 2 || !request.canonicalReplacement?.trim() || !current.includes(request.canonicalReplacement.trim()))) {
    return { ...base, status: "TRACE_REQUIRED" as const, treatment: "TRACE_REQUIRED" as const, reason: "Consolidation requires at least two Current components and a named canonical replacement among them." };
  }
  if (request.intent === "EXTRACT" && (!legacy.length || !current.length)) {
    return { ...base, status: "TRACE_REQUIRED" as const, treatment: "TRACE_REQUIRED" as const, reason: "Extraction requires a proved Legacy candidate and an existing Current integration boundary." };
  }
  if (request.intent === "ARCHIVE_PRECHECK" && (!request.canonicalReplacement?.trim() || !request.recoveryPath?.trim())) {
    return { ...base, status: "TRACE_REQUIRED" as const, treatment: "TRACE_REQUIRED" as const, reason: "Archive preparation requires a canonical replacement and a recovery path." };
  }
  const treatment: MaintenanceTreatment = request.intent === "REPAIR" ? "EXTEND" : request.intent === "HARDEN" ? "HARDEN" : request.intent;
  return {
    ...base,
    status: "APPROVAL_REQUIRED" as const,
    treatment,
    canonicalReplacement: request.canonicalReplacement?.trim() || null,
    recoveryPath: request.recoveryPath?.trim() || null,
    requiredProof: ["existing-component trace", "relevant tests", "type-check", "runtime/build verification when applicable", "human approval before mutation"],
    executionRule: "This plan may guide a separately approved minimal change only. E4 does not perform the change, merge, archive, or deletion.",
  };
}

export interface E5MaintenanceCycleRequest extends MaintenancePlanRequest {
  observedIssue: string;
}

/**
 * E5 is a continuous-assurance control loop, not autonomous self-repair.
 * It turns a named observation into an evidence-backed plan and records the
 * proof still required before any separately approved action can happen.
 */
export function createE5MaintenanceCycle(request: E5MaintenanceCycleRequest) {
  const observedIssue = request.observedIssue.trim();
  const plan = createMaintenancePlan(request);
  const common = {
    cycle: "E5_CONTINUOUS_ASSURANCE" as const,
    observedIssue,
    detection: "EXPLICIT_OBSERVATION_RECORDED" as const,
    diagnosis: {
      capabilityId: request.capabilityId.trim(),
      currentComponentPaths: plan.request.currentComponentPaths,
      legacyCandidatePaths: plan.request.legacyCandidatePaths,
      evidenceIds: plan.request.evidenceIds,
    },
    plan,
    verification: ["relevant focused tests", "type-check", "runtime/build proof when applicable", "evidence-ledger closure"],
    executionRule: "E5 detects, diagnoses, and plans only. It cannot change code, invoke Legacy, merge, archive, quarantine, retire, or delete assets.",
  };
  if (!observedIssue) {
    return { ...common, status: "BLOCKED_INCOMPLETE_OBSERVATION" as const, nextStep: "Record a concrete observed issue before requesting analysis." };
  }
  if (plan.status !== "APPROVAL_REQUIRED") {
    return { ...common, status: plan.status, nextStep: "Resolve the stated evidence or trace gap; do not create a replacement component." };
  }
  return { ...common, status: "REVIEW_READY" as const, nextStep: "Obtain human approval, apply the smallest separately approved change, then complete the listed verification." };
}

export type TreatmentAction = "CONSOLIDATE" | "ARCHIVE" | "QUARANTINE" | "RETIREMENT";

export interface TreatmentAssetEvidence {
  path: string;
  sha256: string;
}

export interface E5TreatmentApprovalRequest {
  action: TreatmentAction;
  requestedBy: string;
  owner: string;
  systemOfRecord: string;
  evidenceIds: string[];
  assets: TreatmentAssetEvidence[];
  canonicalReplacement?: string;
  recoveryPath: string;
  noActiveDependency?: boolean;
  noUniqueBusinessValue?: boolean;
  replacementVerified?: boolean;
  relevantTestsPassed?: boolean;
}

const sha256 = /^[a-f0-9]{64}$/i;

/**
 * This is the Smart Cleaner governance boundary within E5. It produces an
 * approval package, never a filesystem command. A caller must provide the
 * checksum captured by E3/E4 evidence rather than letting E5 mutate assets.
 */
export function createE5TreatmentApprovalPackage(request: E5TreatmentApprovalRequest) {
  const evidenceIds = distinctPaths(request.evidenceIds);
  const assets = request.assets.map((asset) => ({ path: asset.path.trim(), sha256: asset.sha256.trim().toLowerCase() })).filter((asset) => asset.path);
  const common = {
    action: request.action,
    requestedBy: request.requestedBy.trim(),
    owner: request.owner.trim(),
    systemOfRecord: request.systemOfRecord.trim(),
    evidenceIds,
    assets,
    canonicalReplacement: request.canonicalReplacement?.trim() || null,
    recoveryPath: request.recoveryPath.trim(),
    safeguards: ["checksum verified before any separate action", "manifest retained", "original remains recoverable", "distinct human approval required", "post-action verification required"],
    executionRule: "This is an approval package only. E5 does not move, merge, archive, quarantine, retire, or delete any asset.",
  };
  if (!common.requestedBy || !common.owner || !common.systemOfRecord || !evidenceIds.length || !assets.length || !common.recoveryPath) {
    return { ...common, status: "TRACE_REQUIRED" as const, reason: "Requester, owner, system of record, evidence, asset manifest, and recovery path are required." };
  }
  if (assets.some((asset) => !sha256.test(asset.sha256))) {
    return { ...common, status: "TRACE_REQUIRED" as const, reason: "Every asset requires a valid SHA-256 from a prior evidence record." };
  }
  if ((request.action === "CONSOLIDATE" || request.action === "ARCHIVE" || request.action === "RETIREMENT") && !common.canonicalReplacement) {
    return { ...common, status: "TRACE_REQUIRED" as const, reason: "A canonical replacement is required before consolidation, archive, or retirement." };
  }
  if (request.action === "CONSOLIDATE" && !request.relevantTestsPassed) {
    return { ...common, status: "TRACE_REQUIRED" as const, reason: "Consolidation requires passing equivalence and caller regression tests." };
  }
  if (request.action === "RETIREMENT" && (!request.noActiveDependency || !request.noUniqueBusinessValue || !request.replacementVerified || !request.relevantTestsPassed)) {
    return { ...common, status: "TRACE_REQUIRED" as const, reason: "Retirement requires no active dependency, no unique value, verified replacement, and passing tests." };
  }
  return {
    ...common,
    status: "PENDING_HUMAN_APPROVAL" as const,
    approvalRule: "A distinct authorized human approves this exact manifest. Approval expires when any asset checksum, replacement, or recovery path changes.",
    nextStep: "After approval, perform the separately authorized minimal action and record verification; no delete is implied by this package.",
  };
}

export function createE5UnifiedMaintenanceCycle(input: { observation: E5MaintenanceCycleRequest; treatment?: E5TreatmentApprovalRequest }) {
  const cycle = createE5MaintenanceCycle(input.observation);
  if (cycle.status !== "REVIEW_READY") return { status: cycle.status, cycle, treatment: null, nextStep: cycle.nextStep };
  if (!input.treatment) return { status: "REPAIR_PLAN_READY" as const, cycle, treatment: null, nextStep: "Apply the separately approved repair plan and complete verification before requesting asset treatment." };
  const treatment = createE5TreatmentApprovalPackage(input.treatment);
  return {
    status: treatment.status === "PENDING_HUMAN_APPROVAL" ? "PENDING_HUMAN_APPROVAL" as const : treatment.status,
    cycle,
    treatment,
    nextStep: treatment.status === "PENDING_HUMAN_APPROVAL" ? "Present the exact treatment manifest for approval; do not execute automatically." : treatment.reason,
  };
}

export type ConflictKind = "EXACT_DUPLICATE" | "NEAR_DUPLICATE" | "DATA_CONFLICT" | "EVIDENCE_CONFLICT" | "AUTHORITY_CONFLICT" | "VERSION_CONFLICT" | "DEPENDENCY_CONFLICT";

export interface E5ConflictReviewRequest {
  kind: ConflictKind;
  subjectId: string;
  requestedBy: string;
  evidenceIds: string[];
  affectedPaths: string[];
  systemOfRecord?: string;
  canonicalReplacement?: string;
  testsPassed?: boolean;
}

/**
 * A compact, evidence-only classifier for duplicate and conflict findings.
 * It never scans broadly, changes files, resolves business facts, or selects
 * a winner silently. Each caller supplies the already-observed subject and
 * evidence, keeping E5 useful without creating report or scanner sprawl.
 */
export function createE5ConflictReview(request: E5ConflictReviewRequest) {
  const evidenceIds = distinctPaths(request.evidenceIds);
  const affectedPaths = distinctPaths(request.affectedPaths);
  const common = {
    kind: request.kind,
    subjectId: request.subjectId.trim(),
    requestedBy: request.requestedBy.trim(),
    evidenceIds,
    affectedPaths,
    systemOfRecord: request.systemOfRecord?.trim() || null,
    canonicalReplacement: request.canonicalReplacement?.trim() || null,
    prohibitions: ["NO_SILENT_WINNER_SELECTION", "NO_AUTOMATIC_MERGE", "NO_AUTOMATIC_ARCHIVE", "NO_AUTOMATIC_DELETE", "NO_RAW_LEGACY_EXECUTION"],
  };
  if (!common.subjectId || !common.requestedBy || !evidenceIds.length || !affectedPaths.length) {
    return { ...common, status: "BLOCKED_INCOMPLETE_REQUEST" as const, decision: "TRACE_REQUIRED" as const, reason: "Subject, requester, evidence, and explicit affected paths are required." };
  }
  if (request.kind === "EXACT_DUPLICATE" || request.kind === "NEAR_DUPLICATE") {
    if (!common.canonicalReplacement || !request.testsPassed) {
      return { ...common, status: "TRACE_REQUIRED" as const, decision: "CONSOLIDATE_PRECHECK" as const, reason: "A duplicate requires a named canonical replacement and passing caller/equivalence tests before consolidation can be proposed." };
    }
    return { ...common, status: "APPROVAL_REQUIRED" as const, decision: "CONSOLIDATE_PRECHECK" as const, reason: "Duplicate proof is complete enough to prepare a separate checksum-backed treatment approval package." };
  }
  if (request.kind === "DEPENDENCY_CONFLICT") {
    return { ...common, status: "TRACE_REQUIRED" as const, decision: "TRACE_REQUIRED" as const, reason: "Dependency conflicts require caller and dependency proof before a treatment can be proposed." };
  }
  if (!common.systemOfRecord) {
    return { ...common, status: "TRACE_REQUIRED" as const, decision: "TRACE_REQUIRED" as const, reason: "A data, evidence, authority, or version conflict requires a proven System of Record before it can be resolved." };
  }
  return { ...common, status: "REQUIRES_HUMAN_REVIEW" as const, decision: "HUMAN_RESOLUTION_REQUIRED" as const, reason: "E5 preserves the conflict and routes it to the named authority; it never silently chooses a business fact, evidence version, or owner." };
}

export type E6EvidenceKind = "BRAIN_STATIC_REVIEW" | "CODE_DUPLICATION" | "CONFLICT_REVIEW" | "DATA_QUALITY_REVIEW";

export interface E6EvidenceItem {
  kind: E6EvidenceKind;
  evidenceId: string;
  status: "PASS" | "FINDING" | "REVIEW" | "BLOCKED";
  summary: string;
}

export interface E6AssuranceRequest {
  requestedBy: string;
  capabilityId: string;
  evidence: E6EvidenceItem[];
  currentComponentPaths: string[];
}

/** Joins evidence already produced by E5 and E3/E4; it never scans, imports brain.py, runs Legacy, or executes treatment. */
export function createE6AssuranceReview(request: E6AssuranceRequest) {
  const evidence = request.evidence.map((item) => ({ kind: item.kind, evidenceId: item.evidenceId.trim(), status: item.status, summary: item.summary.trim() })).filter((item) => item.evidenceId && item.summary);
  const currentComponentPaths = distinctPaths(request.currentComponentPaths);
  const common = {
    controlPlane: "E6_UNIFIED_ASSURANCE" as const,
    requestedBy: request.requestedBy.trim(), capabilityId: request.capabilityId.trim(), evidence, currentComponentPaths,
    prohibitions: ["NO_BRAIN_IMPORT", "NO_LEGACY_EXECUTION", "NO_AUTOMATIC_MERGE", "NO_AUTOMATIC_ARCHIVE", "NO_AUTOMATIC_RETIREMENT", "NO_AUTOMATIC_DELETE"],
    requiredBeforeChange: ["existing Current component trace", "focused tests", "type-check", "human approval", "post-change verification"],
  };
  if (!common.requestedBy || !common.capabilityId || !evidence.length || !currentComponentPaths.length) return { ...common, status: "BLOCKED_INCOMPLETE_REQUEST" as const, decision: "TRACE_REQUIRED" as const };
  if (evidence.some((item) => item.status === "BLOCKED")) return { ...common, status: "BLOCKED" as const, decision: "NO_TREATMENT" as const, reason: "A supplied evidence record is blocked; resolve its stated safety boundary first." };
  if (evidence.some((item) => item.kind === "BRAIN_STATIC_REVIEW")) return { ...common, status: "EXTRACT_REVIEW_REQUIRED" as const, decision: "TRACE_EXISTING_THEN_EXTRACT" as const, reason: "brain.py is reference evidence only. Trace a named pure function against a Current component; do not import or execute it." };
  if (evidence.some((item) => item.status === "FINDING" || item.status === "REVIEW")) return { ...common, status: "REVIEW_READY" as const, decision: "HUMAN_REVIEW_REQUIRED" as const, reason: "E6 preserved the finding for an evidence-backed E5 maintenance plan; it has not selected or executed a treatment." };
  return { ...common, status: "ASSURANCE_RECORDED" as const, decision: "NO_CHANGE_PROPOSED" as const, reason: "All supplied evidence passed; E6 records assurance but does not infer a need to change the system." };
}
function assetIntelligenceRegistry() {
  return {
    id: "E4-ASSET-INTELLIGENCE-CONTROL-PLANE",
    owner: "E4 governance with human approval for treatment",
    systemOfRecord: "E3/E4 evidence packages and the Current canonical baseline",
    purpose: "Classify, compare and prepare evidence-backed consolidation or treatment decisions for code, data, documents and archive references.",
    invocation: "Import createAssetIntelligenceRequest() from this registry. Every request names explicit paths, scope, intent and requester.",
    currentCapabilities: [
      { id: "E4-CLASSIFICATION-LINEAGE", status: "READ_ONLY_READY", purpose: "Classify assets and record lineage." },
      { id: "E4-CURRENT-COMPARISON", status: "READ_ONLY_READY", purpose: "Compare a Legacy/reference candidate with the Current baseline." },
      { id: "E4-DUPLICATE-CONSOLIDATION-PROOF", status: "READ_ONLY_READY", purpose: "Prove canonical replacement, callers, tests and recovery before consolidation." },
      { id: "E4-TREATMENT-PRECHECK", status: "APPROVAL_REQUIRED", purpose: "Prepare a checksum, owner/SOR, dependency and recovery manifest; it does not perform treatment." },
      { id: "E4-RETENTION-RECOVERY", status: "READ_ONLY_READY", purpose: "Apply retention class and recovery requirements to reports and preserved assets." },
      { id: "E4-EXISTING-ASSET-ROUTER", status: "READ_ONLY_READY", purpose: "Require a traced Current component before a repair or extension plan can proceed." },
      { id: "E4-REPAIR-CONSOLIDATION-PLANNER", status: "APPROVAL_REQUIRED", purpose: "Prepare a minimal repair, hardening, extraction, or consolidation plan with tests and recovery; it never performs the action." },
      { id: "E5-CONTINUOUS-ASSURANCE-CYCLE", status: "READ_ONLY_READY", purpose: "Turn an explicit observed issue into diagnosis, treatment plan, verification requirements and approval gates without autonomous execution." },
      { id: "E5-TREATMENT-APPROVAL-PACKAGE", status: "APPROVAL_REQUIRED", purpose: "Prepare a checksum-backed approval manifest for consolidation, archive, quarantine, or retirement; it never executes treatment." },
      { id: "E5-UNIFIED-MAINTENANCE-CYCLE", status: "READ_ONLY_READY", purpose: "Join diagnosis, repair planning, verification and optional treatment approval into one evidence-led lifecycle." },
      { id: "E5-DUPLICATE-CONFLICT-INTELLIGENCE", status: "READ_ONLY_READY", purpose: "Classify an explicit duplicate or conflict finding and route it to consolidation proof or authority review without silent resolution." },
      { id: "E5-JSCPD-CODE-DUPLICATION", status: "READ_ONLY_READY", purpose: "Run a bounded copy/paste review of Current source and write one replaceable machine report; findings remain evidence, never merge instructions." },
      { id: "E5-TASK-AND-INTEREST-CONFLICT-GUARDS", status: "READ_ONLY_READY", purpose: "Detect task collisions and self-dependency; require a distinct approver for any later maintenance treatment." },
      { id: "E6-UNIFIED-ASSURANCE", status: "READ_ONLY_READY", purpose: "Join existing static brain, duplication, conflict and data-quality evidence into one approval-bound review; it does not scan or execute treatment." },
    ],
    externalCandidates: [
      { name: "jscpd", purpose: "Detect copied code blocks across Current TypeScript/JavaScript source.", status: "READ_ONLY_READY", replacement: "E4 exact-hash and consolidation proof", adoptionRule: "Run only through e5:duplicate-review; every finding needs E5 caller, canonical-replacement, test and approval proof before treatment." },
      { name: "Semgrep", purpose: "Pattern-based static analysis for code and guardrails.", status: "NOT_INSTALLED_REVIEW_REQUIRED", replacement: "Current type-check, tests and E4 static evidence", adoptionRule: "Adopt rules only for a documented safety gap; results never authorize treatment." },
      { name: "Syft", purpose: "Produce an SBOM from a filesystem or image.", status: "NOT_INSTALLED_REVIEW_REQUIRED", replacement: "Package lockfiles and E4 inventory", adoptionRule: "Adopt only when a portable dependency inventory is approved." },
      { name: "Trivy", purpose: "Scan a filesystem for vulnerabilities and exposed secrets.", status: "NOT_INSTALLED_REVIEW_REQUIRED", replacement: "Existing security checks and protected-secret policy", adoptionRule: "Run only in an approved security workflow; findings require review." },
    ],
    safety: [
      "Tools supply evidence; they never approve their own merge, archive or deletion.",
      "E4 is the treatment-control plane, not a raw mutation engine.",
      "A treatment request can prepare a manifest only; execution requires a separate explicit approval.",
    ],
  };
}

export function toolRegistry() {
  const tools = readCapabilities().map((capability) => ({
    id: `LEGACY-${capability.name.toUpperCase()}`,
    name: capability.name,
    category: capability.type,
    disposition: disposition(capability),
    purpose: purpose(capability.name),
    source: capability.legacy_origin,
    confidence: capability.confidence,
    authority: "MasterMind AI routes tools; local brains may request them; no tool can execute commercial actions.",
    inputs: "Explicit reviewed context only",
    outputs: "Auditable finding, recommendation, or adapter proposal",
    executionRule: disposition(capability) === "READ_ONLY_READY"
      ? "Read-only analysis; result remains subject to MasterMind and user approval."
      : disposition(capability) === "ADAPTER_REQUIRED"
        ? "Cannot run until a tested adapter binds it to current canonical data."
        : "Direct execution is prohibited; retained only as historical capability evidence.",
  }));
  const counts = Object.fromEntries(([
    "READ_ONLY_READY", "ADAPTER_REQUIRED", "BLOCKED_DIRECT_EXECUTION",
  ] as const).map((status) => [status, tools.filter((tool) => tool.disposition === status).length]));
  return {
    system: "MasterMind AI Tool Registry",
    source: "greenlines_brain/dna/extracted_knowledge.json",
    total: tools.length,
    counts,
    rules: [
      "MasterMind AI routes and combines tools; it does not let tools override approval requirements.",
      "Local operating brains may request a tool only inside their company context.",
      "All tools are read-only until an explicit tested adapter and user-approved operational workflow exists.",
    ],
    assetIntelligence: assetIntelligenceRegistry(),
    tools,
  };
}
