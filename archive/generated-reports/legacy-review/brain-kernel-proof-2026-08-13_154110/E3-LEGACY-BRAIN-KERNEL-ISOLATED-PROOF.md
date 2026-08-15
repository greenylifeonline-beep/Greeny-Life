# E3 Legacy Brain Kernel â€” Isolated Proof

Generated: 2026-08-13T13:41:11.2250215Z

## Scope

Disposable isolated run using empty temporary knowledge only. No legacy knowledge/data file was read or written; no network/database/external service; no brain.py.

## Result: FAIL

Finding: P1: semantic engine fabricates trade/export relations when repository rules are empty. This violates fail-closed evidence governance.

Recommendation: DO_NOT_REUSE_AS_DECISION_ENGINE. Extract memory, repository and explicit-rule parsing only after a promoted copy removes defaults and enforces NEEDS_VERIFICATION.

| Test | Status | Detail |
|---|---|---|
| empty_knowledge_initialization | PASS | Kernel instantiated with empty temporary knowledge; relations=5 |
| absence_of_evidence_behavior | FAIL | Kernel created default semantic relations: [('egypt', 'exports', 'honey', 0.5), ('egypt', 'exports', 'spices', 0.5), ('honey', 'export_to', 'norway', 0.5), ('spices', 'export_to', 'eu', 0.5), ('norway', 'requires', 'organic_certification', 0.5)] |
| decision_on_empty_knowledge | PARTIAL | confidence=MEDIUM; recommendation=ÔÜá´©Å ┘äÏº ┘å┘êÏÁ┘è Ï¿Ï¬ÏÁÏ»┘èÏ▒ honey ÏÑ┘ä┘ë norway Ï¡Ïº┘ä┘èÏº┘ï; evidence_count=2 |

No legacy source or knowledge file was changed.
