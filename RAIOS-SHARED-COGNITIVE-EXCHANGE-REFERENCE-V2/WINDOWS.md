# Windows behavior — Cognitive Exchange Reference V2

This package does **not** treat `chmod 0444`, the NTFS read-only attribute, or DACLs as an immutability/security boundary.

## Object immutability (application-level)

1. Object identity is SHA-256 of the bytes.
2. Publish is exclusive-create (`os.link` when available, otherwise `O_CREAT|O_EXCL` then replace of the owned dest). Existing canonical objects are never overwritten.
3. Every authoritative read re-hashes the file and fails closed on mismatch (`OBJECT_HASH_TAMPER_DETECTED`).
4. Duplicate concurrent ingestors of identical bytes resolve to one physical object.

`os.replace` on Windows can overwrite; this package therefore does not use replace against an unowned dest. SQLite transactions do not make those filesystem steps atomic; ingest is PREPARE → temp+fsync → verify → exclusive publish → metadata transaction, with startup reconciliation for interrupted temps and orphans.

## Path security

User-supplied paths/scopes are rejected if they contain:

- `..` traversal
- absolute POSIX paths
- drive-letter prefixes (`C:\...`)
- UNC prefixes (`\\server\share` or `//server/share`)
- `:` alternate data streams
- reserved device names (`CON`, `PRN`, `AUX`, `NUL`, `COM1`–`COM9`, `LPT1`–`LPT9`)
- symlinks / junctions / reparse points on any path component

Containment uses resolved/normalized paths (`os.path.normcase` + `Path.resolve` + `relative_to`). `os.path.basename` is never the containment check. Imported content is never executed.

Lease scopes are normalized to lowercase `/` separators so `A/B` and `a/b` collide on case-insensitive volumes.

## SQLite WAL vs collaboration WAL

`PRAGMA journal_mode=WAL` is an internal SQLite durability setting only.

The collaboration event WAL is the append-only `collab_events` stream (`event_id`, `sequence`, `correlation_id`, `causation_id`, `event_type`, `payload_hash`, `previous_event_hash`, `event_hash`, `timestamp`, `idempotency_key`).
