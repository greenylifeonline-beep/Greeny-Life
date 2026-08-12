# Intelligence Runtime Policy

## Approved runtime components

- `greenlines_brain/evidence_gate.py`: fail-closed evidence assessment.
- `greenlines_brain/kernel.py`: read-only reasoning and decision support.
- Canonical audit and integrity engines: read-only validation against `canonical/data/master_products.json`.
- TypeScript adapters in `lib/intelligence/`: controlled access to legacy knowledge, with explicit historical status.

## Retired from direct execution

`brain.py` modes that generate supplier, certificate, inventory, finance, CRM, logistics, customer, analytics, packaging, or label data are blocked. Its consolidation, deep-clean, and self-clean modes are also blocked.

No runtime component may generate business facts, delete files, move files, submit customs documents, make payments, transfer title, or create a pull request automatically.

## Report retention

All reports emitted by the retained canonical writer go to `archive/generated-reports/runtime/`. Reports are evidence artifacts, not operational truth; each must identify its input source and time.
