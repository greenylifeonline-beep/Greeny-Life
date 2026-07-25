# GOVERN_STOP — the kill switch

`touch GOVERN_STOP` at the repo root halts every govern-gated automation:
`govern gate` exits non-zero while the file exists, so any automerge or
loop keyed on it stops immediately — no deploy, no config change.

Re-arm by deleting the file through your normal review process. The gate
refusing while this file exists is contract-pinned; automation must never
remove it on its own.
