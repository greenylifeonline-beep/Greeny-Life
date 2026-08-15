export type OutcomeStatus = "REVIEW_REQUIRED" | "REJECTED";

export interface OutcomeInput {
  decisionId: string;
  contextId: string;
  metric: string;
  expectedValue: number;
  actualValue: number;
  unit: string;
  observedAt: string;
  actor: string;
  evidenceIds: string[];
  notes?: string;
}

export function validateOutcomeInput(input: OutcomeInput) {
  const errors: string[] = [];
  if (!input.decisionId.trim()) errors.push("decisionId is required.");
  if (!input.contextId.trim()) errors.push("contextId is required.");
  if (!input.metric.trim()) errors.push("metric is required.");
  if (!input.unit.trim()) errors.push("unit is required.");
  if (!input.actor.trim()) errors.push("actor is required.");
  if (!Number.isFinite(input.expectedValue) || !Number.isFinite(input.actualValue)) errors.push("expectedValue and actualValue must be finite numbers.");
  if (Number.isNaN(new Date(input.observedAt).valueOf())) errors.push("observedAt must be a valid ISO timestamp.");
  if (!input.evidenceIds.length || input.evidenceIds.some((id) => !id.trim())) errors.push("At least one non-empty evidence ID is required.");
  return errors;
}

export function learningProposal(input: OutcomeInput) {
  const variance = input.actualValue - input.expectedValue;
  const variancePercent = input.expectedValue === 0 ? null : Number(((variance / Math.abs(input.expectedValue)) * 100).toFixed(2));
  const material = variancePercent === null ? variance !== 0 : Math.abs(variancePercent) >= 5;
  return {
    status: "REVIEW_REQUIRED" as OutcomeStatus,
    variance,
    variancePercent,
    material,
    proposal: material
      ? "Investigate the variance and submit a reviewed improvement proposal. No model, policy, master data, price, supplier, or workflow is changed automatically."
      : "Record the outcome for later reviewed evaluation. No automatic change is permitted.",
    promotionRule: "A human reviewer must evaluate evidence, run benchmark/shadow validation, and explicitly approve any promoted change.",
    prohibited: ["automatic model update", "automatic policy update", "automatic master-data update", "automatic commercial execution"],
  };
}
export type LearningGovernanceStatus = "AUTHORIZED" | "DENIED" | "REVIEW_REQUIRED";

// REVIEW_REQUIRED may create a review record; DENIED must never persist learning material.
export function learningGovernanceAllowsPersistence(status: LearningGovernanceStatus) {
  return status !== "DENIED";
}