# Routing

- Architecture/governance → ChatGPT main brain
- Large repo inventory → Gemini CLI
- Deep bounded implementation → Codex or Claude Code
- Interactive IDE repair → Cursor
- GitHub/PR/CI → GitHub agent
- Low-cost repetitive reasoning → DeepSeek
- Validation → preferably a different agent from the implementer

If an agent stops:
read task → read locks → read latest handoff → snapshot → continue.
