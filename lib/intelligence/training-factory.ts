export interface OutcomeForTraining {
  id: string;
  decisionId: string;
  contextId: string;
  metric: string;
  expectedValue: number;
  actualValue: number;
  variance: number;
  variancePercent: number | null;
  unit: string;
  evidenceIds: unknown;
}

export interface TrainingCaseInput {
  outcome: OutcomeForTraining;
  expectedDecision: string;
  actualDecision: string;
  rootCause?: string;
  actor: string;
}

export function validateTrainingCaseInput(input: TrainingCaseInput) {
  const errors: string[] = [];
  if (!input.outcome.id) errors.push("A persisted outcome ID is required.");
  if (!input.expectedDecision.trim()) errors.push("expectedDecision is required.");
  if (!input.actualDecision.trim()) errors.push("actualDecision is required.");
  if (!input.actor.trim()) errors.push("actor is required.");
  return errors;
}

export function buildTrainingCase(input: TrainingCaseInput) {
  const errors = validateTrainingCaseInput(input);
  if (errors.length) throw new Error(errors.join(" "));
  const learningSignal = input.outcome.variancePercent === null
    ? input.outcome.variance === 0 ? "NO_VARIANCE" : "ABSOLUTE_VARIANCE"
    : Math.abs(input.outcome.variancePercent) >= 5 ? "MATERIAL_VARIANCE" : "MINOR_VARIANCE";
  return {
    outcomeId: input.outcome.id,
    decisionId: input.outcome.decisionId,
    contextId: input.outcome.contextId,
    metric: input.outcome.metric,
    expectedDecision: input.expectedDecision.trim(),
    actualDecision: input.actualDecision.trim(),
    rootCause: input.rootCause?.trim() || null,
    learningSignal,
    evidenceIds: input.outcome.evidenceIds,
    status: "REVIEW_REQUIRED" as const,
    trainingRule: "This case is evaluation material only. It cannot train, promote, deploy, or modify a model or policy automatically.",
    promotionRule: "A human reviewer must approve benchmark, shadow, canary, and any production promotion separately.",
  };
}