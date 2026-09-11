# Notetaker App

Notetaker is an installable Windows lecture companion for any subject. It captures lecture audio, builds a timestamped transcript, and continuously writes detailed, source-linked study notes that preserve definitions, explanations, worked examples, qualifications, and instructor emphasis.

The Windows deliverable is Electron-based. The React workspace runs inside a hardened Electron window, while the existing FastAPI, speech, notes, PostgreSQL, SeaweedFS and Kafka services continue to own persistence and background processing. The native Qt application has been removed; there is one supported desktop path.

![Notetaker logo](docs/assets/notetaker-logo.svg)

## Windows app

The Electron app creates a normal Windows window and Start menu entry. Its setup screen starts or reconnects to the local services, discovers local models, and keeps service configuration outside the install directory. The first-use distribution requires Docker Desktop with Linux containers, PowerShell 7, Ollama for note generation, and a local faster-whisper model for speech. The app never downloads model weights or silently sends lecture audio to an external provider.

The workspace is organized around a course sidebar and lecture sections: Study notes, Transcript, Materials, Capture, Visual notes, and Finish. Recording stays alive while moving between sections. Saved audio, transcript passages, source links, protected edits, regeneration proposals, final snapshots, recovery, deletion, exports, prompt profiles, and local/cloud model choices remain part of the same lecture workflow.

### Install and start

1. Download the latest unsigned x64 Electron installer from the [GitHub releases page](https://github.com/akulusprimerift/Notetaker-App/releases/latest).
2. Open Notetaker from the Start menu. On first launch, choose **Create new desktop library** or **Use existing workspace folder** to reuse the existing development library and its service configuration.
3. Start the local services from setup, then choose a local note model in the lecture’s note settings. Models are selected from the computer; they are not downloaded by Notetaker.
4. Create a course and lecture. In **Note preferences**, keep the local model or connect an API provider/official subscription client if desired. Cloud choices require an explicit confirmation for each lecture.
5. In **Capture**, choose the recording input and press **Start recording**. Capture and confirmed-save progress are shown separately.
6. Stop recording when the lecture ends. Transcription and detailed note sections continue through the local workers; earlier saved notes remain available if a later attempt needs attention.
7. Review the transcript, notes, visual schematics and source evidence. Make protected edits or compare a regenerated suggestion, then export the selected revision or final snapshot.

The installer is a development distribution, not a release-ready offline bundle. It retains app data on uninstall. Real-device recording, accessibility, long-duration endurance, coordinated backup/restore, upgrade testing, signing and human note-quality review remain open qualification work. Use synthetic audio for engineering checks unless physical microphone testing is explicitly authorized.

If setup reports “PowerShell 7 was not found”, install PowerShell 7 from Microsoft, restart Notetaker, and start the services again. Windows PowerShell 5.1 is a separate product and is not sufficient for the service startup scripts.

## Current phase

The active implementation phase is **6.8 / M08 — Electron Windows application**. See the [feature and architecture phase plan](docs/project-phases.md), [M08 evidence](docs/implementation/phase-6-m08.md), and [desktop direction](docs/architecture/windows-desktop-direction.md).

The product priority is reliable lecture capture → timestamped transcription → high-quality, source-linked notes. Course materials, source-linked visual schematics, saved prompt profiles, protected editing, finalization, deletion reconciliation and the local Electron service lifecycle are included. OpenAI/Claude API and subscription connections are available through the Electron host bridge, remain explicitly chosen per lecture and are still subject to provider/account qualification. The bridge uses Windows protected storage and official provider clients; it does not collect passwords or import another app’s tokens.

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
