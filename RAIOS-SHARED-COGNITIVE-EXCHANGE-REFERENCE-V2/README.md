# RAIOS Shared Cognitive Exchange — Reference V2

Standalone executable reference. It is not a RAIOS runtime integration and does not declare stored data true or canonical.

## Test command

```bash
python3 run_tests.py
```

Benchmarks run after the unit suite and are recorded in `CERTIFICATION.json`.

## Architecture

- Filesystem content-addressed objects (`objects/ab/cd/<sha256>`)
- SQLite metadata index (`db/exchange.sqlite`)
- Logical collaboration WAL table `collab_events` (not SQLite WAL mode)
- Crash-safe ingest: temp write → fsync → SHA-256 verify → exclusive publish → metadata transaction
- Startup reconciliation for temps, orphans, and metadata-without-object
- Leases with fencing generations; write/write overlap rejected; read-only verifiers may coexist
- Capsules reference `artifact://sha256/...` instead of copying bytes

## Authority

The exchange stores and routes. It separates `storage_status`, `validation_status`, `trust_status`, and `canonical_status`. External model output is UNTRUSTED. FTS hits are retrieval candidates only.

See `WINDOWS.md` for Windows immutability and path-escape behavior.
