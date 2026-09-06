# Phase 6 / M01: Private workspace foundation

Date: 2026-09-06. Status: M01 complete for the private workspace and service foundation; M02 capture is next.

## What works

The [Next.js interface](../../apps/web/app/page.tsx) and [FastAPI backend](../../apps/api/notetaker/main.py) provide a private course library, course creation, lecture creation/listing, a saved lecture workspace and reload/reopen behavior. The UI explicitly says that recording, transcription and generated notes are not available yet. The Docker application now contains a Computer Science course and a lecture named **Binary search — workspace verification**, created through the browser and reopened after restarting both app containers. No lecture audio or generated notes were used in this check. The earlier SQLite preview and its separate sample course remain intact.

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
| Docker | Docker Desktop 4.89.0 (238018), client/server 29.7.2, Compose 5.5.0; Linux/amd64 engine running after the user's WSL installation and restart. |
| Containers | PostgreSQL 17.11 verified by query; Apache Kafka and SeaweedFS probes pass. All five images use immutable digests in Compose/Dockerfiles. Python and Node application images built and ran successfully. Tags alongside digests are descriptive; the digest pins content. |
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

## Run the container application

Open Docker Desktop and wait for its Linux engine. WSL setup is complete on the verified host. The [launcher](../../scripts/Start-App.ps1) detects the Docker CLI, checks the engine, initializes credentials only if absent, builds the app and waits for startup. It preserves existing volumes and does not stop unrelated processes. Stop the SQLite preview first if it occupies the app's ports.

The per-user Docker CLI was found at `C:/Users/Neil/AppData/Local/Programs/DockerDesktop/resources/bin/docker.exe`; a newly opened terminal should pick up the installed command path. If not, use that executable explicitly.

```powershell
pwsh -File scripts/Start-App.ps1 -NewUnlockCode
# For a later start using the existing browser session:
pwsh -File scripts/Start-App.ps1 -NoBuild
# Integration verification requires the host Python dependencies above:
pwsh -File scripts/Test-Services.ps1
# Optional drill restarts the three services; use when no recording is active.
pwsh -File scripts/Test-Services.ps1 -Restart
```

Open `http://127.0.0.1:3000` and paste the code from `.local/unlock-code.txt`. `-NewUnlockCode` revokes old sessions while retaining courses and lectures; omit it when the current session is valid. `-NoBuild` reuses existing app images and should be omitted after code changes. Either launcher/testing script accepts `-DockerPath` when necessary. The launcher needs Docker only; host Node/Python are required for development and host tests.

The initialization script has already been run on this workspace. It creates ignored service credentials and S3 identity configuration. Compose exposes only loopback ports, persists PostgreSQL data, SeaweedFS objects **and filer metadata**, and Kafka logs. It uses local service networking and S3 credentials. Models remain a separately provisioned local service; M01 starts none.

The service verifier creates and removes only its own freshly named synthetic S3 bucket/object and Kafka topic. The application tests use fresh random PostgreSQL schemas and remove only those schemas; they never drop the application database. The [restart drill](../../apps/api/notetaker/verify_restart.py) also creates a private synthetic course/lecture through the API in its own schema, stores an object and broker record, restarts the three containers, then reopens the course/lecture and checks the original object's byte length/SHA-256 and broker record. It removes only resources generated in that invocation. A nonzero exit is a failed check, never completion evidence. Interrupted checks can leave their uniquely named test resources for inspection.

`docker compose --env-file .local/services.env stop` stops services while retaining volumes. Do not use volume removal to solve an ordinary startup problem. There is no automatic backup. Never delete `.local` or volumes containing wanted data; future backup/restore work must preserve database and referenced objects together.

## Executed verification

| Check | Result and scope |
| --- | --- |
| Backend application suite | All 24 passed against real PostgreSQL, using an isolated random schema per test. The earlier 24-test SQLite preview run also passed. Covers fresh/repeated migration, retained data and prohibited destructive downgrade; create/reopen/restart; concurrent duplicate commands; changed-payload conflict; CSRF/origin; source/lecture ownership; tombstones; expired/revoked sessions; cookie flags; authenticated socket boundary; safe errors and foreign keys. Two upstream test-client deprecation warnings remain visible. |
| Existing architecture / AI suite | All 52 passed; unchanged saved model evidence remains bound to its hashes. |
| TypeScript / frontend production build | Passed. No remote fonts or image assets are required. Development telemetry is disabled in the launch script/container environment; the initial build displayed Next.js's telemetry notice before this setting was added. |
| Migration dialect | Migration 0001 executed successfully on fresh real PostgreSQL schemas and the application database; repeated migration and preserved-data checks pass. |
| Compose / scripts | Both app images built successfully. All five containers started. The launcher completed and generated a usable one-use code; API and broker health checks pass. Windows test temporary-directory permissions initially blocked pytest before application execution; the test script now creates a unique workspace test directory, and the rerun passes. |
| Browser walkthrough | Unlocked the workspace, created a CS course and lecture, reopened after page reload and an actual API process restart, inspected desktop/narrow layouts without page overflow, and checked keyboard skip navigation and form focus. Stopping the API during a create form produced a visible error and retained the entered title; that diagnostic form was cancelled, not saved. The preview clearly displays no recording/no notes. |
| Container-app browser | Unlocked the PostgreSQL-backed application, created Computer Science and the verification lecture through the UI, restarted API/web, reloaded and saw the same saved lecture/settings. The UI displays Private library rather than Local preview. |
| Service integration | S3 put/readback/length/SHA-256 and Kafka publish/consume pass. An actual restart of PostgreSQL, SeaweedFS and Kafka retained the synthetic course, lecture, settings, original S3 object and original broker record. Expected broker disconnect messages occurred during the deliberate restart; recovery and final assertions passed. This tests orderly container restart with volumes, not host loss, power failure or captured-audio durability. |

M01's stated foundation exit is complete. This is an implemented course/lecture application, not an implemented recording or AI notes pipeline. M02 capture, M03 speech, M04 detailed notes and subsequent increments remain planned in the [roadmap](phase-5-roadmap.md). G01–G06 remain open at product/release scope; the M01 evidence is a prerequisite, not a replacement for their later checks.

## Next inputs and actions

1. Begin M02's real microphone capture and journal/recovery path; the M01 service gate now passes.
2. Keep storage acknowledgement, browser recovery and gap reporting ahead of speech/note integration. Recording must remain safe with models unavailable.
3. For M03/M04, obtain representative English CS audio and a human-reviewed reference for key terms, corrections and worked examples. A short excerpt can start development; a separately annotated 45–60 minute recording is still required for release qualification. These are evaluation inputs, not requirements to create a course today.

Selected implementation references: [Next.js installation](https://nextjs.org/docs/app/getting-started/installation), [FastAPI container guidance](https://fastapi.tiangolo.com/deployment/docker/), [SeaweedFS reference Compose](https://github.com/seaweedfs/seaweedfs/blob/master/docker/seaweedfs-compose.yml), and [official Kafka image configuration](https://hub.docker.com/r/apache/kafka). Executed runtime evidence is recorded above.
