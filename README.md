# Notetaker App

Notetaker is an installable Windows lecture companion for any subject. It captures lecture audio, builds a timestamped transcript, and continuously writes detailed, source-linked study notes that preserve definitions, explanations, worked examples, qualifications, and instructor emphasis.

The Windows deliverable is Electron-based. The React workspace runs inside a hardened Electron window, with bundled FastAPI, speech and note workers. SQLite stores the library; verified audio files are kept beside it. Workers recover from the saved job queue. Docker, PostgreSQL, Kafka and SeaweedFS have been removed from the delivery path. The Qt application has been removed.

![Notetaker logo](docs/assets/notetaker-logo.svg)

## Windows app

The Electron app creates a normal Windows window and Start menu entry. The standalone build bundles its web server, Python services, SQLite and CPU Ollama runtime without requiring separate Docker, Python, Node or PowerShell 7 installations. Users still select existing local note and faster-whisper models. The app never downloads model weights or silently sends lecture audio to an external provider.

The workspace keeps the course library in a sidebar and recording controls in a persistent header. Choose a course and lecture from **Record** before starting; controls and save status remain visible as you move between the library, course, and lecture. **Notes** and **Finish** are the main lecture sections. Transcript, Capture, Materials, Visual notes, and Study tools sit in quieter side navigation. Notes remain the reading focus with a compact transcript preview; full transcript, audio recovery, source review, protected edits, exports, finalization, and data removal remain available in their lecture sections. See the [workspace layout and recording evidence](docs/implementation/workspace-layout-recording.md).

The Theme selector offers Slate, Midnight, Pink and Blue, with prominent glass surfaces, animated navigation and gradient loading progress that respect reduced-motion preferences. Saved notes flow through fixed-height numbered sections with sideways swipe/scroll and keyboard navigation. The Windows controls share the workspace header and the library sidebar slides open and closed. See [paged notes and motion delivery status](docs/implementation/paged-notes-and-motion.md); the updated unsigned Windows installer is available with packaged synthetic verification. Installed local display fonts style the interface while note and transcript content retain their reading font. See [appearance and delivery status](docs/implementation/workspace-appearance.md).

### Install and start

1. Use the local unsigned x64 standalone installer described in the [Windows distribution guide](docs/implementation/windows-standalone.md). Use a newly built SQLite installer; earlier PostgreSQL installers and Mac releases do not contain this change.
2. Open Notetaker from the Start menu. On first launch, choose **Create or open standalone library** or **Choose an existing SQLite library**. The default is `sqlite-library` in the app data folder. Earlier libraries require [explicit conversion](docs/implementation/sqlite-standalone.md); conversion copies records and verified audio into a separate folder and keeps the original intact.
3. Setup is shown on first launch or when startup needs attention. Returning users see a themed loading animation while their saved library starts automatically; **Workspace settings** reopens setup. Choose an existing speech-model folder (the selector offers discovered local models), start services and select **Open workspace**, then choose an installed local note model in the lecture’s note settings. Models are never downloaded by Notetaker. Restart standalone services after changing the speech folder.
4. Create a course and lecture. In **Note preferences**, keep the local model or open **Accounts & API keys** to link ChatGPT or paste an OpenAI/Claude API key if desired. Cloud choices require an explicit confirmation for each lecture.
5. In the persistent **Record** bar, choose the course and lecture, choose the recording input, and press **Start recording**. Capture and confirmed-save progress remain visible while you navigate. Open **Capture** from the lecture side navigation for recovery actions and saved segments.
6. While recording, **Notes** keeps the saved notes in focus with a compact live transcript preview. Open **Transcript** for full passages, playback and corrections. Note drafts stream after enough transcript context accumulates. A missing speech model is shown in the lecture status; use **Select speech model** or **How to get a model** and restart services after finishing recording. The Windows standalone status confirms when the speech worker has loaded the model. Stop recording when the lecture ends; local processing continues over remaining saved audio.
7. Review the transcript, notes, visual schematics and source evidence. Make protected edits or compare a regenerated suggestion, then use the prominent **Export Markdown** control for the selected saved revision or final snapshot. **More formats** offers Word, study slides, plain text and HTML (printable to PDF). The adjacent guide includes a study prompt you can copy.

The installer is a development distribution, not a release-ready offline bundle. It retains app data on uninstall. Real-device recording, accessibility, long-duration endurance, coordinated backup/restore, upgrade testing, signing and human note-quality review remain open qualification work. Use synthetic audio for engineering checks unless physical microphone testing is explicitly authorized.

## Current phase

The active development phase remains **6.9.5 — Mac installer and distribution**, with the user-requested [SQLite standalone switch](docs/implementation/sqlite-standalone.md) taking priority on 2026-10-05. Earlier distribution evidence below describes PostgreSQL builds and does not qualify the new SQLite Mac runtime. Tagged GitHub builds publish an Apple Silicon DMG, Developer ID signed and notarized when signing secrets are configured ([distribution](docs/implementation/macos-distribution.md)). The user reported the 6.9.4 test build working on their Mac. A cross-platform [workflow harness](docs/implementation/macos-workflow.md) exercises the full synthetic lecture workflow and records performance; it passes on the Windows standalone runtime, and native Mac runs remain next. Earlier priority repairs: [live transcription and audio storage](docs/implementation/live-transcription-storage.md) and [speed and restart](docs/implementation/live-speed-restart.md). Mac milestone **6.9.3 — macOS integration** remains open, targeting Apple Silicon through the shared Electron/React/FastAPI application. [Mac integration](docs/implementation/macos-integration.md) adds native menus, window/Dock behavior, microphone denial recovery and sleep/wake recording interruptions, using existing protected credential storage. Shared code is checked on Windows; actual Mac permission, Keychain, lifecycle and earlier runtime-build qualification remain open. The [Mac build guide](docs/implementation/macos-standalone.md) retains the required arm64 preparation steps. The user accepts Windows as finished for the current development scope; earlier Windows release and human-quality gaps remain recorded. See the [phase plan](docs/project-phases.md) and [session transfer](SESSION_TRANSFER.md).

The product priority is reliable lecture capture → timestamped transcription → high-quality, source-linked notes. Course materials, source-linked visual schematics, saved prompt profiles, protected editing, finalization, deletion reconciliation and the local Electron service lifecycle are included. The Accounts & API keys panel supports OpenAI/Claude API keys and browser-based ChatGPT linking through a bundled official Codex helper. API keys load supported text models; ChatGPT exposes the Codex model catalog for an eligible paid account, not every model on the ChatGPT website. Claude subscription linking requires Anthropic approval and is unavailable for new connections. All cloud models remain explicitly chosen per lecture; live account/inference qualification is still open. The bridge uses Windows protected storage and a separate client profile; it does not collect passwords or import another app’s tokens.

For development, create a locked uv environment and install JavaScript dependencies with Bun. Use the [standalone build instructions](docs/implementation/sqlite-standalone.md), or run `scripts/Start-Preview.ps1` for an isolated SQLite UI preview. The preview does not launch inference workers. The workspace opens locally without an access key.

## Project references

- [Consolidated product and technical specification](multimodal_academic_learning_system_spec.md)
- [Implementation roadmap and acceptance cases](docs/implementation/phase-5-roadmap.md)
- [Materials evidence](docs/implementation/course-materials.md)
- [Visual notes and provider limitations](docs/implementation/visual-notes-providers.md)
- [M07 finalization and data control](docs/implementation/phase-6-m07.md)
- [M06 editing, streaming and regeneration](docs/implementation/phase-6-m06.md)
- [Session transfer](SESSION_TRANSFER.md)
- [Working instructions](AGENTS.md)

Earlier phase documents retain the product-design and architecture decisions that led to the current implementation. Practice generation, mastery tracking and advanced infrastructure demonstrations follow validation of the core note-taking experience.

## Checks

Use **Bun** for JavaScript and **uv** for Python. Install dependencies with `bun install --frozen-lockfile --ignore-scripts` and use the existing uv-managed environment for backend checks.

```powershell
bun run test
bun run test:desktop
bun run typecheck
bun run lint
bun run build:web
bun run verify:docs
uv run --no-project ruff check apps/api
$env:PYTHONPATH='apps/api'; uv run --no-project python -m pytest apps/api/tests -q
git diff --check
```

All backend tests use isolated SQLite libraries. Packaged checks create fresh SQLite folders and synthetic audio. Synthetic checks do not establish microphone quality, educational usefulness, live-provider compatibility, or release readiness. Keep student data, credentials, model weights and generated caches out of Git.
