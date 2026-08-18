# RAIOS V9 — RECURSIVE COGNITIVE ARCHITECTURE

## Central principle

RAIOS V9 is built recursively.

The initial kernel must be capable of observing the work used to build
later kernels, converting real work into structured Experiences, and
reusing validated knowledge to reduce future cognitive cost.

## Cognitive modes

### LIVE BRAIN

Foreground cognition.

Responsibilities:

- active user/task interaction
- bounded reasoning
- planning
- tool orchestration
- decision generation
- low-latency execution

### EVOLUTION BRAIN

Background cognition.

Responsibilities:

- repository census
- search
- evidence mining
- comparison
- contradiction discovery
- failure clustering
- skill candidate generation
- benchmark candidate generation
- model comparison
- architecture analysis

The Evolution Brain MUST NOT silently mutate canonical truth.

### AUTONOMIC CORE

Reflex / health / safety / recovery plane.

Responsibilities:

- runtime health
- resource pressure
- recovery
- checkpoints
- circuit breakers
- graceful degradation
- rollback triggers
- memory admission control

## V9.0-A Cognitive primitives

READ
SEARCH
UNDERSTAND
COMPARE
VERIFY
ACT
OBSERVE
LEARN

Higher-level capabilities must be composed from these primitives where
possible.

## Experience invariant

Every meaningful operation must be representable as:

INTENT
CONTEXT
HYPOTHESIS_OR_PLAN
TOOLS
OBSERVATIONS
FAILURES
CORRECTIONS
RESULT
EVIDENCE
LESSON
REUSABILITY_ASSESSMENT
SKILL_CANDIDATE

Logs alone are insufficient.

## Evidence invariant

Never promote an observation into a stronger fact than the evidence permits.

Examples:

report says ACTIVE
!= implementation exists

implementation exists
!= runtime proven

runtime proven once
!= production reliability

historical truth
!= current truth

model confidence
!= calibrated probability

## Recursive flywheel

BUILD RAIOS
    ->
RAIOS OBSERVES BUILD PROCESS
    ->
EXPERIENCE
    ->
VALIDATION
    ->
REUSABLE PROCEDURE
    ->
SKILL CANDIDATE
    ->
BENCHMARK
    ->
PROMOTION
    ->
RAIOS BUILDS BETTER

No promotion step may be skipped.
