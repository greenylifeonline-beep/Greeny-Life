# Legacy Repair Register

## Repaired and retained

- `greenlines_brain/evidence_gate.py` is retained as a fail-closed evidence rule: missing, expired, non-official, or incomplete evidence cannot produce a GO decision.
- `greenlines_brain/kernel.py` and its knowledge repository are syntactically valid and were executed against the current extracted knowledge.
- The observed export scenario returned **verification required**, not permission to export.
- Legacy npm commands were repaired to execute a real legacy-health inspection instead of failing on missing paths.

## Protected from unsafe use

- All legacy migration aliases now refuse to execute. A migration requires a reviewed field mapping, data-quality gate, and explicit approval.
- Historical reports and generated artifacts remain reference material; they do not become runtime authority.
- The final runtime keeps the evidence-first decision API as the only trade-decision entry point.

## Remaining work

- The legacy domain/application layers require per-domain integration tests before any use in runtime.
- The Green Lines brain is an evidence and knowledge component; it is not an authority to infer missing regulatory facts.
- Live sources, OCR, search, shipping, and finance integrations require provider contracts and credentials before activation.
