# ORDERS — PowerShell assistant (field engineer)

FROM: Cursor commander
TO: Local PowerShell assistant
MODE: EXECUTE, not census
REPO: `C:\Users\Ghanam\Documents\Codex\Greeny-Life-Repair`
BRANCH: `v9-neurolingua-semantic-kernel`
DO NOT TOUCH: OneDrive `C:\Users\Ghanam\OneDrive\projects\Greeny-Life`

You are not the architect. You compress the estate and return receipts.
If a unique `.ts`/`.py` is not a hash-duplicate of a keeper, DO NOT delete it; list it.

## Run this and nothing else first

```powershell
Set-Location 'C:\Users\Ghanam\Documents\Codex\Greeny-Life-Repair'
$ErrorActionPreference = 'Stop'
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\ai-os\estate-hash-gc.ps1
```

If the script is missing, you still have git: `git pull origin v9-neurolingua-semantic-kernel` then rerun.

## Forbidden

- No new `_raios-*` folder
- No `migration/gl-004` or `migration/gl-005`
- No worktree recreate
- No `git add .`
- No force-push
- No delete under `canonical/`, `lib/`, `app/`, `src/`, `RAIOS/V9/`, `.ai-os/`, `tests/`, `prisma/`
- Do not treat engine-audit 1872 as inventory

## After the script

Return exactly:

```
GC_EXIT=
TAG=
DELETED_FILES=
DELETED_BYTES=
UNIQUE_KEPT=
DANGLING_COUNT=
TYPECHECK_EXIT=
TEST_CANONICAL_EXIT=
TEST_ORCH_EXIT=
RECEIPT_PATH=
RECEIPT_SHA256=
```

Then STOP and wait. Do not invent a follow-up census.
