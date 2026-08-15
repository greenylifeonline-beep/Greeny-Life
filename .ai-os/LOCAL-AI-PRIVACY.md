# RAIOS Local AI Privacy Boundary

## Local engine
Agent: deepseek-local
Model: deepseek-r1:1.5b
Runtime: Ollama
Endpoint: http://localhost:11434

## Classification

PUBLIC
May be processed locally or by approved cloud agents.

INTERNAL
Prefer local processing.

CONFIDENTIAL
LOCAL_ONLY unless explicitly approved.

SECRET
LOCAL_ONLY.
Never send to cloud/model APIs without explicit human approval.

## Rules

1. Local inference uses Ollama at localhost.
2. No private project content may be sent to external model APIs by this agent.
3. Cloud fallback is forbidden for CONFIDENTIAL or SECRET data.
4. Local model output is advisory and must pass project validation.
5. No autonomous destructive actions.
6. No secrets in Git.
