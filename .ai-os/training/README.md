# RAIOS Dataset Factory

## Core principle

Never train directly from raw conversations.

Only validated experience can become training material.

Pipeline:

RAW EXPERIENCE
→ VALIDATION
→ ACCEPTED CASE
→ NORMALIZATION
→ DEDUPLICATION
→ QUALITY SCORE
→ CURATED DATASET
→ TRAIN / VALIDATION / TEST SPLIT
→ BASELINE EVALUATION
→ LoRA / QLoRA
→ POST-TRAIN EVALUATION
→ ACCEPT / REJECT MODEL

## Never include

- API keys
- passwords
- tokens
- private credentials
- unvalidated hallucinations
- destructive commands without context
- rejected implementation presented as correct