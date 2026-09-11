# Session transfer

## Electron workspace and native retirement — 2026-09-11

Active phase remains **6.8 / M08**. The user reported that the application was difficult to navigate and visually janky, asked for a cleaner NotebookLM-inspired experience, and selected Electron as the only Windows host. The earlier Qt/native application and its standalone storage/packaging profile were removed from the repository. The existing Electron host, React workspace, FastAPI services and Docker development profile are now the single delivery path.

## Completed in this increment

- Added focused lecture navigation with persistent course and lecture links in the sidebar.
- Added lecture sections for Study notes, Transcript, Materials, Capture, Visual notes and Finish.
- Kept one recorder mounted while switching sections so a tab change cannot dispose an active recording.
- Added microphone input selection in the Electron renderer using the browser media-device API.
- Ported source-linked visual schematics into a safe React/SVG reader. Model labels are rendered as text nodes; arbitrary HTML and JavaScript are never executed.
- Added an Electron-only workspace-settings action that opens the existing local service/model setup window through a narrowly authorized IPC call.
- Hardened PowerShell 7 startup discovery so Electron checks PATH and standard machine/user install locations before launching Docker; missing PowerShell now produces a direct setup message instead of a raw spawn error.
- Moved Windows child-process ownership into `apps/api/notetaker/process_job.py` so subscription bridges do not depend on the removed native package.
- Removed the native Qt application, native tests, native dependency locks, native packaging scripts/workflow, native-only download/third-party documents and native evaluation reports.
- Updated the README, phase plan, desktop direction, M08 evidence and visual/provider evidence to describe Electron as the only Windows host.

## Existing behavior preserved

The shared React/API path still owns local audio journaling and recovery, live timestamped transcription, protected corrections, contextual streamed note sections, saved prompt profiles, source inspection/playback, course materials, model selection, revision comparison, keep/merge/replace/undo, finalization, immutable snapshots, deletion reconciliation, browser-copy purge and exports. The Electron host continues to reuse the existing loopback API and Docker service lifecycle. Existing development workspace data and service credentials are preserved; no migration or deletion of student data was performed.

Visual note data remains validated by the API. The Electron reader describes diagrams as cited explanatory schematics, not recovered slide/board images. OpenAI/Claude API and subscription connection code remains in the shared service scope and continues to require explicit per-lecture consent; live account/provider qualification is still open.

## Verification status

Executed in this increment:

- `bun run test`: 60 JavaScript contract/capture tests passed.
- `bun run test:desktop`: 3 Electron policy/model-discovery/startup-discovery tests passed.
- `node tests/desktop/smoke.cjs`: Electron isolation, setup, outage reporting, workspace reuse, model discovery, hide/reopen and synthetic journal checks passed.
- `bun run typecheck`, `bun run lint`, `bun run build:web`, `bun run verify:docs`, `uv run --no-project ruff check apps/api` and `git diff --check` passed.
- `PYTHONPATH=apps/api; uv run --no-project python -m pytest apps/api/tests -q --basetemp .local/pytest-run-0911`: 175 passed, 1 service-only skip.
- `bun run build:desktop`: unsigned x64 Electron NSIS installer built under `.local/desktop-dist`.
- Native files were removed only after checking their tracked paths and moving the one shared process-job dependency.

These checks use synthetic data/audio only. They do not qualify real microphone behavior, full-hour endurance, accessibility, educational usefulness, authenticated provider inference, coordinated backup/restore, clean-machine installation or release readiness.

## Environment and next work

Bun is the JavaScript runtime; uv manages Python. The development workspace runs with Docker Desktop Linux containers, PowerShell 7, a local Ollama service and the provisioned faster-whisper model. `bun run dev:desktop` opens the Electron shell after services are available. `bun run build:desktop` creates the unsigned Electron NSIS installer under `.local/desktop-dist`.

Next work after this commit: continue M08 clean-machine, upgrade, endurance, accessibility, restore and quality gates. Do not restore the removed native app or its workflow.
