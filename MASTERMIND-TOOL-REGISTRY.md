# MasterMind Tool Registry

The registry consolidates all 39 capabilities extracted from the historical Brain. It is exposed at `GET /api/mastermind/tools`.

| Disposition | Meaning |
| --- | --- |
| `READ_ONLY_READY` | Analysis or validation capability that may be rebuilt as a controlled read-only tool. |
| `ADAPTER_REQUIRED` | Useful historical capability, but it can create data or depends on old sources; it needs a tested adapter to current canonical data. |
| `BLOCKED_DIRECT_EXECUTION` | Autonomous loop, cleanup, consolidation, or self-evolution behavior; never runs directly. |

MasterMind routes tools, the three local operating brains request them within their company scope, and the user approves any action beyond analysis. No tool is an autonomous commercial actor.
