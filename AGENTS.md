# Working on Notetaker

## Product

Build an installable Windows lecture companion for any subject. Capture lecture audio reliably, transcribe timestamped segments during recording, and continuously write detailed, source-linked study notes. Preserve explanations, definitions, worked examples, qualifications and professor emphasis. Accumulate enough transcript context before writing each note batch; show the model's text as it streams. Students control detail, layout and style through their own prompts, with saved profiles for reuse. The loopback workspace opens without an access key. Protect student edits, compare regeneration suggestions, support keep/merge/replace and undo, and export the selected saved revision.

Audio preservation is independent of inference. Never silently discard sources, overwrite student revisions, invent missing visual information, download models or fall back to external providers. A short summary is optional; detailed trustworthy notes are the priority.

## Read first and session workflow

1. Read [README.md](README.md), [project phases](docs/project-phases.md), and [SESSION_TRANSFER.md](SESSION_TRANSFER.md). The [consolidated specification](multimodal_academic_learning_system_spec.md) controls scope; latest user instructions control requested changes.
2. Inspect Git status and applicable instructions. Preserve unrelated work and existing student data.
3. State the active phase and intended user result. Build small increments spanning migrations, domain rules, API, UI and meaningful failure checks.
4. Use **Bun** for JavaScript dependencies and scripts and **uv** for Python environments, dependencies and commands. Do not introduce npm/pip workflows. Keep locks reproducible; use `bun install --frozen-lockfile` and `uv pip sync apps/api/requirements.lock` for existing environments.
5. Run appropriate tests, type checks, lint and build. Record executed evidence separately from planned or unavailable checks. Test synthetic audio only unless the user explicitly changes that preference; do not access the microphone.
6. Update implementation evidence, roadmap status and session transfer with changes, checks, remaining risks and exact next work. Locally commit each coherent increment with a short description; do not push unless requested.

## Stack and boundaries

The user selected a browser-free native Windows rebuild on 2026-09-09. For the Windows deliverable, use Qt Widgets/Qt Multimedia in `apps/native`, bundled Python/speech/CPU Ollama runtimes, and the explicit standalone SQLite/private-file storage profile. No Chromium, Electron or WebView engine is allowed in that package. Preserve the earlier PostgreSQL/Docker/React workspace as a separate development profile; do not silently migrate or delete its data. Model weights remain user-selected local files. The older stack bullets below describe that development profile.

- Next.js, React and strict TypeScript; accessible semantic HTML and existing CSS patterns.
- Browser AudioWorklet/worker capture, IndexedDB audio recovery and durable local edit drafts.
- Python/FastAPI modular backend; separate faster-whisper speech and Ollama note worker processes.
- SQLAlchemy/Alembic with PostgreSQL as authority. SQLite is an explicitly selected development/test preview.
- Private SeaweedFS audio objects; Kafka notifications plus database reconciliation/outbox. Docker Compose for local services.
- Windows desktop host and installer in M08, reusing UI/backend. Optional cloud providers belong to later Phase 7, with explicit user choice.

## Code style and correctness

Follow nearby conventions; prefer small domain-focused modules, explicit types and descriptive names. Avoid unrelated formatting changes or speculative infrastructure. Validate all external input. Keep authorization, CSRF, idempotency, ownership, expected-version writes and worker attempt/epoch fencing on new paths. Add additive migrations; never mutate immutable source/settings/note history. Preserve final snapshots when recovering late evidence; retain deletion tombstones and reconcile late object writes. Render arbitrary text safely, preserve code/equation whitespace, and label student changes and unvalidated streaming previews honestly. Keep secrets, model weights, generated caches and local lecture data out of Git.

## Testing and linting

- JavaScript contracts: `bun run test`.
- Backend: `uv run --no-project python -m pytest -q` with `PYTHONPATH=apps/api` (add `apps/api/tests` for browser tests; Windows separates entries with `;`).
- Frontend: `bun run typecheck`, `bun run lint`, `bun run build:web`.
- Python lint: `uv run --no-project ruff check apps/api` using the project configuration.
- Documentation: `bun run verify:docs`; whitespace: `git diff --check`.
- Exercise actual affected user flows and relevant failures; no tests that merely mirror trivial edits. Synthetic tests do not qualify microphone quality, educational usefulness, live hardware latency or release readiness.

## Phases

| Phase | Work |
| --- | --- |
| 1 | Product definition, audience, scope and quality gates. |
| 2 | Student experience, recovery flows and acceptance scenarios. |
| 3 | Architecture, data model, authorization and revision contracts. |
| 4 | AI pipeline, provenance and evaluation. |
| 5 | Consolidated specification and implementation roadmap. |
| 6.1 / M01 | Private local workspace, courses, lectures and service foundation. |
| 6.2 / M02 | Reliable recording, atomic recovery journal and verified audio saves. |
| 6.3 / M03 | Timestamped transcription, playback and protected corrections. |
| 6.4 / M04 | Automatic detailed notes, model choice, citations and export. |
| 6.5 / M05 | Live transcription, contextual note batches, streaming and reconnect. |
| 6.6 / M06 | Durable drafts, protected edits, settings snapshots, regeneration proposals, conflicts, keep/merge/replace and undo. Detail/format are custom prompts; do not restore redundant dropdowns. |
| 6.7 / M07 | Finalization, immutable final snapshots, retention and deletion reconciliation. |
| 6.8 / M08 | Windows host/installer, lifecycle, endurance, backup/restore and release gates. |
| 7.1 | Note usefulness: emphasis, catch-up and terminology. |
| 7.2 | Course materials and visual evidence when justified. |
| 7.3 | Learning tools, practice and personalization. |
| 7.4 | Measured scaling and infrastructure demonstrations. |

Keep one active implementation phase. Independent work may proceed with explicitly recorded earlier qualification gaps. “Implemented”, “verified on a named environment”, “complete” and “release-ready” are different claims. Consult the phase plan for full acceptance criteria and optional provider connections.
