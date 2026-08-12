export const minimumBenchmarkCases = 10;

export interface EvaluationInput {
  candidateVersion: string;
  baselineVersion?: string;
  trainingCaseIds: string[];
  metricScores: Record<string, number>;
  actor: string;
  notes?: string;
}

export function validateEvaluationInput(input: EvaluationInput) {
  const errors: string[] = [];
  if (!input.candidateVersion.trim()) errors.push("candidateVersion is required.");
  if (!input.actor.trim()) errors.push("actor is required.");
  if (!input.trainingCaseIds.length || input.trainingCaseIds.some((id) => !id.trim())) errors.push("At least one training case ID is required.");
  if (new Set(input.trainingCaseIds).size !== input.trainingCaseIds.length) errors.push("trainingCaseIds must not contain duplicates.");
  const metrics = Object.entries(input.metricScores);
  if (!metrics.length) errors.push("At least one metric score is required.");
  if (metrics.some(([name, value]) => !name.trim() || !Number.isFinite(value) || value < 0 || value > 100)) errors.push("Metric scores must be finite values from 0 to 100.");
  return errors;
}

export function evaluateCandidate(input: EvaluationInput) {
  const errors = validateEvaluationInput(input);
  if (errors.length) throw new Error(errors.join(" "));
  const scores = Object.values(input.metricScores);
  const score = Number((scores.reduce((sum, value) => sum + value, 0) / scores.length).toFixed(2));
  const benchmarkReady = input.trainingCaseIds.length >= minimumBenchmarkCases;
  return {
    score,
    benchmarkReady,
    status: benchmarkReady ? "REVIEW_REQUIRED" : "INSUFFICIENT_BENCHMARK_CASES",
    decision: benchmarkReady
      ? "Benchmark recorded for human review. Shadow, canary, approval, and deployment remain separate gated steps."
      : `Only ${input.trainingCaseIds.length} case(s) supplied; at least ${minimumBenchmarkCases} are required before a benchmark can be reviewed.`,
    promotionRule: "No evaluation can promote, deploy, replace, or modify a model, prompt, policy, authority rule, or commercial workflow. A human approval is required after benchmark, shadow, and canary evidence.",
    prohibited: ["automatic promotion", "automatic deployment", "automatic rollback", "automatic policy modification", "automatic commercial execution"],
  };
}