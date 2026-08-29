# C5 Conversation Runtime/UI Repair

Task: RAIOS-C5-CONVERSATION-RUNTIME-UI-REPAIR-AND-CANONICAL-CLOSURE-01

Root cause was a request contract mismatch: canonical C5 accepted `text`, while legacy/UI callers may send `message`. The canonical gateway now accepts both names, preserves `language/locale`, returns `response/content/reply`, validates empty input, and maps bounded Ollama timeout to HTTP 504.

Tests passed: 9 repository tests, 6 runtime contract checks, live Arabic direct chat, existing desktop bridge E2E, empty-input 422, timeout 504, and learning-trace append outside Git.

Deployment used the canonical script. A candidate became healthy on stage port 9766 before PID 23244 was replaced by PID 13456 on port 8766. Runtime health reports `CANONICAL_DEPLOYMENT`, model `qwen3:0.6b`, and head `a6765f4dafd52a9ad2f7f546c960c5f8a6395418`.

No second gateway or UI was created. No model was downloaded. No GPU or paid resource was used. C6 Weight-Merge scope was untouched.
