# SQLite library, conversion, and recovery

Updated 2026-10-03. SQLite is the application database for the browser, Docker, Windows, and macOS runtimes. Each library uses one SQLite file on a local filesystem. PostgreSQL remains only as a legacy source for explicit conversion; starting the app never migrates or deletes it.

SQLite connections enable foreign keys, WAL mode, a 30-second busy timeout, and full synchronous commits. API and worker processes must share the same database file and local filesystem so the per-library inference lock files coordinate across processes. Network filesystems are unsupported. SQLite permits one writer at a time; the app serializes state-changing claims and writes, but this profile is for one local learner rather than a multi-host service.

## Convert a PostgreSQL library

Conversion reads one read-only repeatable-read snapshot. It requires a source schema revision present in this checkout, creates a new adjacent staging file, copies every application table in foreign-key order, checks source and destination row counts and SHA-256 digests, upgrades SQLite to the current Alembic head, runs SQLite integrity and foreign-key checks, then atomically publishes the new file. Existing destinations are refused. The source is never modified. Keep the original PostgreSQL data and its audio objects as the rollback copy.

For the existing Docker workspace, stop application writers while leaving its database available. The `migration` profile starts only the retained PostgreSQL service and reuses the existing `postgres-data` volume. Existing `.local/services.env` credentials are not overwritten by the initializer.

```powershell
docker compose --profile migration up -d postgres
docker compose --profile app stop api notes speech web
$taskValues = @{}
foreach ($taskLine in (Get-Content .local/services.env)) {
    $taskParts = $taskLine -split '=',2
    if ($taskParts.Count -eq 2) { $taskValues[$taskParts[0]] = $taskParts[1] }
}
$env:NOTETAKER_POSTGRES_EXPORT_URL = "postgresql+psycopg://notetaker:$($taskValues.POSTGRES_PASSWORD)@127.0.0.1:5432/notetaker"
uv pip sync apps/api/requirements-migration.lock
$env:PYTHONPATH = 'apps/api'
uv run --no-project python -m notetaker.postgres_migration --target (Join-Path $PWD '.local/sqlite/notetaker-import.sqlite3')
Remove-Item Env:NOTETAKER_POSTGRES_EXPORT_URL
```

Run conversion from the repository checkout whose Alembic migrations match the old app. The destination parent is created, but the destination file must not exist. The command prints the source/current revisions, per-table row counts, a digest over all source table digests, and the output path. It does not print row contents or the connection URL. Keep the output file until the app opens the converted library and representative notes, transcript revisions, final snapshots, retention choices and pending deletions have been inspected.

To use the converted database in Docker, stop the app and copy it to the Compose default only if that destination does not exist:

```powershell
if (Test-Path .local/sqlite/notetaker.sqlite3) { throw 'Choose a new library path; the current SQLite database was retained.' }
Move-Item .local/sqlite/notetaker-import.sqlite3 .local/sqlite/notetaker.sqlite3
docker compose --profile app up -d api notes web
```

The SQLite file preserves relational IDs and references, immutable note/transcript/finalization revisions, timestamps, command receipts, job attempts and leases, outbox/inbox state, deletion tombstones, and audio-retention fields. Audio objects are outside the database. Preserve the corresponding SeaweedFS volume and filer data at cutover; changing the database alone does not copy or validate audio objects.

The Windows and Mac frozen service also exposes `migrate-postgres --target <new-file>` and reads its source URL from `NOTETAKER_POSTGRES_EXPORT_URL`. Use a source PostgreSQL endpoint and credentials explicitly supplied by the existing library owner. Do not start the new library until the converter reports success. A legacy standalone library whose PostgreSQL server is no longer running needs its owner to start that server with its matching PostgreSQL runtime first; the new app does not start or upgrade old PostgreSQL data automatically.

## Backup and restore

For a SQLite-only snapshot, use SQLite's online backup API rather than copying a live `.sqlite3` file without its WAL sidecars:

```powershell
$env:PYTHONPATH = 'apps/api'
uv run --no-project python -m notetaker.backup_sqlite `
  --source .local/sqlite/notetaker.sqlite3 `
  --target .local/backups/notetaker-2026-10-03.sqlite3
```

The helper writes a new file only, checks `integrity_check` and `foreign_key_check`, and refuses to overwrite an existing backup. For a complete lecture-library backup, quiesce capture and workers, stop the app and SeaweedFS, and preserve the SQLite snapshot together with SeaweedFS volume and filer data, the matching S3 configuration/secret, and the backup date/version. The lecture deletion ledger and tombstones live in SQLite; retain them with the library and apply any newer external deletion journal before serving a restored backup.

Restore into a new library directory, verify the SQLite integrity and foreign keys, restore the matching object/filer data and credentials, then open the app. A database-only restore may leave audio objects unavailable and must be treated as incomplete until reconciliation verifies them. Never overwrite a newer library during restore.

## Rollback and limits

The source PostgreSQL volume and objects remain intact after conversion. Before making writes in SQLite, rollback means closing the new app and reopening the original PostgreSQL-backed release with its original credentials and objects. After SQLite accepts new writes, those changes are not copied back automatically; retain both libraries and choose one authoritative library before resuming. No bidirectional merge is provided.

Synthetic migration tests exercise every table-copy/check/publish step and preserve representative immutable and retention state. PostgreSQL server integration has not been qualified in this environment because no PostgreSQL server or Docker daemon is available. Conversion has no measured scale limit or benchmark yet. A repeatable-read export may use substantial temporary disk space, approximately the size of the destination database plus SQLite journal/WAL overhead. The original PostgreSQL source and audio/object backup remain the recovery path until a complete restore drill is qualified.
