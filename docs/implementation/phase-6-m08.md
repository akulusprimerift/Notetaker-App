# Phase 6.8 / M08 — Electron Windows application

Updated 2026-09-11. M08 is the active implementation phase. The user superseded the earlier Qt direction and selected Electron as the only Windows desktop host. The Qt/native app, standalone native storage profile, native packaging workflow and native-only tests have been removed from the repository.

## Current Electron delivery

Electron 44.3.0 hosts the existing Next.js/React workspace in a sandboxed, context-isolated renderer. `bun run dev:desktop` opens the desktop shell. `bun run build:desktop` creates an unsigned per-user x64 NSIS installer under `.local/desktop-dist`, with Start menu and desktop shortcuts. Uninstall retains app data. The installer includes the service source and pinned locks, but no credentials, lecture data, caches or model weights.

The shell starts or reconnects to the Docker/FastAPI workspace, offers existing-workspace selection, discovers local Ollama and speech-model files, and keeps mutable configuration in the per-user Electron data directory. The app manages only its startup helper; unrelated Docker workloads are not stopped. Hiding the window keeps recording and background processing alive. Explicit Quit explains what happens to a recording journal and already-confirmed audio.

## Workspace navigation increment

The lecture workspace now uses a persistent course-and-lecture sidebar and focused lecture sections: **Study notes**, **Transcript**, **Materials**, **Capture**, **Visual notes**, and **Finish**. A compact capture bar stays mounted across section changes, so changing tabs cannot dispose an active recorder. Capture exposes the available audio input, keeps captured and confirmed-save progress separate, and keeps recovery actions in the Capture section. The sidebar expands the selected course to show its lectures and the current lecture remains directly reachable.

The Visual notes section ports the source-linked schematic reader into the Electron renderer. It draws only app-generated SVG shapes from validated diagram data, renders model labels as React text nodes, and never executes model HTML or JavaScript. It explains that diagrams are cited schematics rather than recovered slide images and marks sections that need review after student edits. Existing Markdown and self-contained HTML exports remain served by the API.

All earlier lecture behavior remains in the shared React/API path: local audio journal and recovery, live timestamped transcription, protected corrections, contextual streamed note sections, saved prompt profiles, source inspection/playback, materials, revision comparison, keep/merge/replace/undo, final snapshots, deletion reconciliation and browser-copy purge. Local note models remain explicit selections. Cloud API/subscription connections remain opt-in per lecture and subject to provider/account qualification.

## Security boundary

Renderer Node integration is disabled, context isolation and sandboxing are enabled, navigation and new windows are restricted, and the webview tag is blocked. The microphone permission handler accepts only audio requests from the exact loopback workspace origin and asks the user before granting access. Setup IPC checks the exact sender frame; workspace settings can only request the setup window. Lecture/model text has no filesystem or shell authority.

## Verification

The existing Electron policy/model-discovery tests cover loopback navigation, audio-only permission checks, installed-model metadata, missing providers and speech-model detection. The desktop smoke covers renderer isolation, denied setup IPC from the lecture page, separate setup/model discovery, synthetic IndexedDB audio preservation across journal reopen, workspace reuse, service-outage messaging and window hide/show. It never requests a microphone.

The shared JavaScript contracts, web typecheck, lint, production build, API tests, Ruff, documentation checks and whitespace checks remain the relevant verification set. Synthetic audio cannot qualify physical microphone behavior, sustained performance, accessibility, educational usefulness, live provider compatibility or release readiness.

## Recovery, upgrades and remaining release work

Preserve Docker volumes, their matching `.local/services.env` and `s3.json`, the Electron user-data directory, any recovery journal/drafts, and any external speech-model folder. A filesystem copy taken while services are writing is not a coordinated backup. Existing immutable note/final exports remain available for selected revisions.

Before upgrading service software, finish recording and allow audio saves and inference to settle; close the desktop. Keep a coordinated database/object backup and deletion journal. An app-only reinstall retains user data; service migrations run on the next service startup. A full automated quiesced backup/restore and deletion-journal replay tool remains required.

Open gates are clean Windows installation and prerequisite experience, upgrade/uninstall retention on a separate machine, signed distribution, actual microphone/device failures, full-hour endurance, human educational-quality review, accessibility qualification and coordinated restore. The installer is a development distribution with Docker/PowerShell/Ollama prerequisites, not a standalone offline bundle. The user currently authorizes synthetic audio only.

References: [Electron security](https://www.electronjs.org/docs/latest/tutorial/security), [Electron sandboxing](https://www.electronjs.org/docs/latest/tutorial/sandbox), and the [phase plan](../project-phases.md).
