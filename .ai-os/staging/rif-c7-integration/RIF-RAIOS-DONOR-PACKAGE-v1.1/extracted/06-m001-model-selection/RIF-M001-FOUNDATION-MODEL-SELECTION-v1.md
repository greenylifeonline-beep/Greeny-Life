# RIF M001 Foundation Model Selection v1

## Purpose
Specify and harness model selection for RIF bootstrap evaluation.

## Historical Design (v1.0)
- Single "best model" selection approach (REJECTED in v1.1)
- Basic disqualifier list
- No multi-role profiles
- No Pareto frontier analysis
- Output not machine-readable for future self-review

## Historical Limitations
- Universal best model fallacy
- Insufficient disqualifiers
- No role-based selection
- No reproducibility for future RIF re-evaluation
- Could trigger downloads (FORBIDDEN in v1.1)

## v1.1 Adaptation Notes
- Remains SPEC/HARNESS only — not downloader, not deployment engine, not trainer
- Multi-role profiles: FAST_ROUTER, STRUCTURED_JUDGE, DEEP_REASONER, CODING_AGENT, SEMANTIC_NORMALIZER, LOW_RESOURCE_CPU, LOW_VRAM_GPU, HIGH_ACCURACY_GPU, OFFLINE_RESILIENCE, DISTILLATION_TEACHER_CANDIDATE
- Selection via: hard gates, minimum thresholds, Pareto frontier, scenario ranking
- Output machine-readable for Full RIF re-evaluation
- Hard disqualifiers expanded per D-E
