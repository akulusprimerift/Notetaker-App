# Phase 6.8 / M08 — Windows application

Updated: 2026-09-08. Active implementation phase. Electron host and Windows installer are implemented; release qualification remains open.

## Windows delivery

Electron 44.3.0 reuses the existing loopback UI/backend. `bun run dev:desktop` opens the desktop host. `bun run build:desktop` produces `.local/desktop-dist/Notetaker-0.1.0-Setup.exe`, an unsigned per-user x64 NSIS installer with Start menu/desktop shortcuts. The installer retains app data on uninstall. The build includes the service source, pinned locks and startup scripts, but no credentials, lecture data, caches or model weights.

This distribution explicitly requires Docker Desktop (Linux containers), PowerShell 7 and Ollama for note generation. First service startup builds software dependencies; it never provisions models. Packaged service files are copied to `%APPDATA%/Notetaker/services`, keeping mutable configuration outside the install directory. Newly created desktop services use Compose project `notetaker-desktop`; development services retain `notetaker`. An already running loopback workspace can be opened without stopping or replacing it. Existing development and desktop data volumes are not merged automatically. Stop the intended deployment before starting another on the same loopback ports; retain its original credentials with its volumes.

Setup shows startup readiness/errors and local model discovery. Ollama's local inventory is queried; remote/cloud registrations are excluded. Common LM Studio/Hugging Face directories are inspected for model files, and offline Ollama manifests are listed as unverified registrations. Detection is not a compatibility guarantee or automatic import. The existing note adapter still verifies supported local Qwen models, model digest and context capacity before generation. A folder chooser accepts an existing faster-whisper directory containing model.bin and config.json and supplies its path to Compose. No model download or external inference fallback exists.

Renderer Node integration is off, context isolation and sandboxing are on, navigation/new windows are restricted, and setup IPC checks the exact sender frame and setup document. Microphone access requires the local lecture page and an explicit audio-only desktop prompt. Setup opens in a separate window, preserving the lecture. Hiding keeps the renderer running without background throttling; explicit Quit explains recorder closure and journal recovery. Services continue processing when the desktop closes. Only the app-started startup helper is launched; unrelated Docker workloads are not stopped.

## Verification

Executed on Windows 11 build 26200: desktop policy/model-discovery unit tests passed; frozen Bun installation passed. An actual Electron smoke test passed renderer isolation, denied setup IPC from the lecture page, separate setup/model discovery, synthetic IndexedDB audio preservation across journal reopen, and window hide/show. Screenshots `.local/desktop-setup.png` and `.local/desktop-workspace.png` were produced; setup was visually inspected. The smoke test uses its own profile and never requests microphone access. Run `node tests/desktop/smoke.cjs` with the existing uv-managed Playwright dependency and the local workspace running.

An initial unsigned NSIS installer build succeeded. Subsequent changes add final icon/metadata, PDF support and updated model filtering; final build and packaged-install evidence are recorded in the session transfer. Material/streaming verification is in [course materials](course-materials.md). Earlier real-service verification passed 148 PostgreSQL tests and storage/broker probes before the final PDF follow-up. Do not treat these as a clean-machine or real-lecture result.

## Recovery, upgrades and remaining release work

Preserve Docker volumes, their matching `services/.local/services.env` and `s3.json`, the Electron user-data directory (including recovery journal/drafts), and any external speech-model folder. These locations contain different parts of the library. A filesystem copy taken while services are writing is not a coordinated backup. Existing immutable note/final exports remain available for selected revisions.

Before upgrading service software, finish recording and allow audio saves and inference to settle; close the desktop. Keep a coordinated database/object backup and deletion journal. An app-only reinstall retains user data; service migrations run on the next service startup. Do not change credentials or remove volumes as a repair shortcut. A full automated quiesced backup/restore and deletion-journal replay tool remains required; no unverified restore command is provided.

Open gates: clean Windows machine install/prerequisite experience, upgrade/uninstall data retention on a separate qualification machine, signed distribution, actual microphone/device failures, full-hour endurance, human educational-quality review, accessibility qualification and coordinated restore. The installer is a development distribution with prerequisites, not a release-ready standalone offline bundle. The user currently authorizes synthetic audio only.

References: [Electron security](https://www.electronjs.org/docs/latest/tutorial/security), [Electron sandboxing](https://www.electronjs.org/docs/latest/tutorial/sandbox), and [phase plan](../project-phases.md).
