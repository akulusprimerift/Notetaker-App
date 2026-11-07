# SQLite standalone delivery — 2026-10-05

Active phase remains **6.9.5 — Mac installer and distribution**. The user's requested SQLite switch takes priority. Earlier PostgreSQL/Docker build evidence is historical and does not qualify this runtime.

## App behavior

SQLite is the only application database. The default private library is `<app-data>/sqlite-library`: `workspace.sqlite3` stores every course, lecture, transcript/settings/note revision, protected edit, final snapshot, job lease, epoch, receipt, deletion record and outbox/inbox history. Verified immutable audio files live in `audio/`. Existing browser recovery journals, drafts, theme settings and protected account credentials stay in the app-data profile. No database password is needed; account credentials continue using the host's protected storage.

The launcher starts FastAPI, Ollama and the separate speech/notes workers. It no longer starts PostgreSQL, SeaweedFS or Kafka, and it reserves only the web/API/Ollama ports. Setup offers a new library or an existing SQLite folder. Older saved desktop configurations require an explicit choice; they cannot silently open an empty replacement for a PostgreSQL library. Legacy data and encrypted credential files are retained. Models remain selected local files; no weights are downloaded.

SQLite connections enable foreign keys, WAL, FULL synchronization and a 30-second busy timeout. Mutation/claim locks acquire the SQLite writer before authoritative state checks. Migrations explicitly begin a write transaction so SQLite DDL participates in commit/rollback. Native OS file locks provide independent speech and notes inference slots across processes and release on process death; learning generation shares the notes slot. Capture and object verification do not wait for model inference. Saved-job reconciliation replaces broker delivery; existing outbox/history remains intact.

Audio writes fsync a temporary file, publish an immutable hard link, and compare readback before acknowledgement. Retrying an identity cannot overwrite its original audio. Traversal is rejected, Windows extended paths support long library/object names, and local deletion reconciliation includes late/unpublished files. Audio preservation remains independent of inference.

Docker Compose, Dockerfiles, Docker setup/start/provisioning scripts, broker service probes and the PowerShell discovery helper were removed. Build-time PowerShell scripts remain for Windows provisioning/documentation, and an isolated SQLite developer UI preview remains available. They are not end-user prerequisites. The provider bridge now listens only on loopback.

## Explicit earlier-library conversion

Conversion writes a **new folder**, verifies all 36 application tables and their values, preserved student edits/final snapshots, retained audio checksums, SQLite integrity and foreign keys, then publishes it. It keeps the source and refuses any existing destination. A failed conversion retains an inspectable `.pending-*` folder and never presents it as an imported library. Running/expired job attempts remain fenced by their original epochs/tokens; source/settings/history IDs are preserved.

This is a maintenance conversion tool; it does not start an older PostgreSQL or audio service and does not silently access the student's library. Before conversion, finish capture, wait for confirmed saves, and pause the **earlier app's speech/notes workers** while retaining its PostgreSQL and audio services. An earlier standalone app must be managed with its earlier runtime; an earlier container library requires its earlier service environment for this one conversion. New users require none of those services. Source schema must be 0018; update an older app first. Keep a verified backup and the earlier installation until import/reopen succeeds.

Create an isolated maintenance environment (its PostgreSQL/S3 drivers are excluded from the shipped service):

```powershell
uv venv .local/legacy-conversion
uv pip sync --python .local/legacy-conversion/Scripts/python.exe apps/api/requirements-legacy.lock
$env:PYTHONPATH='apps/api'
```

Set these environment variables locally using the **earlier** library's existing configuration; never paste their values into Git, command logs or documentation:

- `NOTETAKER_LEGACY_DATABASE_URL`: `postgresql+psycopg` URL for its loopback server, database and existing credentials.
- `NOTETAKER_LEGACY_S3_ENDPOINT`, `NOTETAKER_LEGACY_S3_ACCESS_KEY`, `NOTETAKER_LEGACY_S3_SECRET_KEY`: earlier loopback SeaweedFS endpoint/credentials.
- Optional `NOTETAKER_LEGACY_AUDIO_BUCKET` (default `notetaker-audio`). If original audio is already in ordinary files, use `--audio-directory` instead of the S3 variables.

After explicitly pausing the source workers:

```powershell
uv run --no-project --python .local/legacy-conversion/Scripts/python.exe python scripts/convert-library.py --source-paused --destination C:/Notetaker/ConvertedLibrary
```

The source is read in one repeatable, read-only database snapshot. Oversized, missing retained or checksum-mismatched audio stops publication; legitimately released/removed audio remains absent. The private report contains table counts/digests and audio identities, with no provider/database credentials. Open setup in the updated app and select **Choose an existing SQLite library**, then the new folder. Reopen courses, sources, protected edits and exports before retiring the earlier services. Never copy an actively used SQLite database without its WAL; use SQLite backup or pause services before copying the whole library.

## Windows build

Use locked Bun and uv dependencies. The frozen service must be rebuilt; do not reuse an earlier PostgreSQL service or installer:

```powershell
bun install --frozen-lockfile --ignore-scripts
uv pip sync apps/api/requirements-windows.lock apps/api/requirements-dev.lock
bun run build:windows-service
bun run prepare:desktop-web
pwsh -NoProfile -File scripts/Provision-WindowsRuntimes.ps1
bun run prepare:windows-runtime <new-web-directory> <new-service-directory>
$env:NOTETAKER_NATIVE_RESOURCES='<new-runtime-directory>'
bun run build:desktop --config.directories.output=.local/sqlite-switch/installer
```

Provisioning is build-time only, verifies the pinned Ollama archive and downloads no models. The runtime manifest uses `windows-sqlite-local-reconciliation`. Packaging requires that standalone runtime; it no longer bundles Docker service source as a fallback. The Windows tag workflow runs all SQLite backend tests, builds the frozen service/web component, provisions only Ollama and publishes the standalone installer.

Verify the frozen migrations and document parser, then the packaged Electron workflow in a disposable profile:

```powershell
$env:PYTHONPATH='apps/api'
$env:NOTETAKER_TEST_SERVICE_EXECUTABLE='<prepared-runtime>/service/NotetakerService.exe'
uv run --no-project python -m pytest -q apps/api/tests/test_sqlite_library.py apps/api/tests/test_windows_material_parser.py
$env:NOTETAKER_TEST_EXECUTABLE='<installer-output>/win-unpacked/Notetaker.exe'
bun run test:standalone '<prepared-runtime>'
```

The Bun script runs the existing Node-based Playwright driver. Invoking this harness directly in Bun timed out during the Electron debugger handshake on this Windows environment. The package check creates a fresh SQLite library, captures synthetic oscillator audio through the real recorder, repeats start/stop three times, finalizes/exports and quits/reopens with byte-identical source audio. It never opens the microphone or the student library. Tagged Windows CI now runs these checks after packaging.

## Mac build

On an Apple Silicon Mac, use the locked native arm64 uv environment, `bun run build:macos-service` and `bun run prepare:desktop-web`. The component descriptor now requires only `service`, `ollama` and `account-client`, each with its original notices and hash inventory. Run `bun run lock:macos-runtime <descriptor>`, `bun run prepare:macos-runtime <web> <lock>` and `bun run build:macos-app <runtime>`. The manifest uses `macos-sqlite-local-reconciliation`; PostgreSQL/Seaweed build/download steps were removed from tagged CI. Existing signing/notarization behavior is retained. Earlier published DMGs still contain the previous runtime until a new tag is built.

## Executed evidence

Windows x64, Python 3.12.14, Bun 1.3.10 and uv 0.12.10; all libraries and audio used for verification were disposable/synthetic:

| Executed check | Result |
| --- | --- |
| Locked dependencies | `bun install --frozen-lockfile`; `uv pip sync apps/api/requirements-windows.lock apps/api/requirements-dev.lock` passed. Eleven retired client/dependency packages removed from the normal environment. |
| Full backend on SQLite | **277 passed, 1 skipped**, 461.45 s. The skip requires a packaged document parser; it passed in the focused frozen run below. Two existing dependency deprecation warnings remain. |
| Frozen SQLite/conversion/host/parser checks | **26 passed, no skips**, 54.29 s, using the newly rebuilt `NotetakerService.exe`. Both fresh and earlier-schema migration processes exit with committed schema 0018; the earlier course/lecture and retained-audio policy survive. |
| JavaScript contracts / desktop contracts | **63 / 40 passed**. Desktop checks include legacy/incomplete-library refusal, new setup persistence, platform manifest requirements and rejection of SQLite databases/WAL/import reports from build inputs. The staged runtime also passes this updated privacy inventory. |
| Frontend and Python | Typecheck, JavaScript lint, production Next.js build/web bundle and Ruff passed. |
| Real legacy conversion | A disposable PostgreSQL + SeaweedFS source converted through `scripts/convert-library.py`: **36 tables, 81 records, 3 audio files**. Every source/target table digest and audio byte matched, including protected student edits and a final snapshot; source rows remained unchanged. No student library was used. |
| SQLite failure/concurrency checks | Missing, corrupt or oversized audio prevents conversion publication; destination overwrite is refused. Concurrent course commands/reopen, FK/integrity/WAL/FULL checks and cross-process inference exclusion/crash release passed. |
| Standalone source launcher with frozen services | Real oscillator recorder: **3 start/stop cycles**, verified upload/seal, finalization, Word/slides/text exports, theme persistence and byte-identical source readback after Quit/reopen passed. Observed launch/reopen: 56.84 / 29.33 s during concurrent build/compression; not a matched performance benchmark. |
| Packaged Electron app | The same complete recorder/export/Quit/reopen checks **passed** using `.local/sqlite-switch/installer/win-unpacked/Notetaker.exe`. Its fresh profile is `.local/standalone-smoke-176b9c75-8f61-45f2-801f-0ac740ea58ee`; launch/reopen observed 27.49 / 44.76 s under concurrent installer compression, without a performance claim. |
| Missing-model standalone host | SQLite API write/read passed; observed host startup 7.8 s. Missing speech-model status remained explicit. |
| Actual local models and restart recovery | Frozen SQLite host, small.en + qwen3:4b, 68.04 s synthetic lecture uploaded without real-time pacing: **35 verified chunks, 5 completed speech windows, 7 saved note revisions**. Citations/source audio, material upload, protected save/regeneration/merge/undo, recall/self-assessment/catch-up and selected-revision exports passed. The first uninterrupted run hit its hard-coded 600 s final-snapshot deadline during the last model request; it is **not counted as a full passing harness run**. Reopening that disposable library recovered the fenced job, produced/exported the strict final snapshot, retained all **3 immutable student edit revisions** unchanged, and verified every original audio byte plus SQLite integrity/FKs. The snapshot honestly remains `incomplete` for uncertain speech, unclear coverage and the student's selected earlier sources/settings. |
| Runtime inventory | **2,319 hashed files**, SQLite extension included; no PostgreSQL, SeaweedFS, psycopg, Kafka or boto clients. Final web bundle `.local/desktop-web/6c35360e-ffee-473e-819d-be367bf7516a`; frozen service `.local/windows-service/72da7318-78ef-4603-bd17-958f8c4f8315/dist/NotetakerService`; staged runtime `.local/windows-runtime/be9a81a1-bf77-459c-9cee-9e41679f623f`. |

The unsigned local Windows installer was built successfully: `.local/sqlite-switch/installer/Notetaker-0.1.0-Windows-Standalone-Setup.exe`, **318,285,556 bytes**, SHA-256 `F78D7E099C67C68FFEBCB85565D4401A2D993E4E39DC1A428D554B8A398A4794`. It was not installed or published automatically. Mac native building/signing was not executed on this Windows host.

The first packaged workflow exposed a migration transaction boundary: a successful process exit retained schema 0012 because the new explicit transaction had no owner committing its tail. The standalone migration path now uses an owned transaction, with fresh/upgrade process regression checks and a rebuilt service. Earlier unsuccessful runs are not counted as passing checks. The workflow harness now honors the requested timeout for finalization (with a 600 s minimum). Recovery evidence is retained in `.local/host-smoke-8775fb2a52f64504b6a3ac1c66e51225/sqlite-recovery-report.json`; original timeout, recovery and confirmation logs remain separate.

## Apple Silicon local build — 2026-11-07

Executed on the user's Apple Silicon Mac (Apple M5 Pro, 24 GB, macOS 26.6 build 25G72, native arm64): Xcode command-line tools, Bun 1.4.4 (the repository pins 1.3.10; `bun install --frozen-lockfile --ignore-scripts` left `bun.lock` unchanged), uv 0.13.7 and CPython 3.12.16 synchronized from the existing locks. All libraries and audio were disposable/synthetic; no student library, microphone, model download or provider call was used.

| Executed check | Result |
| --- | --- |
| Shared contracts | **63 JavaScript / 40 desktop passed**; typecheck, JavaScript lint, Ruff and whitespace passed. `bun run verify:docs` was **not run**: PowerShell is not installed on this Mac. |
| Full backend, first run | **268 passed, 8 failed, 2 skipped.** All failures were `test_cloud_notes.py` storing keys through Windows DPAPI, which deliberately refuses off Windows; Mac keys use the Electron bridge's Keychain-backed storage. Off Windows these tests now use a reversible test double, and a new check confirms the real backend store still refuses plaintext. |
| Full backend after fixes | **284 passed, 1 skipped** (packaged document parser), including the later Ollama Cloud and transcript-tail changes. With `NOTETAKER_TEST_SERVICE_EXECUTABLE` set to the Mac frozen service, the frozen parser and SQLite library checks pass (**20 passed**, no skips). |
| Native components | Pinned Ollama 0.33.3 `ollama-darwin.tgz` matched the workflow SHA-256; 22 Intel-only libraries were removed and the arm64 `ollama`/`llama-server`/`llama-quantize` slices load only system libraries. Codex 0.154.0 came from the Bun lock. Lock, staging (arm64/load-path audit) and app packaging passed. |
| Artifact | `.local/macos-standalone-dist/Notetaker-0.1.0-macOS-arm64-unsigned.dmg`, **619,884,164 bytes**, SHA-256 `0e910bd5c46b1351361d055a9d8327a695f3975fb1491986ec1a3a0422b347fe` (final build including [Ollama Cloud](ollama-cloud.md)). Ad-hoc signed: `codesign --verify --deep --strict` and `hdiutil verify` passed. Runtime stage `.local/macos-runtime/33ea2e65-5cbe-41a0-9869-6a25794f3011`. Not Developer ID signed, notarized, installed or published. |
| Packaged Electron smoke | **Passed** with the packaged `Notetaker.app`: fresh SQLite library, bundled host/API/speech/notes/Ollama/web startup, verified synthetic audio, **3 real recorder start/stop cycles** (AudioWorklet in the packaged app), finalization with Word/slides/text exports, Quit → reopen with byte-identical audio, renderer isolation and theme persistence. Final build: startup 5.48 s fresh / 3.09 s reopen, profile `.local/standalone-smoke-d7efa8df-0ce5-4d66-95f0-655e65780585`. |
| Speech workflow, local `small.en` | **Passed**, paced: first passage 8.15 s, backlog ≤ 8 s, transcript complete 2.05 s after capture, last passage ends at 64.96 s of 65.21 s, 98.9% of script words present. See [workflow harness](macos-workflow.md#mac-runs--2026-11-07). |
| Workflow harness, missing speech model | **Passed** with the frozen Mac host and 65.2 s of synthetic `say` speech, paced in real time: Markdown material saved, 33 verified chunks (save p50 0.014 s / max 0.017 s), missing-model status visible, no invented passages, all audio intact; host startup 0.98 s. A `--fast` run also passed. See [workflow harness](macos-workflow.md#mac-runs--2026-11-07). |
| Abrupt parent death | One manual check on a disposable profile: after `SIGKILL` of the Electron process, all bundled service processes exited within 2 s and ports 3000/8010/11435 were released. |

Defects found and fixed during this build:

- **Transcript reported finished before its ending.** After a recording stopped, the status read `processed` while saved audio past the last live window (here 60–65 s) had not yet been planned; the harness stopped there and the final sentence was missing. The status is now `queued` until every saved second has a window. A new regression test failed on the old code.

- **Course materials could not be uploaded on Mac.** The frozen API launched its isolated document parser as `NotetakerService.exe`, so every PPTX/DOCX/PDF/TXT/Markdown upload returned `material_unreadable`. It now relaunches the running service executable on every platform. A new unit test covering Mac and Windows paths failed on the old code for the Mac path; the frozen-build check reproduced the failure against the Mac service and passes after the fix.

- **Reopen refused after Quit.** Relaunching within about 30 s of a confirmed Quit showed "Port 3000 is in use" although no process was listening: the host's port probe bound without `SO_REUSEADDR`, so macOS rejected it while only `TIME_WAIT` sockets remained. The bundled servers themselves bind with reuse, so the probe was stricter than what it protects. On POSIX the probe now binds with `SO_REUSEADDR`, and a loopback connect check refuses any active listener, including wildcard binds. The occupied-port refusal test now runs on every platform; a new `TIME_WAIT` regression test failed on the old code and passes with the fix. Windows keeps `SO_EXCLUSIVEADDRUSE`.
- **Smoke test expected Windows chrome on Mac.** The Mac app intentionally keeps the standard title bar (`data-desktop=false`), so the test now checks for a non-draggable top bar on Mac and the drag region on Windows.

Still not executed on the Mac: Developer ID signing/notarization (no credentials configured), a quarantined download/clean-machine Gatekeeper launch, installing over the earlier PostgreSQL-based DMG, notes with a real local or Ollama Cloud model (no local note model is installed and no cloud key was used), real Keychain credentials, microphone permission/capture and sleep/wake.

## Remaining qualification

Actual SQLite Mac startup, permissions/Keychain, sleep/wake, native packaged lecture workflows, signed/notarized delivery, clean-machine installation and installed-library upgrades require their named environments. Synthetic checks do not qualify physical microphone capture, power-loss storage behavior, long-duration endurance or human note usefulness. Fewer processes are expected to reduce startup work; this change does not promise a measured end-user loading improvement without a matched before/after benchmark. No existing student library is converted automatically or accessed for these checks.

The qwen3:4b final-batch stall recovered after host restart, but its cause and unattended inference/endurance remain unqualified. The timeout adjustment does not claim to fix model behavior. Saved sources and student revisions survived; finalization uncertainty remains visible instead of being silently discarded.
