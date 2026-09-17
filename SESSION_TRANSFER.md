# Session transfer

## Phase 7.3 — 2026-09-16

Active phase: **7.3 — Learning tools**, explicitly selected by the user, followed by standalone Windows distribution. Phase 7.2/7.4 are not prerequisites. Earlier phase entries below are historical; earlier quality/release gaps remain open.

First learning increment implemented: Study tools → Recall practice offers topic recall cards from complete saved note sections, optional temporary practice answers, reveal/source inspection, persistent self-assessments/reset and topic/review filters. It respects selected student edits, excludes complete blocks with changed/unsupported/visual evidence, reports source warnings, and starts fresh ratings for new note revisions. No generated question-quality or objective mastery claim. See [behavior, evidence and next work](docs/implementation/phase-7-3.md).

Migration 0016 adds append-only learning reviews. Writes retain ownership, CSRF, idempotency, expected-version and lecture/tombstone fences. Deletion removes review history. Existing student data was not migrated or changed, no model/provider was invoked, and no microphone or installed app was used.

Executed: full backend **189 passed, 1 service-only skip**; subsequent focused **5 learning tests passed**, including the newly added upgrade-from-0015 preservation case and unauthenticated access check. **60** JavaScript contracts, **12** desktop tests; Chromium learning/previous study flows with synthetic responses, retry identity, source reveal, persisted ratings, filters, conflicts/reset, Midnight and narrow layout; typecheck, frontend/Python lint, production web build, documentation and whitespace checks passed. The first mixed-evidence fixture needed a deep copy before SQLAlchemy would persist its synthetic data; fixed and rerun successfully.

Next: distinct source-validated questions/individual flashcards through the selected model, protected generated learning content, and human question-quality/learning-state evaluation. Then standalone Windows runtime/service distribution and explicit existing-library preservation. Keep the current Docker library intact and models user-selected. The prior unsigned installer has not been rebuilt for this increment and still needs Docker/PowerShell/Ollama/local speech files. No push or installation performed. Human note/learning quality, live provider inference and M08 hardware, accessibility, endurance, clean-install/upgrade and restore qualification remain open. macOS follows Windows.

## Phase 7.1 — 2026-09-15

Implementation committed as `6c1a660`; provider follow-up `47c5b9f` and browser controls verification `6e62d35`. The unsigned x64 installer was rebuilt successfully at `.local/desktop-dist/Notetaker-0.1.0-Setup.exe` (202,452,730 bytes; SHA-256 `0A675FB8437759780B6B594EEE0AE42431FA0AFD7F779B5793FD81E5E6C8C7EB`). Packaged study/terminology modules, both migrations, UI components and provider controls match working-source hashes. This checks packaging contents, not clean installation, upgrade or a running installed workflow. The installer retains the existing Docker/local-model prerequisites. No push or installation was performed.

Active phase: **7.1 — Note usefulness**. The user requested full subscription model access and disconnect before starting this phase. Commit `47c5b9f` includes all exposed Codex catalog pages/hidden models, model-list refresh, and reliable ChatGPT/legacy Claude disconnect. Provider limits remain explicit: the consumer ChatGPT menu is not available in full; new Claude subscription login requires Anthropic approval. No live account/inference qualification was performed.

Phase 7.1 implements Mark Important, source-linked Catch Me Up, and course terminology hints. See [implementation and evidence](docs/implementation/phase-7-1.md). Additive migrations 0014/0015 are included; existing student data was not touched. Marks freeze into final snapshots; source corrections and selected student note edits are respected by catch-up. Term versions are pinned to future speech windows and passed as hints to the local speech adapter, never treated as independent source evidence. Draft conflict comparison, marker retry, removal and undo are visible.

Executed so far: backend **185 passed, 1 skipped** on SQLite; **60** JavaScript contracts and **12** desktop tests; new Chromium study UI flow including Midnight and narrow layout, marker failure/retry, source inspection, removal/undo and terminology conflict preservation; typecheck, frontend lint and Python lint. Only synthetic audio/data were used. Final production web build, documentation and whitespace checks passed; the nine focused backend tests passed again after the final source-order/boundary adjustment. The skipped backend test requires real PostgreSQL/object services. Account browser refresh/disconnect checks are committed as `6e62d35`.

Remaining: human usefulness and real-speech terminology evaluation, live provider entitlement/inference, and prior M08 microphone, accessibility, endurance, clean-install/upgrade and restore gates. Phase 7.2 has not started. Standalone Windows distribution follows selected Phase 7 work; macOS follows Windows.

## Account linking and theme repair — 2026-09-15

Active phase: **6.8 / M08**. User sequencing is these usability repairs → Phase 7 → standalone Windows distribution → macOS. Existing Docker/PostgreSQL student data is unchanged; release gates remain open.

- Midnight contrast repair committed separately as `01251db`: nested materials/model/provider/transcript surfaces now follow the palette; selected sections are clearer.
- Accounts & API keys opens from the sidebar, the narrow-window top bar, or Note preferences. It is a modal over the workspace, so opening it does not navigate away or unmount recording.
- ChatGPT linking starts the official app-server browser flow, opens only an allowlisted provider HTTPS URL through Electron, verifies a paid account, and loads the provider model catalog. The pinned Codex 0.154.0 Windows helper is bundled with its license/notice; no executable chooser, password collection, token import, or model download is involved. Disconnect an existing ChatGPT connection before linking another account.
- OpenAI and Claude API setup needs only a key. Validation/model discovery precedes protected-storage replacement; model selection remains per lecture. The OpenAI picker filters out known non-chat model families; catalog availability does not prove successful inference for every listed model.
- Claude subscription linking is unavailable for new connections: Anthropic requires approval for third-party subscription login. Existing saved rows are preserved and can be disconnected. The requested all-model subscription access is not delivered: ChatGPT provides Codex-accessible models, and Claude needs provider approval.
- Connections retain CSRF, authenticated host requests, idempotency receipts, per-provider mutation exclusion and model-digest fencing. Failed key validation preserves a working key. Paid inference and real-account browser completion have not been exercised.

Executed checks: 60 JavaScript contracts; 10 desktop tests; 10 backend cloud/connection tests; Chromium account UI flows with synthetic API responses (key-only payload, sign-in payload, cleared key, Escape/focus restoration, 400px layout and actual Midnight materials rendering); eight affected text/background pairs pass 4.5:1 in each theme. Pinned helper initialize/account-read passed in a fresh signed-out profile after fixing required profile creation and process-exit cleanup. Typecheck, lint, production web build, Python lint, documentation checks, whitespace checks and frozen Bun install passed. The unsigned x64 NSIS installer was rebuilt under `.local/desktop-dist`; the packaged helper also passed its isolated signed-out protocol check. An initial pytest run hit existing temporary/cache-folder permissions; a fresh `.local` base/cache run passed.

Next: qualify real browser sign-in and authenticated note generation with user-owned accounts; do not claim that mocked tests qualify providers. Claude login requires a provider-approved integration. Then scope Phase 7.1 (emphasis, catch-up and terminology); standalone packaging follows Phase 7 and macOS follows Windows. Real microphone, educational quality, endurance, accessibility, clean install, upgrade and restore gates remain open.

## Electron workspace and provider/materials usability — 2026-09-11

Active phase remains **6.8 / M08**. The user reported that the application was difficult to navigate and visually janky, asked for a cleaner NotebookLM-inspired experience, and selected Electron as the only Windows host. The earlier Qt/native application and its standalone storage/packaging profile were removed from the repository. The existing Electron host, React workspace, FastAPI services and Docker development profile are now the single delivery path.

## Completed in this increment

- Fixed local note-model discovery: supported Ollama families now include Gemma and other common local text models instead of silently limiting the chooser to Qwen.
- Added visible model-list status, refresh feedback, local/provider grouping and explicit per-lecture cloud-processing consent in Note preferences.
- Added an Electron-host provider bridge and Note preferences connection UI for OpenAI API, Claude API, ChatGPT subscription through Codex and Claude subscription through Claude Code. Connection files use Electron Windows protected storage; the Docker services receive only authenticated bridge requests and never store provider secrets.
- Added official-client selection, sign-in, sign-out and disconnect actions without collecting provider passwords or extracting another app's tokens.
- Replaced the materials upload row with a spaced two-step source card, explicit save action, selected-file review, file-size feedback and readable saved-material previews.
- Removed the Electron application menu bar containing Notetaker, Edit and View. Workspace settings remain available from the in-app button.

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

Visual note data remains validated by the API. The Electron reader describes diagrams as cited explanatory schematics, not recovered slide/board images. OpenAI/Claude API and subscription connections now run through the Electron host bridge and still require explicit per-lecture consent; live account/provider qualification is still open.

## Verification status

Executed in this increment:

- `bun run test`: 60 JavaScript contract/capture tests passed.
- `bun run test:desktop`: 4 Electron policy/model-discovery/startup-discovery/provider-bridge tests passed.
- `node tests/desktop/smoke.cjs`: Electron isolation, setup, outage reporting, workspace reuse, model discovery, hide/reopen and synthetic journal checks passed.
- `bun run typecheck`, `bun run lint`, `bun run build:web`, `bun run verify:docs`, `uv run --no-project ruff check apps/api` and `git diff --check` passed.
- `PYTHONPATH=apps/api; uv run --no-project python -m pytest apps/api/tests -q --basetemp .local/pytest-run-0911`: the fresh full run reached 174 passed and 1 service-only skip, with one pre-existing SQLite note-edit case failing once; that exact test passed in an isolated rerun. An earlier fresh full run reached 175 passed and 1 skip.
- `bun run build:desktop`: unsigned x64 Electron NSIS installer built under `.local/desktop-dist`.
- `bun run build:web` and the updated production renderer compiled with the materials/provider changes.
- Native files were removed only after checking their tracked paths and moving the one shared process-job dependency.

These checks use synthetic data/audio only. The provider bridge test uses a protected-storage test double and no live credentials. They do not qualify real microphone behavior, full-hour endurance, accessibility, educational usefulness, authenticated provider inference, coordinated backup/restore, clean-machine installation or release readiness.

## Environment and next work

Bun is the JavaScript runtime; uv manages Python. The development workspace runs with Docker Desktop Linux containers, PowerShell 7, a local Ollama service and the provisioned faster-whisper model. `bun run dev:desktop` opens the Electron shell after services are available. `bun run build:desktop` creates the unsigned Electron NSIS installer under `.local/desktop-dist`.

Next work after this commit: restart the Docker profile from Electron so existing service containers receive the provider-bridge settings, then continue M08 clean-machine, upgrade, endurance, accessibility, restore and live-provider qualification gates. Do not restore the removed native app or its workflow.

## Current priority — 2026-09-15

Active phase: M08 usability repairs. Midnight nested surfaces now use theme colors, with clearer selected lecture sections. Synthetic Chromium checks passed eight affected text/background pairs at 4.5:1 in both themes; Midnight image inspected; lint/typecheck passed. Next: finish dedicated account linking and API-key setup. User sequencing: these fixes → Phase 7 → standalone Windows app → macOS. Prior release qualification gaps remain open.

## Subscription catalog and disconnect follow-up — 2026-09-15

Before Phase 7.1, subscription discovery now requests hidden as well as default-visible models on every provider catalog page. Connected accounts expose their model IDs and an explicit Refresh models action. Refresh keeps the credential digest stable but prevents choosing removed models. Both ChatGPT and legacy Claude subscription connections disconnect locally even when the client cannot confirm logout; the UI reports that distinction. This does not cancel the provider subscription or delete lecture notes.

Executed: 12 desktop tests (including hidden/paginated catalog, refresh and missing-client disconnect), 10 backend cloud/connection tests including authenticated refresh and disconnect notice, frontend typecheck/lint and Python lint. Full consumer-website catalogs and live model entitlement cannot be guaranteed by these APIs; the documented Claude approval limitation remains. Next active implementation: Phase 7.1.
