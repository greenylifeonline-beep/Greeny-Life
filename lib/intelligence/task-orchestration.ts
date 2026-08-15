import crypto from "node:crypto";

export type TaskType = "PRODUCT_CONTEXT" | "INVENTORY_REVIEW" | "SUPPLIER_REVIEW" | "SHIPMENT_REVIEW" | "EXPORT_EVIDENCE_REVIEW" | "OUTCOME_CAPTURE" | "SYSTEM_MAINTENANCE_REVIEW";
export type TaskStatus = "RECEIVED" | "VALIDATING" | "BLOCKED" | "REVIEW_REQUIRED" | "COMPLETED" | "FAILED" | "CANCELLED";

export interface TaskInput {
  taskType: TaskType;
  ownerCompany: "GREENY_LIFE_EGYPT" | "GREENS_NATURE_UAE" | "GREEN_LINES_NORWAY_EU" | "MASTERMIND";
  subjectId: string;
  requestedBy: string;
  evidenceIds: string[];
  dependsOn?: string[];
  priority?: "LOW" | "MEDIUM" | "HIGH";
  payload?: Record<string, unknown>;
}

const routing: Record<TaskType, { executor: string; outputContract: string; execution: boolean }> = {
  PRODUCT_CONTEXT: { executor: "CANONICAL_PRODUCT_CONTEXT", outputContract: "Canonical product context or UNKNOWN.", execution: false },
  INVENTORY_REVIEW: { executor: "LEGACY-ANALYZE_INVENTORY", outputContract: "Read-only inventory finding with freshness status.", execution: false },
  SUPPLIER_REVIEW: { executor: "SUPPLIER_QUALITY_REVIEW", outputContract: "Supplier readiness finding with evidence gaps.", execution: false },
  SHIPMENT_REVIEW: { executor: "SHIPMENT_TRACKING", outputContract: "Historical shipment finding; not a release or reroute instruction.", execution: false },
  EXPORT_EVIDENCE_REVIEW: { executor: "EVIDENCE_COMPLIANCE", outputContract: "Evidence status: SUPPORTED, UNKNOWN, or NOT_READY.", execution: false },
  OUTCOME_CAPTURE: { executor: "CONTROLLED_LEARNING", outputContract: "Review-only outcome capture proposal.", execution: false },
  SYSTEM_MAINTENANCE_REVIEW: { executor: "E5_CONTINUOUS_ASSURANCE_CONTROL_PLANE", outputContract: "Evidence-backed maintenance cycle: observation, diagnosis, existing-component plan, verification requirements, blockers and required approvals.", execution: false },
};

export function validateTaskInput(input: TaskInput) {
  const errors: string[] = [];
  if (!input.subjectId.trim()) errors.push("subjectId is required.");
  if (!input.requestedBy.trim()) errors.push("requestedBy is required.");
  if (!input.evidenceIds.length || input.evidenceIds.some((id) => !id.trim())) errors.push("At least one non-empty evidence ID is required.");
  if (input.dependsOn && new Set(input.dependsOn).size !== input.dependsOn.length) errors.push("dependsOn cannot contain duplicate task IDs.");
  return errors;
}

export function createTaskContract(input: TaskInput) {
  const errors = validateTaskInput(input);
  if (errors.length) throw new Error(errors.join(" "));
  const rule = routing[input.taskType];
  const idempotencyKey = crypto.createHash("sha256").update(JSON.stringify({ type: input.taskType, owner: input.ownerCompany, subject: input.subjectId.trim().toUpperCase(), dependencies: [...(input.dependsOn ?? [])].sort(), payload: input.payload ?? {} })).digest("hex");
  return {
    taskType: input.taskType, ownerCompany: input.ownerCompany, subjectId: input.subjectId.trim(), requestedBy: input.requestedBy.trim(), evidenceIds: input.evidenceIds.map((id) => id.trim()),
    dependsOn: input.dependsOn ?? [], priority: input.priority ?? "MEDIUM", payload: input.payload ?? {}, idempotencyKey,
    executor: rule.executor, outputContract: rule.outputContract, status: "REVIEW_REQUIRED" as TaskStatus,
    authority: "Task orchestration creates a review request only. MasterMind and explicit user approval control any later execution.",
    executionRule: rule.execution ? "Execution is separately governed." : "This is read-only analysis or review. It cannot create an order, commitment, inventory movement, shipment, customs filing, payment, or policy change.",
  };
}


export interface TaskConflictRecord {
  id: string;
  taskType: TaskType;
  ownerCompany: TaskInput["ownerCompany"];
  subjectId: string;
  requestedBy: string;
  idempotencyKey: string;
  status: TaskStatus;
  dependsOn: string[];
}

export type TaskConflictFinding = {
  kind: "DUPLICATE_TASK" | "PARALLEL_TASK_REVIEW" | "SELF_DEPENDENCY" | "DEPENDENCY_CYCLE";
  taskIds: string[];
  status: "BLOCKED" | "REVIEW_REQUIRED";
  reason: string;
};

const activeTask = (status: TaskStatus) => ["RECEIVED", "VALIDATING", "REVIEW_REQUIRED"].includes(status);
const normalized = (value: string) => value.trim().toLowerCase();

/** Finds task-level collisions without altering tasks or choosing a winner. */
export function detectTaskConflicts(tasks: TaskConflictRecord[]): TaskConflictFinding[] {
  const findings: TaskConflictFinding[] = [];
  const byIdempotency = new Map<string, TaskConflictRecord[]>();
  const byActiveSubject = new Map<string, TaskConflictRecord[]>();
  const byId = new Map(tasks.map((task) => [task.id, task]));
  for (const task of tasks) {
    const same = byIdempotency.get(task.idempotencyKey) ?? []; same.push(task); byIdempotency.set(task.idempotencyKey, same);
    if (activeTask(task.status)) {
      const key = `${task.taskType}:${task.ownerCompany}:${task.subjectId.trim().toUpperCase()}`;
      const parallel = byActiveSubject.get(key) ?? []; parallel.push(task); byActiveSubject.set(key, parallel);
    }
    if (task.dependsOn.includes(task.id)) findings.push({ kind: "SELF_DEPENDENCY", taskIds: [task.id], status: "BLOCKED", reason: "A task cannot depend on itself." });
  }
  for (const group of byIdempotency.values()) if (group.length > 1) findings.push({ kind: "DUPLICATE_TASK", taskIds: group.map((task) => task.id).sort(), status: "BLOCKED", reason: "Multiple tasks share one idempotency key." });
  for (const group of byActiveSubject.values()) if (group.length > 1) findings.push({ kind: "PARALLEL_TASK_REVIEW", taskIds: group.map((task) => task.id).sort(), status: "REVIEW_REQUIRED", reason: "Multiple active tasks address the same subject and capability; retain one only after owner review." });
  const visiting = new Set<string>(); const visited = new Set<string>();
  const visit = (id: string, trail: string[]): void => {
    if (visiting.has(id)) { findings.push({ kind: "DEPENDENCY_CYCLE", taskIds: [...trail, id], status: "BLOCKED", reason: "A dependency cycle prevents controlled completion." }); return; }
    if (visited.has(id)) return;
    visiting.add(id);
    const task = byId.get(id); for (const dependency of task?.dependsOn ?? []) if (byId.has(dependency)) visit(dependency, [...trail, id]);
    visiting.delete(id); visited.add(id);
  };
  for (const task of tasks) visit(task.id, []);
  return findings;
}

export function assessTaskInterestConflict(input: { requestedBy: string; proposedApprover: string | null | undefined }) {
  const requester = normalized(input.requestedBy);
  const approver = normalized(input.proposedApprover ?? "");
  if (!requester || !approver) return { status: "REVIEW_REQUIRED" as const, reason: "A distinct named approver is required before any maintenance treatment may be approved." };
  if (requester === approver) return { status: "BLOCKED_SELF_APPROVAL" as const, reason: "The requester cannot approve the same maintenance treatment." };
  return { status: "DISTINCT_APPROVER_REQUIRED" as const, reason: "Identity separation is satisfied; evidence and authority approval are still required." };
}
export function validateTaskTransition(input: { current: TaskStatus; target: TaskStatus; dependenciesComplete: boolean; hasValidatedOutput: boolean }) {
  if (["COMPLETED", "FAILED", "CANCELLED"].includes(input.current)) return { allowed: false, reason: "Terminal tasks cannot transition." };
  if (input.target === "COMPLETED" && (!input.dependenciesComplete || !input.hasValidatedOutput)) return { allowed: false, reason: "Completion requires completed dependencies and a validated output contract." };
  if (input.target === "VALIDATING" && input.current !== "RECEIVED" && input.current !== "REVIEW_REQUIRED") return { allowed: false, reason: "Only received or review-required tasks may enter validation." };
  if (input.target === "REVIEW_REQUIRED" || input.target === "BLOCKED" || input.target === "FAILED" || input.target === "CANCELLED" || input.target === "VALIDATING") return { allowed: true, reason: "Controlled non-executing transition." };
  return { allowed: false, reason: "Unsupported task transition." };
}
