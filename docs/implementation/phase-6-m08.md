# Phase 6.8 / M08 — Electron Windows application

Latest increment (2026-09-18): [standalone Windows distribution](windows-standalone.md) bundles the Electron web server, Python workers, PostgreSQL, SeaweedFS and CPU Ollama. Users choose a separate native library or their existing Docker workspace. Native services use database reconciliation; Docker retains Kafka. Release gates remain open. Earlier delivery descriptions below are historical.

Updated 2026-09-11. M08 is the active implementation phase. The user superseded the earlier Qt direction and selected Electron as the only Windows desktop host. The Qt/native app, standalone native storage profile, native packaging workflow and native-only tests have been removed from the repository.

## Current Electron delivery

Electron 44.3.0 hosts the existing Next.js/React workspace in a sandboxed, context-isolated renderer. `bun run dev:desktop` opens the desktop shell. `bun run build:desktop` creates an unsigned per-user x64 NSIS installer under `.local/desktop-dist`, with Start menu and desktop shortcuts. Uninstall retains app data. The installer includes the service source and pinned locks, but no credentials, lecture data, caches or model weights.

The shell starts or reconnects to the Docker/FastAPI workspace, offers existing-workspace selection, discovers local Ollama and speech-model files, and keeps mutable configuration and protected provider connections in the per-user Electron data directory. An authenticated Electron-host bridge lets the Docker API/worker use selected API or official subscription connections without placing provider secrets in service volumes or API responses. The app manages only its startup helper; unrelated Docker workloads are not stopped. Hiding the window keeps recording and background processing alive. Explicit Quit explains what happens to a recording journal and already-confirmed audio.

## Workspace navigation increment

The lecture workspace now uses a persistent course-and-lecture sidebar and focused lecture sections: **Study notes**, **Transcript**, **Materials**, **Capture**, **Visual notes**, and **Finish**. A compact capture bar stays mounted across section changes, so changing tabs cannot dispose an active recorder. Capture exposes the available audio input, keeps captured and confirmed-save progress separate, and keeps recovery actions in the Capture section. The sidebar expands the selected course to show its lectures and the current lecture remains directly reachable.

The Visual notes section ports the source-linked schematic reader into the Electron renderer. It draws only app-generated SVG shapes from validated diagram data, renders model labels as React text nodes, and never executes model HTML or JavaScript. It explains that diagrams are cited schematics rather than recovered slide images and marks sections that need review after student edits. Existing Markdown and self-contained HTML exports remain served by the API.

All earlier lecture behavior remains in the shared React/API path: local audio journal and recovery, live timestamped transcription, protected corrections, contextual streamed note sections, saved prompt profiles, source inspection/playback, materials, revision comparison, keep/merge/replace/undo, final snapshots, deletion reconciliation and browser-copy purge. Local note models remain explicit selections. Cloud API/subscription connections remain opt-in per lecture and subject to provider/account qualification.

Note preferences now reports local model availability, groups compatible local Ollama models separately from connected providers, and exposes connection setup for OpenAI API, Claude API, ChatGPT/Codex subscription and Claude Code subscription. Materials use a two-step upload card with explicit save, size/type guidance and extracted-text review. The Electron application menu bar is removed; workspace settings remain in the renderer.

## Security boundary

Renderer Node integration is disabled, context isolation and sandboxing are enabled, navigation and new windows are restricted, and the webview tag is blocked. The microphone permission handler accepts only audio requests from the exact loopback workspace origin and asks the user before granting access. Setup IPC checks the exact sender frame; workspace settings can only request the setup window. Lecture/model text has no filesystem or shell authority.

## Verification

The existing Electron policy/model-discovery tests cover loopback navigation, audio-only permission checks, installed-model metadata, missing providers and speech-model detection. The provider-bridge test covers authenticated access, protected connection files, inventory, verification and removal using a storage test double. The desktop smoke covers renderer isolation, denied setup IPC from the lecture page, separate setup/model discovery, no application menu, synthetic IndexedDB audio preservation across journal reopen, workspace reuse, service-outage messaging and window hide/show. It never requests a microphone.

The shared JavaScript contracts, web typecheck, lint, production build, API tests, Ruff, documentation checks and whitespace checks remain the relevant verification set. Synthetic audio cannot qualify physical microphone behavior, sustained performance, accessibility, educational usefulness, live provider compatibility or release readiness.

## Recovery, upgrades and remaining release work

Preserve Docker volumes, their matching `.local/services.env` and `s3.json`, the Electron user-data directory, any recovery journal/drafts, and any external speech-model folder. A filesystem copy taken while services are writing is not a coordinated backup. Existing immutable note/final exports remain available for selected revisions.

Before upgrading service software, finish recording and allow audio saves and inference to settle; close the desktop. Keep a coordinated database/object backup and deletion journal. An app-only reinstall retains user data; service migrations run on the next service startup. A full automated quiesced backup/restore and deletion-journal replay tool remains required.

Open gates are clean Windows installation and prerequisite experience, upgrade/uninstall retention on a separate machine, signed distribution, actual microphone/device failures, full-hour endurance, human educational-quality review, accessibility qualification and coordinated restore. The installer is a development distribution with Docker/PowerShell/Ollama prerequisites, not a standalone offline bundle. The user currently authorizes synthetic audio only.

References: [Electron security](https://www.electronjs.org/docs/latest/tutorial/security), [Electron sandboxing](https://www.electronjs.org/docs/latest/tutorial/sandbox), and the [phase plan](../project-phases.md).

## Midnight contrast and navigation — 2026-09-15

M08 remains active. Repaired nested materials, provider, model, transcript and visual surfaces to use the selected palette. Added stronger active-section and course-card cues. Executed: synthetic Chromium rendering and 4.5:1 text contrast checks for eight affected surface/text pairs in both themes (`bun tests/desktop/theme-contrast.cjs`); inspected the Midnight rendering; frontend lint/typecheck and whitespace checks passed. Full accessibility and real-device qualification remain open. Next: dedicated account linking and API-key setup, then Phase 7; standalone Windows packaging after Phase 7, followed by macOS development, as requested by the user.

## Account linking evidence — 2026-09-15

Active phase: **6.8 / M08**. User sequencing is these usability repairs → Phase 7 → standalone Windows distribution → macOS. Existing Docker/PostgreSQL student data is unchanged; release gates remain open.

- Midnight contrast repair committed separately as `01251db`: nested materials/model/provider/transcript surfaces now follow the palette; selected sections are clearer.
- Accounts & API keys opens from the sidebar, the narrow-window top bar, or Note preferences. It is a modal over the workspace, so opening it does not navigate away or unmount recording.
- ChatGPT linking starts the official app-server browser flow, opens only an allowlisted provider HTTPS URL through Electron, verifies a paid account, and loads the provider model catalog. The pinned Codex 0.154.0 Windows helper is bundled with its license/notice; no executable chooser, password collection, token import, or model download is involved. Disconnect an existing ChatGPT connection before linking another account.
- OpenAI and Claude API setup needs only a key. Validation/model discovery precedes protected-storage replacement; model selection remains per lecture. The OpenAI picker filters out known non-chat model families; catalog availability does not prove successful inference for every listed model.
- Claude subscription linking is unavailable for new connections: Anthropic requires approval for third-party subscription login. Existing saved rows are preserved and can be disconnected. The requested all-model subscription access is not delivered: ChatGPT provides Codex-accessible models, and Claude needs provider approval.
- Connections retain CSRF, authenticated host requests, idempotency receipts, per-provider mutation exclusion and model-digest fencing. Failed key validation preserves a working key. Paid inference and real-account browser completion have not been exercised.

Executed checks: 60 JavaScript contracts; 10 desktop tests; 10 backend cloud/connection tests; Chromium account UI flows with synthetic API responses (key-only payload, sign-in payload, cleared key, Escape/focus restoration, 400px layout and actual Midnight materials rendering); eight affected text/background pairs pass 4.5:1 in each theme. Pinned helper initialize/account-read passed in a fresh signed-out profile after fixing required profile creation and process-exit cleanup. Typecheck, lint, production web build, Python lint, documentation checks, whitespace checks and frozen Bun install passed. The unsigned x64 NSIS installer was rebuilt under `.local/desktop-dist`; the packaged helper also passed its isolated signed-out protocol check. An initial pytest run hit existing temporary/cache-folder permissions; a fresh `.local` base/cache run passed.

Next: qualify real browser sign-in and authenticated note generation with user-owned accounts; do not claim that mocked tests qualify providers. Claude login requires a provider-approved integration. Then scope Phase 7.1 (emphasis, catch-up and terminology); standalone packaging follows Phase 7 and macOS follows Windows. Real microphone, educational quality, endurance, accessibility, clean install, upgrade and restore gates remain open.

## Subscription catalog/disconnect follow-up — 2026-09-15

Full exposed ChatGPT catalog pagination now includes hidden entries; users can inspect IDs and refresh the model list. Explicit ChatGPT/legacy Claude disconnect revokes Notetaker access even if provider-client logout fails, with a visible notice. Tests: 12 desktop and 10 backend cloud/connection checks, frontend typecheck/lint and Python lint passed. Provider API restrictions and live-account qualification remain open. User authorized Phase 7.1 next.

Follow-up browser verification (2026-09-15): actual React account controls passed with synthetic API responses for full-catalog refresh, visible added model IDs, ChatGPT disconnect and legacy Claude disconnect including an unconfirmed official-client logout notice. This is UI contract evidence, not live account qualification.
