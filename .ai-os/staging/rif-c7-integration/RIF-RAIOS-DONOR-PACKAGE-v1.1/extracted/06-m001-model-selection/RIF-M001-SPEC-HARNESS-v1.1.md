# RIF M001 Foundation Model Selection Spec/Harness v1.1

## Classification
- TYPE: SPEC_HARNESS
- DOWNLOAD_ENGINE: FALSE
- DEPLOYMENT_ENGINE: FALSE
- TRAINER: FALSE
- PAID_API_DEPENDENCY: NONE_REQUIRED

## Design Principle
M001 remains FOUNDATION MODEL SELECTION SPEC/HARNESS only.
- NOT downloader
- NOT deployment engine
- NOT trainer
- No large model download
- No paid API dependency

## Hard Disqualifiers

Candidate MAY be disqualified for role depending on:

1. **license_incompatibility**: License conflicts with deployment requirements
2. **weights_unavailable**: Local ownership required but weights not accessible
3. **unsupported_architecture**: Runtime/architecture mismatch
4. **minimum_context_failure**: Context window below role minimum
5. **schema_adherence_below_minimum**: Cannot produce required output schema
6. **unsafe_tool_behavior**: Tool use patterns violate safety requirements
7. **abstention_below_minimum**: Refuses required operations too frequently
8. **resource_requirement_impossible**: Exceeds available resources
9. **offline_requirement_failure**: Offline required but needs connectivity
10. **privacy_requirement_failure**: Privacy requirements not met

### API-Only Policy
- Do NOT universally reject API-only models
- Reject ONLY if scenario explicitly requires local/open/self-hosted
- Default RAIOS strategy: prefer local/open/free/near-free

## Multi-Role Selection

No universal "best model". Role-based profiles:

### Profiles
1. **FAST_ROUTER**: Low latency, simple routing decisions
2. **STRUCTURED_JUDGE**: Strict schema adherence, structured output
3. **DEEP_REASONER**: Complex reasoning, long context
4. **CODING_AGENT**: Code generation, syntax correctness
5. **SEMANTIC_NORMALIZER**: Text normalization, canonicalization prep
6. **LOW_RESOURCE_CPU**: Runs on minimal CPU resources
7. **LOW_VRAM_GPU**: Runs on limited GPU memory
8. **HIGH_ACCURACY_GPU**: Maximum accuracy, high GPU resources
9. **OFFLINE_RESILIENCE**: Full offline capability
10. **DISTILLATION_TEACHER_CANDIDATE**: Suitable for distillation source

### Selection Methodology
- **Hard gates**: Minimum thresholds per role (pass/fail)
- **Minimum thresholds**: Non-negotiable requirements
- **Pareto frontier**: Multi-objective optimization
- **Scenario ranking**: Context-specific ranking

### Anti-Pattern
```
# FORBIDDEN: Single weighted score
score = w1*accuracy + w2*speed + w3*cost
```

## Future Self-Review

Output MUST be machine-readable so Full RIF can later:
- re-run
- challenge
- re-score
- invalidate
- replace

the bootstrap model selection.

### Required Output Schema
```json
{
  "selection_id": "uuid",
  "timestamp": "ISO8601",
  "scenario": "scenario_description",
  "role": "role_profile",
  "candidates": [
    {
      "model_id": "string",
      "disqualifiers": ["list"],
      "hard_gates_passed": boolean,
      "pareto_rank": integer,
      "scenario_rank": integer,
      "selection_confidence": "decimal",
      "selection_reason": "string",
      "reproducibility_hash": "sha256"
    }
  ],
  "selected_model": "model_id",
  "selection_rationale": "string",
  "invalidation_conditions": ["list"]
}
```

### Mandatory Flow
```
LLM Bootstrap
  → Full RIF
  → RIF re-evaluates LLM
```

M001 output must enable this re-evaluation.
