# Phase 6 / M01: Private workspace foundation

Date: 2026-09-06. Status: runnable preview implemented; full M01 service qualification pending WSL/Docker startup.

## What works

The [Next.js interface](../../apps/web/app/page.tsx) and [FastAPI backend](../../apps/api/notetaker/main.py) provide a private course library, course creation, lecture creation/listing, a saved lecture workspace and reload/reopen behavior. The UI explicitly says that recording, transcription and generated notes are not available yet. The preview contains a Computer Science course and a clearly named workspace-preview lecture created during browser verification, not a recording or generated note.

The backend has one-use local unlock, hashed sessions, HttpOnly/SameSite cookies, strict mutation-origin/CSRF checks, authorization and tombstone checks, idempotent creation, expected metadata and a consistent joined lecture snapshot. Lecture creation commits settings, its update cursor, a reference-only outbox record and command receipt together. Structured trace IDs and duration headers exclude content and credentials.

Migration [0001](../../apps/api/migrations/versions/0001_private_workspace_foundation.py) introduces owners/sessions/bootstrap, courses, lectures/epochs, immutable settings versions, jobs, outbox/inbox, receipts and update records. A destructive downgrade is deliberately disabled. M03/M05 still own actual dispatch, worker execution and full WebSocket replay; M01's authenticated socket sends only a snapshot-required notice then closes.

## Explicit preview exception

PostgreSQL remains the application system of record. While Docker was unavailable, this milestone added a **separately selected SQLite preview** to run the real course/lecture UI and application tests. It requires `NOTETAKER_PREVIEW=true`; there is no automatic fallback from PostgreSQL failure. The UI labels that mode and the local file is `.local/workspace.db`, excluded from Git and container builds.

This is an implementation-stage preview exception to the deployment baseline, not a replacement storage architecture or evidence of PostgreSQL concurrency/durability. Preview content is not automatically copied into PostgreSQL. Retain the preview file if its data is wanted; do not silently migrate or erase it when switching modes.

## Environment and dependencies

| Component | Recorded version / state |
| --- | --- |
| Host / Node | Windows build 26200; Node 22.13.1. |
| Python | 3.12.14 in a workspace `.venv`, initially created using the bundled local interpreter. |
| Frontend | Next.js 16.3.4, React/React DOM 19.2.8, TypeScript 5.9.3; exact transitive versions in the root lockfile. |
| Backend | FastAPI 0.141.1, SQLAlchemy 2.0.52, Alembic 1.19.2, Uvicorn 0.52.4; all 40 resolved packages hash-pinned in the backend lockfile. |
| Docker | User installed Docker Desktop 4.89.0. Client 29.7.2 and Compose 5.5.0 respond; Linux engine cannot start because WSL is missing. |
| Containers | PostgreSQL 17, Apache Kafka, SeaweedFS, Python 3.12 and Node 22 image manifests resolved to immutable digests in Compose/Dockerfiles. Images have not been pulled, built or executed here. Tags alongside digests are descriptive; the digest pins content. |
| Existing Ollama models | `qwen3:4b` and `qwen2.5:14b` are local installed entries. `glm-5.3:cloud` and `kimi-k3:cloud` are cloud-backed entries. Inventory was read; this milestone made no new inference calls or model downloads. |

The user authorized local-model testing. Use that authorization in the speech/note milestones; an installed cloud alias is not a local model and is not authorization to send lecture data externally.

## Run the local preview

From the repository root, with Node 22 and Python 3.12 available:

```powershell
npm ci --ignore-scripts
uv venv .venv --python 3.12
uv pip sync apps/api/requirements.lock --python .venv/Scripts/python.exe --require-hashes
pwsh -File scripts/Start-Preview.ps1 -NewUnlockCode
```

Open `http://127.0.0.1:3000` and paste the code from `.local/unlock-code.txt`. Only the backend stores the hashed code; the local file is a short-lived delivery mechanism. The code expires after 30 minutes. Treat the file as private; it inherits the workspace's Windows file permissions. On non-Windows hosts the administration command restricts the output file to the owner.

`-NewUnlockCode` revokes old sessions and creates a new one-use unlock code; it does not erase courses or lectures. Omit it when continuing with an unexpired browser session. The preview launcher checks ports 3000/8010, migrates before startup and stops its own API process when the foreground web process exits. It does not stop unrelated services. Port 8000 was already occupied on this machine, so this app uses 8010.

If Python is supplied separately, pass its existing environment interpreter using `-PythonPath`. The launcher requires dependencies already installed; it does not silently install software. Source code, schemas and locks are committed; local databases, tokens, dependencies and caches are not.

## Run the planned container stack after WSL is ready

Docker's current startup log says WSL is not installed and directs installation followed by a Windows restart. Finish that machine setup and open Docker Desktop until its Linux engine is running. The [Docker Windows setup documentation](https://docs.docker.com/desktop/setup/install/windows-install/) and [Microsoft WSL installation guide](https://learn.microsoft.com/en-us/windows/wsl/install) describe the host prerequisites. A successful `docker compose config` does not mean the engine is running.

The per-user Docker CLI was found at `C:/Users/Neil/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe`; a newly opened terminal should pick up the installed command path. If not, use that executable explicitly.

```powershell
# First time only; preserves existing credentials rather than overwriting them.
pwsh -File scripts/Initialize-Services.ps1

# Stop the preview first if using its ports for the container app.
docker compose --env-file .local/services.env up -d postgres seaweed kafka
pwsh -File scripts/Test-Services.ps1
docker compose --env-file .local/services.env --profile app up -d --build
docker compose --env-file .local/services.env exec api python -m notetaker.manage unlock
```

The initialization script has already been run on this workspace; skip it here. It creates ignored service credentials and S3 identity configuration. Compose exposes only loopback ports, persists PostgreSQL data, SeaweedFS objects **and filer metadata**, and Kafka logs. It uses local service networking and S3 credentials. Models remain a separately provisioned local service; M01 starts none.

The service verifier creates and removes only its own freshly named synthetic S3 bucket/object and Kafka topic. The application tests use fresh random PostgreSQL schemas and remove only those schemas; they never drop the application database. A nonzero exit is a failed/unavailable integration check, not permission to claim completion. After first successful service checks, still test process/container restart and object availability with persistent volumes before closing M01.

`docker compose --env-file .local/services.env stop` stops services while retaining volumes. Do not use volume removal to solve an ordinary startup problem. There is no automatic backup. Never delete `.local` or volumes containing wanted data; future backup/restore work must preserve database and referenced objects together.

## Executed verification

| Check | Result and scope |
| --- | --- |
| Backend application suite | 24 passed using an explicitly selected SQLite test database per test. Covers fresh/repeated migration, retained data and prohibited destructive downgrade; create/reopen/restart; concurrent duplicate commands; changed-payload conflict; CSRF/origin; source/lecture ownership; tombstones; expired/revoked sessions; cookie flags; authenticated socket boundary; safe errors and foreign keys. Two upstream test-client deprecation warnings remain visible. |
| Existing architecture / AI suite | All 52 passed; unchanged saved model evidence remains bound to its hashes. |
| TypeScript / frontend production build | Passed. No remote fonts or image assets are required. Development telemetry is disabled in the launch script/container environment; the initial build displayed Next.js's telemetry notice before this setting was added. |
| Migration dialect | Initial PostgreSQL DDL compiled offline. No PostgreSQL connection or migration has run. |
| Compose / scripts | Compose configuration validates with the installed CLI; initialization, preview and service-test scripts parse. Startup/runtime semantics are still untested against a running engine. |
| Browser walkthrough | Unlocked the workspace, created a CS course and lecture, reopened after page reload and an actual API process restart, inspected desktop/narrow layouts without page overflow, and checked keyboard skip navigation and form focus. Stopping the API during a create form produced a visible error and retained the entered title; that diagnostic form was cancelled, not saved. The preview clearly displays no recording/no notes. |
| Service integration | Pending: Docker engine reports WSL missing. Real PostgreSQL tests, S3 readback, Kafka round trip, image builds and persistent-volume restart checks have not run. |

The preview is an implemented application slice, not an implemented recording or AI notes pipeline. M01's full exit remains open until the real-service evidence passes. M02 capture, M03 speech, M04 detailed notes and subsequent increments remain planned in the [roadmap](phase-5-roadmap.md).

## Next inputs and actions

1. Finish WSL/Docker startup and rerun the real-service suite plus container restart checks; fix any failures before marking M01 complete.
2. Begin M02's real microphone capture and journal/recovery path once M01's service gate passes.
3. For M03/M04, obtain representative English CS audio and a human-reviewed reference for key terms, corrections and worked examples. A short excerpt can start development; a separately annotated 45–60 minute recording is still required for release qualification. These are evaluation inputs, not requirements to create a course today.

Selected implementation references: [Next.js installation](https://nextjs.org/docs/app/getting-started/installation), [FastAPI container guidance](https://fastapi.tiangolo.com/deployment/docker/), [SeaweedFS reference Compose](https://github.com/seaweedfs/seaweedfs/blob/master/docker/seaweedfs-compose.yml), and [official Kafka image configuration](https://hub.docker.com/r/apache/kafka). Container commands remain subject to the unexecuted runtime checks above.
