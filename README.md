# Notetaker App

Notetaker is an installable Windows lecture companion for any subject. It captures lecture audio, builds a timestamped transcript, and continuously writes detailed, source-linked study notes that preserve definitions, explanations, worked examples, qualifications, and instructor emphasis.

The Windows deliverable is Electron-based. The React workspace runs inside a hardened Electron window, with FastAPI, speech, notes, PostgreSQL and SeaweedFS services. The standalone profile uses database reconciliation; the existing Docker development profile retains Kafka. The Qt application has been removed.

![Notetaker logo](docs/assets/notetaker-logo.svg)

## Windows app

The Electron app creates a normal Windows window and Start menu entry. The standalone build bundles its web server, Python services, PostgreSQL, audio storage and CPU Ollama runtime without requiring separate Docker, Python, Node or PowerShell 7 installations. Users still select existing local note and faster-whisper models. The existing Docker profile remains available. The app never downloads model weights or silently sends lecture audio to an external provider.

The workspace is organized around a course sidebar and lecture sections: Study notes, Transcript, Materials, Capture, Visual notes, Study tools, and Finish. Recording stays alive while moving between sections. Saved audio, transcript passages, source links, protected edits, regeneration proposals, final snapshots, recovery, deletion, exports, prompt profiles, and local/cloud model choices remain part of the same lecture workflow.

The Theme selector offers Slate, Midnight, Pink and Blue, with rounded translucent surfaces and smooth tab transitions that respect reduced-motion preferences. Installed local display fonts style the interface while note and transcript content retain their reading font. See [appearance and delivery status](docs/implementation/workspace-appearance.md).

### Install and start

1. Use the local unsigned x64 standalone installer described in the [Windows distribution guide](docs/implementation/windows-standalone.md). This increment has not been published to GitHub releases; older installers retain Docker prerequisites.
2. Open Notetaker from the Start menu. On first launch, choose **Create or open standalone library** or **Use existing workspace folder**. The standalone library is separate and leaves existing Docker data intact.
3. Setup is shown on first launch or when startup needs attention. Returning users see a themed loading animation while their saved library starts automatically; **Workspace settings** reopens setup. Choose an existing speech-model folder (the selector offers discovered local models), start services and select **Open workspace**, then choose an installed local note model in the lecture’s note settings. Models are never downloaded by Notetaker. Restart standalone services after changing the speech folder.
4. Create a course and lecture. In **Note preferences**, keep the local model or open **Accounts & API keys** to link ChatGPT or paste an OpenAI/Claude API key if desired. Cloud choices require an explicit confirmation for each lecture.
5. In **Capture**, choose the recording input and press **Start recording**. Capture and confirmed-save progress are shown separately.
6. While recording, **Study notes** shows a fixed-height live transcript directly above the notes, with automatic scrolling and model-identified important ideas highlighted in the selected theme. Open **Transcript** for full passages, playback and corrections. Note drafts stream after enough transcript context accumulates. A missing speech model is shown in the lecture status; use **Select speech model** or **How to get a model** and restart services after finishing recording. The Windows standalone status confirms when the speech worker has loaded the model. Stop recording when the lecture ends; local processing continues over remaining saved audio.
7. Review the transcript, notes, visual schematics and source evidence. Make protected edits or compare a regenerated suggestion, then use the prominent **Export Markdown** control for the selected saved revision or final snapshot. **More formats** offers Word, study slides, plain text and HTML (printable to PDF). The adjacent guide includes a study prompt you can copy.

The installer is a development distribution, not a release-ready offline bundle. It retains app data on uninstall. Real-device recording, accessibility, long-duration endurance, coordinated backup/restore, upgrade testing, signing and human note-quality review remain open qualification work. Use synthetic audio for engineering checks unless physical microphone testing is explicitly authorized.

The existing Docker profile still requires Docker Desktop's Linux engine and PowerShell 7. If that profile reports “PowerShell 7 was not found”, install PowerShell 7 and restart Notetaker.

## Current phase

The active delivery phase is **6.8 / M08 — Standalone Windows distribution**. The [standalone increment](docs/implementation/windows-standalone.md) bundles the web and native services with explicit separate-library selection and preserved Docker support. Phase 7.4's [PostgreSQL contention experiment](docs/implementation/phase-7-4.md) remains deferred. Study tools retains source-linked recall cards, generated questions/flashcards, protected edits and self-assessments; [human question quality and learning outcomes](docs/ai/phase-7-3-learning-evaluation.md) remain open. Earlier [M08 qualification gaps](docs/implementation/phase-6-m08.md) remain open; see the [phase plan](docs/project-phases.md) and [desktop direction](docs/architecture/windows-desktop-direction.md).

The product priority is reliable lecture capture → timestamped transcription → high-quality, source-linked notes. Course materials, source-linked visual schematics, saved prompt profiles, protected editing, finalization, deletion reconciliation and the local Electron service lifecycle are included. The Accounts & API keys panel supports OpenAI/Claude API keys and browser-based ChatGPT linking through a bundled official Codex helper. API keys load supported text models; ChatGPT exposes the Codex model catalog for an eligible paid account, not every model on the ChatGPT website. Claude subscription linking requires Anthropic approval and is unavailable for new connections. All cloud models remain explicitly chosen per lecture; live account/inference qualification is still open. The bridge uses Windows protected storage and a separate client profile; it does not collect passwords or import another app’s tokens.

Run the development profile with Docker Desktop's Linux engine:

```powershell
pwsh -File scripts/Provision-Speech.ps1
pwsh -File scripts/Start-App.ps1 -WithSpeech
```

Then open `http://127.0.0.1:3000`, or launch the desktop shell with `bun run dev:desktop` after the local services are running. Existing courses and lectures are preserved. The workspace opens locally without an access key.

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

The backend defaults to isolated SQLite tests; service checks use temporary PostgreSQL schemas. Synthetic checks do not establish microphone quality, educational usefulness, live-provider compatibility, or release readiness. Keep student data, credentials, model weights and generated caches out of Git.
