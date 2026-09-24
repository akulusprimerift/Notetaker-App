# Session transfer

## Startup and exports — 2026-09-24

Active phase remains **6.8 / M08**. Implemented themed automatic startup/recovery, guided setup, native theme-colored Windows controls, a persisted sidebar toggle, Slate glass surfaces, prominent Markdown export, a study-use guide/copyable prompt, and Word/PPTX/plain-text/HTML choices for saved revisions and final snapshots. No student data, model downloads, microphone or provider calls. See [behavior and executed evidence](docs/implementation/startup-and-exports.md).

Executed: 60 contracts, 21 desktop tests, full backend 245 passed/1 service-only skip followed by 9 final focused export tests; actual Chromium appearance/sidebar/recorder, setup/loading/recovery/help, four-theme contrast and existing live-note/draft flows; frontend typecheck/lint/build and Python lint. Installer built: `.local/startup-export/installer/Notetaker-0.1.0-Windows-Standalone-Setup.exe`, **407,266,757 bytes**, SHA-256 `035508E527CCB4567231D712409CD818E99D991FEFAD1D3BAB3B43B0913B4772`. The packaged app passed native overlay/dragging, separate-library startup, synthetic audio save/Quit/automatic reopen/readback, theme persistence and DOCX/PPTX/TXT final-snapshot downloads. Exported Office files reopened successfully. A final setup-button contrast correction passed four-theme Chromium checks and was repackaged; packaged desktop files match source. The final full repeat correctly refused port 3000 because the installed user app was running; its isolated test was stopped without touching the installed app. See linked evidence for exact limits and profiles. Source commit: `ca90cd7`. Next: close the installed app normally, install this unsigned build retaining the library selection, and qualify the installed upgrade. Earlier installed-upgrade, Office rendering, hardware, human-quality and release gates remain open.


## Appearance installer delivered — 2026-09-24

Active phase remains **6.8 / M08**. The Pink/Blue glass UI, geometric headings, spacing and navigation animations are packaged into `.local/appearance-package/installer/Notetaker-0.1.0-Windows-Standalone-Setup.exe` (**397,878,582 bytes**; SHA-256 `8E6AA9B2FFF8636E67B881EA801B3CFAD34E31785E330E77C8FFE8A75EB2D7CA`). [Full packaging evidence](docs/implementation/workspace-appearance.md#installer-delivery--2026-09-24). The installer is unsigned and has not been automatically installed.

The standalone renderer was freshly built; all 4,957 unchanged native files from the previously verified runtime were hash-checked before/after staging. Production-bundle hydration/assets/hash checks, production appearance and existing live-note/transcript browser flows, **60 contracts**, **18 desktop tests**, documentation/whitespace and installer build passed. Actual packaged Electron passed isolated library startup, synthetic verified audio save, Quit/reopen and identical readback, renderer isolation, Blue persistence and Pink selection. Profile: `.local/standalone-smoke-c066b215-fbea-4098-a8a6-e773444cd4d4`. A Bun constant-folding issue in the test's isolation callback was corrected before the successful rerun; app security was unchanged.

No microphone, student-library access, backend/inference change, font/model download, automatic installation or push. Next: close the existing app, install the new build retaining its library selection, and qualify the installed upgrade. Earlier hardware, human quality, endurance, backup/restore and release gates remain open. Implementation commits are `bf4ce96`, `e708588`, `dfc51db`; delivery evidence/test changes are committed in this packaging increment.

## Blue theme checked before packaging — 2026-09-24

Active phase remains **6.8 / M08**. Blue uses the latest geometric typography, glass surfaces, spacing and animations. Fixed primary-button hover contrast and matched native choice-control accents. Expanded synthetic browser checks pass all seven lecture sections at 1440px/400px plus course/account dialogs, Blue hover contrast and existing appearance checks. Four-theme contrast, lint/typecheck, production build and documentation/whitespace pass. [Evidence and fixture corrections](docs/implementation/workspace-appearance.md). No note/transcript behavior, student data or installed app was changed. Next: package the updated renderer with the existing standalone runtime and qualify installed upgrade; installer has not yet been rebuilt.

## Appearance refinement after review — 2026-09-24

Active phase remains **6.8 / M08**. Replaced the rejected Wayfinder heading with local TikTok Sans; increased glass transparency, highlight edges and spacing; simplified lecture tab labels and added a responsive sliding selection highlight plus library/course/lecture entrance animation. Reduced-motion behavior and recorder ownership are preserved. No inference, transcript, note-editing or data changes. See [current appearance evidence](docs/implementation/workspace-appearance.md).

Executed: Chromium appearance/font/persistence/400px/animation/recorder checks, 32 focused contrast pairs, existing live transcript/note flows, frontend lint/typecheck/build and documentation/whitespace. Installer remains unchanged; next delivery step is packaging the renderer with the existing standalone runtime and qualifying the installed upgrade. No microphone, student-library access or push.

## Workspace appearance — 2026-09-24

Active phase remains **6.8 / M08**. Added persisted Pink/Blue palettes, locally installed Wayfinder/Lemon Milk typography with a geometric supporting face, rounded translucent surfaces and directional tab slides with reduced-motion support. Note/transcript content fonts, inference, recording and student revision behavior are preserved. See [scope and verification](docs/implementation/workspace-appearance.md).

Executed: **60 JavaScript contracts**, **18 desktop tests**, actual Chromium appearance and existing live transcript/note flows, 32 focused contrast pairs across four themes, frontend typecheck/lint and production web build, documentation and whitespace checks. Screenshots are under `.local/appearance-review`. No backend changes, student-data access, microphone, provider calls, font redistribution, installation or push. Installer not rebuilt; next delivery step is packaging the new renderer with the existing standalone runtime and qualifying the installed upgrade. Earlier release gates remain open.

## Live notes and lecture deletion — 2026-09-23

Active phase remains **6.8 / M08**. Notes now automatically display new saved generated revisions; the desktop provider bridge forwards incremental text instead of buffering complete cloud responses. Existing student revisions and unsaved drafts remain protected. Worth reviewing stays dismissed per lecture across revisions/reloads until reopened. The lecture header opens the existing deletion confirmation, with sidebar cleanup and navigation from all lecture tabs fixed. See [behavior, executed checks and delivery](docs/implementation/live-notes-usability.md).

Executed: existing backend suite **233 passed, 1 skip**, plus **4 new bridge tests**; **60 JavaScript contracts**, **18 desktop tests**, synthetic Chromium flows, typecheck, frontend/Python lint and production standalone web build. No microphone, model downloads, live cloud inference, installed-library modifications or push. The rebuilt packaged app also passed isolated synthetic audio save, Quit/reopen and identical readback with renderer isolation enabled. Installer: `.local/notes-fix/installer/Notetaker-0.1.0-Windows-Standalone-Setup.exe` (397,873,440 bytes; SHA-256 `8C4808EC2A7E66A7E6833A3D9EC60E180B7EF46AAAE1D9D69AB3CB8CBC729157`). Source commit: `7dbce42`. Next: close the installed app, install this build with the existing library selection, and qualify actual connected-provider streaming and existing-library upgrade; retain earlier human-quality/hardware/release gaps. No automatic installation performed.

## Speech workspace usability — 2026-09-23

Active phase remains **6.8 / M08**. Removed the manual Mark Important control while retaining prior bookmarks; new note generation infers contextual emphasis and renders it bold in theme colors. A fixed-height, automatically scrolling transcript preview sits directly above the note content; the dedicated Transcript tab remains. The recorder stays mounted across tab changes and help. Speech setup now offers discovered local folders, a direct selector, Windows/macOS preparation help and native worker-confirmed readiness with stale-status rejection. Selection does not stop recording; restart after confirmed saves activates a changed model. No automatic model downloads, student-data changes, microphone access or push.

Executed: **233 backend passed, 1 skip**, **60 JavaScript contracts**, **15 desktop tests**, browser synthetic flows, typecheck/lint, Python lint and production web build. See [implementation, evidence and remaining gates](docs/implementation/speech-workspace-ux.md). Frozen worker readiness passed before capture. Full packaged audio/inference validation is blocked by the drive being below SeaweedFS’s 1% free-space reserve (about 10 GB); the longer test returned 503. No files were deleted or safeguard lowered. The packaged Electron app passed model selection, persisted settings, quit/reopen and actual loaded-worker readiness in an isolated library; renderer isolation remained enabled. Unsigned installer: `.local/speech-ux/installer/Notetaker-0.1.0-Windows-Standalone-Setup.exe` (397,870,083 bytes; SHA-256 `3AEBB1A0A8CBF3EB71DCE6B942FF0660C07763B6878F44CA147274C515CB6303`). Close the app before installing; ensure more than 10 GB free on C: before recording. Installer delivery is recorded in the linked report. Next: installed upgrade and real-device qualification; human evaluation of automatic importance remains open.


## Windows live transcription repair — 2026-09-23

Active phase remains **6.8 / M08 — Standalone Windows distribution**. The installed settings had no speech model selected, so native startup silently omitted the speech worker. Native startup now always launches speech reconciliation; missing models are visible in lecture/transcript status and become retryable jobs. The Transcript UI now displays the existing fenced partial-recognition text. Model discovery checks all three required files. See [repair and verification](docs/implementation/live-transcription-repair.md).

With explicit user approval, the installed app's speech path now points to `C:\ezNote\Notetaker App\.local\models\faster-whisper-small.en`; the app was closed and other settings preserved. Next startup applies it. Student lecture data was not accessed or modified, and no microphone, model download, cloud inference or push was used.

The rebuilt packaged Electron application passed fresh-library startup, missing-model setup status, synthetic audio save, quit/reopen, persisted course and identical audio readback in `.local/standalone-smoke-b44c5eff-62e6-4208-a8fe-54cbcc2abe23`. Renderer isolation remained enabled. Installed upgrade and microphone/quality/release gates remain open.

Updated unsigned installer: `.local/live-fix/installer/Notetaker-0.1.0-Windows-Standalone-Setup.exe`, **397,916,242 bytes**, SHA-256 `906C7C693F65A6D01D3DC8389359176F10A28085B3317FC4FE53607AE93AD1D9`. It includes the earlier material-upload fix. Packaging succeeded and its frozen service matches the tested executable. No automatic installed-binary replacement occurred. Next: install this build, reopen the existing library, and confirm each lecture has a selected note model; saved audio should resume transcription with the approved speech folder.

Executed: **231 backend passed, 1 service-only skip**, **45 focused live/transcription tests**, **60 JavaScript contracts**, **15 desktop tests**, typecheck, frontend/Python lint, production desktop web build and isolated bundle smoke. Chromium verified missing-model guidance, partial transcript rendering, transition to saved passages and streamed notes. The frozen native host with real PostgreSQL/audio storage, local faster-whisper `small.en` and Ollama `qwen3:4b` produced **21 passages and a saved note revision before capture was sealed**, in `.local/host-smoke-0b288acf88314ac6b73751619adc693c`. The initial frozen live test hit SeaweedFS's 1% free-disk reserve before inference; the isolated rerun passed after space recovered. See the repair evidence for installer delivery.

## Windows material upload repair — 2026-09-22

Active phase remains **6.8 / M08 — Standalone Windows distribution**. Fixed valid slides/syllabus uploads being rejected in the installed profile: `materials.parse_upload` launched `NotetakerService.exe material-parser <extension>`, but the frozen entrypoint neither accepted its argument count nor dispatched that role. The entrypoint now forwards the extension to the existing isolated parser. No changes to file limits, extraction policy, schemas, student revisions or data. See [materials evidence](docs/implementation/course-materials.md#windows-upload-repair--2026-09-22).

Executed on Windows: **230 backend passed, 1 service-only skip**, **60 JavaScript contracts**, **15 desktop tests**, Python lint, documentation and whitespace checks. The focused materials/service suite passed **16 tests**. The rebuilt frozen service passed the same **10 command regressions**, including successful PPTX/DOCX/PDF/TXT/Markdown extraction, the API's frozen subprocess-launch branch, and corrupt/empty/unsupported/invalid-encoding rejection. The initial targeted run encountered pytest temporary/cache permissions; rerunning under isolated `.local/material-upload-fix` paths passed. Frontend code is unchanged; its existing verified web bundle is reused, with no new frontend typecheck/lint/build claim.

The corrected service is staged at `.local/material-upload-fix/service-dist/NotetakerService`; the refreshed runtime is `.local/material-upload-fix/runtime`. Unchanged web/vendor components were compared to the previous runtime SHA-256 inventory and service hashes regenerated. No running installed app, student library, microphone, provider or model was accessed or changed. Existing M08 clean-machine, upgrade, hardware, educational quality and release gates remain open.

Repaired unsigned installer: `.local/material-upload-fix/installer/Notetaker-0.1.0-Windows-Standalone-Setup.exe`, **397,914,425 bytes**, SHA-256 `FF132D0D9E7FC5BA4063362227FD082085D7E081560D3BCB8F18452A2049DF97`. The unpacked app's bundled service executable matches the tested frozen executable SHA-256. This is a rebuilt artifact, not a claim of installed upgrade or clean-machine qualification. The earlier installer and running installed app were not replaced.

Next: close the installed app normally and install the repaired build, then retry the original lecture slides and syllabus. Those user documents were not available for testing. Preserve existing library selection and data; qualify installed upgrade separately.

## Standalone Windows runtime — 2026-09-18

Active phase: **6.8 / M08 — Standalone Windows distribution**. The bundled native profile is implemented: Electron-hosted Next server, frozen Python 3.12.14 API/speech/note workers, PostgreSQL 17.11, SeaweedFS 4.47 and Ollama 0.33.3 CPU. It needs no separate Docker, Python, Node or PowerShell 7 installation. Speech/note models remain separately selected local files; no model weights were downloaded. See [runtime, build instructions and limits](docs/implementation/windows-standalone.md). Earlier entries below are historical; Phase 7.4 contention work remains deferred.

Fresh setup requires explicit standalone-library or existing-workspace selection. Standalone data is separate under Electron app data; existing Docker/PostgreSQL data remains untouched. Native processing uses the existing database reconciliation loops without Kafka, retaining outbox records. Docker retains Kafka. Runtime hashes are checked before execution; Windows-protected credentials, private library ACLs, loopback binding, occupied-port refusal and owned-process shutdown are implemented. Pause services permits library/model changes; Quit retains data and stops owned native processing. No SQLite production replacement, Qt restoration or provider fallback.

Executed Windows checks: **220 backend passed, 1 service-only skip**, **60 JavaScript contracts**, **15 desktop tests**, typecheck, frontend lint, normal production web build and Python lint passed. Focused host tests passed **2/2** after final startup fixes. Documentation and whitespace checks passed. Source-host and frozen-host real PostgreSQL/API create/read passed. Both development Electron and the actual packaged `win-unpacked/Notetaker.exe` passed fresh-library selection, synthetic PCM upload/verified storage/seal, normal Quit, reopen, course persistence and identical downloaded audio SHA-256. Renderer Node access stayed disabled. Isolated synthetic profiles only; no microphone, student-library writes, installed-app replacement, model downloads or push.

The packaged test used `.local/standalone-smoke-528e8638-3c34-42ae-933f-e8c46026824a`; development Electron used `.local/standalone-smoke-3136b63c-7b1a-4016-8571-c9e941e137a0`. Runtime stage: `.local/windows-runtime/2b77b113-f2de-432f-87e3-539945e40860`. Frozen migrations initially blocked because a child inherited the supervisor's watched stdin pipe; separate null stdin fixed it. PyInstaller DLL search state is reset around external executables. A fresh-setup test needed the explicit Open workspace step. Interrupted synthetic profiles were retained. A pytest cache warning did not affect results; timing during interrupted/parallel builds does not qualify latency.

Installer rebuilt successfully on **2026-09-19**: `.local/windows-standalone-dist/Notetaker-0.1.0-Windows-Standalone-Setup.exe`, **397,913,314 bytes**, SHA-256 `9A173FA21DD2915DD37D0DF27B700D659651032EEBF25DE943DD87A40AE490F3`. The initial compressed NSIS build timed out. The successful build reused the tested unpacked app and existing archive with NSIS compression disabled; future native builds use store compression. No installation, existing-app replacement or publication was performed. The packaged runtime flow passed; this does not qualify the installer on a clean machine.

Next: clean-machine installer/Start menu launch, upgrade and uninstall retention, coordinated backup/restore, crash recovery during capture, long-duration audio and broker-free outbox growth, actual packaged speech/note inference, signing, accessibility and earlier human quality gates. Do not label the app release-ready. macOS follows Windows.

## Standalone Windows distribution — prebuilt web component — 2026-09-17

Active phase: **6.8 / M08 — Standalone Windows distribution**, following the user's request to move to the next phase and the recorded Windows-before-macOS sequence. Phase 7.4's PostgreSQL contention experiment remains deferred, not complete. Earlier entries below are historical. See [scope and exact next work](docs/implementation/windows-standalone.md).

`bun run prepare:desktop-web` now builds an isolated Next standalone component with loopback API rewrites, static/capture assets and a SHA-256 file manifest. It rejects copied private configuration and writes to a new `.local/desktop-web/<uuid>` directory. Normal web/Docker builds are unchanged. This component does not yet bundle a runtime or alter the current Electron installer/service startup. PostgreSQL authority and the explicit existing-Docker-library choice remain required; do not activate leftover SQLite standalone mode as a production shortcut.

Executed on Windows: web component build (1,240 files, 27,783,751 bytes excluding manifest), hash verification and isolated Chromium smoke using Node 22.13.1. The smoke copied the component outside the repository, loaded the actual React UI with synthetic API responses, opened the course form and served five capture assets. Its initial 10-second startup allowance expired; a 60-second allowance passed. No startup-latency qualification is claimed. **60 JavaScript contracts**, **13 desktop tests**, typecheck, frontend lint and normal production web build passed. No backend changes or backend test rerun, microphone access, student-library writes, model downloads, installer rebuild or push.

Next: supervise the staged server through Electron's runtime with loopback port collision handling, owned-child shutdown and writable cache paths outside installation; then bundle pinned Windows Python/API/speech and PostgreSQL/audio/broker runtimes, license/integrity checks and explicit library selection. Qualify packaged synthetic capture/recovery/upgrade before clean-machine release. Earlier quality, provider, hardware, accessibility, endurance and restore gates remain open.

## Phase 7.4 — Processing diagnostics and scale baseline — 2026-09-17

Active phase: **7.4 — Measured infrastructure**, explicitly selected by the user after reading the 7.3 handoff. Earlier dated active-phase statements are historical. First increment: authenticated, content-free `GET /diagnostics/processing` with aggregate current-epoch job counts, retry eligibility, expired leases and oldest currently due time. It excludes hidden/deleted lectures and obsolete epochs. No migration, student-library writes, model/provider calls, microphone access, new infrastructure or UI polling. See [implementation, semantics and next work](docs/implementation/phase-7-4.md).

Executed isolated Windows SQLite experiment: 1k/10k/100k synthetic jobs, 10% active, 100 lectures and 20 warm samples per size. Median queries 1.194/2.806/72.962 ms; p95 1.532/2.967/98.234 ms. Responses remain 622–634 bytes; traced Python allocation peaks approximately 36 KB. [Raw report](docs/implementation/phase-7-4-benchmark.json) records environment and limits. This is monitoring overhead, not model throughput or end-to-end performance; no competing optimization or PostgreSQL result is claimed.

Executed checks: full backend **218 passed, 1 service-only skip**; **60 JavaScript contracts**, **12 desktop tests**; typecheck, frontend/Python lint, production web build, documentation and whitespace checks passed. Two new diagnostics tests cover authorization/privacy, tombstones/epochs, timing/retry/lease boundaries and single-query read-only behavior. Initial pytest temp/cache permissions required fresh `.local` paths; a connection-specific query counter fixed interference from the existing background coordinator. No UI changes or browser-flow qualification in this increment.

Next: isolated PostgreSQL workload with concurrent synthetic job transitions/audio saves, query plans, and monitoring-disabled/enabled save-latency comparison at a declared sampling interval. Decide on index/cache changes from that evidence. A student-facing panel and inference timing history remain deferred. Earlier note/question quality, live-provider and M08 release gates remain open; standalone Windows distribution remains follow-on work. No push or installer rebuild.

## Generated questions and learning evaluation — 2026-09-17

Active phase: **7.3 — Learning tools**. Generated question/flashcard sets and separate question-quality evaluation are now implemented. The next user-selected delivery priority is standalone Windows distribution, with human note/question quality and earlier M08 release qualification explicitly retained as open work.

Study tools → Generated questions & flashcards generates from one eligible saved note section using the selected note model. It supports mixed/flashcard/practice formats, up to eight questions, a study focus, and explicit cloud confirmation. Each new set preserves earlier sets and edits. The existing note worker runs durable question jobs after note work using the same inference slot; source/model/settings/epoch/lease fences protect previews and publication. New migration **0017** adds pinned sets and append-only question revisions. Existing student data was not migrated or changed.

Questions expose their cited evidence and support protected wording/answer edits, four quality dimensions with feedback, conflict comparison, saved history/undo and separate self-assessments. Quality concerns pause assessment; changed note/source revisions block it. Edits/quality saves start fresh self-assessments. Scratch answers and unsaved question drafts are explicitly temporary to the open card. Deletion erases sets/edits/reviews and fences late results and receipt replays. No paid provider, microphone, model download, installation or push was used.

Executed: stable full backend **216 passed, 1 service-only skip**; 26 new question/adapter/evaluation tests cover queue ownership/idempotency, stale publication, lease reclaim, invalid output, shared inference slot, cloud consent/routing, edits/history, quality/assessment transitions and deletion. Existing migration-preservation tests run through 0017. **60 JavaScript contracts**, **12 desktop tests**; Chromium questions flow and prior study flow passed, including cloud consent, request retry identity, unvalidated preview, source reveal, conflict/draft comparison, quality gating, undo, stale-source blocking and Midnight/400px layout. Narrow screenshot inspected. Typecheck, frontend/Python lint, production web build, documentation and whitespace checks passed.

Actual installed `qwen3:4b` ran on synthetic CS, biology, physics and history fixtures. Final result: **4/4 successful requests, 8 structurally/citation-valid questions, 3/4 fixture pattern checks passed**. Physics still omits intermediate working. Assistant audit also records CS cue wording and biology specificity/redundancy issues. Human rubric fields remain unfilled and learning outcomes are not measured. See [evaluation, recorded failures and human protocol](docs/ai/phase-7-3-learning-evaluation.md) and [implementation details](docs/implementation/phase-7-3.md).

Earlier trials exposed unsupported Ollama grammar and a cited but invented numerical biology exercise. The adapter now uses an inlined simplified grammar, retains full post-generation validation, and rejects generated numeric literals absent from cited sources. Original reports remain committed beside the final rerun. Interrupted long trial timings do not qualify latency. A long-running backend suite spanned a module edit and failed a mixed-import case; the stable final run passed. Browser testing exposed verbose textarea accessible names; explicit labels fixed them.

Next delivery work: standalone Windows service/runtime packaging through the existing Electron/React/FastAPI path, with explicit existing Docker/PostgreSQL-library preservation and user-selected local model files. Do not restore Qt or silently migrate/delete the existing library. The installer has not been rebuilt for this increment and retains Docker/PowerShell/Ollama/speech-model prerequisites. Independent qualification still needed: improve worked-step completeness, review held-out questions against human-verified notes, run a learning-outcome pilot, qualify live provider inference and M08 hardware/accessibility/endurance/clean-install/upgrade/restore gates. macOS follows Windows.

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
