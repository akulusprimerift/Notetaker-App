# Session transfer

## Persistent recording and lecture layout - 2026-10-03

Active phase remains **6.9.5 - Mac installer and distribution**. The accepted `notetaker-layout` increment moves Notes and Finish to the prominent lecture navigation, places Transcript, Capture, Materials, Visual notes and Study tools in quieter side navigation, and keeps a real recording controller and save status in a sticky workspace header. The Record picker requires an explicit course and lecture before starting. One recorder controller survives library, course and lecture-section hash navigation; Capture opens the same controller's recovery and saved-segment details. Data-removal progress sits in the library sidebar while removal and finalization remain accessible under Finish. Settings relocation and broad theme changes remain with the follow-on settings work; flashcard and catch-up changes remain separate.

See [workspace layout and recording evidence](docs/implementation/workspace-layout-recording.md) for exact checks, limits and delivery pointer. Synthetic browser verification does not qualify physical-device recording or Mac lifecycle behavior.

## Phase 6.9.5 DMG published — 2026-10-02

Active phase: **6.9.5 — Mac installer and distribution**. The user reported the 6.9.4 test build works on their Mac. Tagged CI now builds a drag-to-Applications DMG with a Mac icon and run-number build version. Developer ID signing (hardened runtime, entitlements), notarization and stapling run only when the `MACOS_CERTIFICATE_P12`, `MACOS_CERTIFICATE_PASSWORD`, `APPLE_ID`, `APPLE_APP_SPECIFIC_PASSWORD` and `APPLE_TEAM_ID` secrets exist; native components are signed before the runtime hash lock because the launcher verifies them. [Details](docs/implementation/macos-distribution.md).

Executed: Windows `bun run test`, `bun run test:desktop`, docs and whitespace checks. Run 37075163831 (tag `macos-v0.1.0-beta.1`) passed and published pre-release `Notetaker-0.1.0-macOS-arm64-unsigned.dmg` (711,945,751 bytes, SHA-256 `63a6f0edbf1d44f1bbcf4a3613851a68c40468a1bfd56946b7746d3382d2b0b0`); no signing secrets were present, so it is ad-hoc signed and un-notarized.

**Exact next work:** the user installs the DMG over the existing app and confirms the library is retained. To complete 6.9.5, add a Developer ID Application certificate and the secrets above, push a new `macos-v*` tag, and verify the notarized DMG opens on a clean Mac without `xattr`. Then 6.9.6.

## First downloadable Mac test build — 2026-10-02

Active phase remains **6.9.4**. At the user's request, `.github/workflows/electron-macos.yml` builds an unsigned Apple Silicon app on GitHub's macos-15 runner when a `macos-v*` tag is pushed, and publishes it as a pre-release. PostgreSQL 17.11 is built from the publisher source (SHA-256 checked) with loader paths relocated and ad-hoc signed; SeaweedFS 4.47 (publisher MD5) and Ollama 0.33.3 (publisher SHA-256) are verified; Intel-only Ollama libraries are dropped and the arm64 dependency audit still gates packaging. No models are bundled. `scripts/ci-step.sh` posts failure logs as public annotations.

First successful run: tag `macos-v0.1.0-test.10`, run 37069067692, pre-release asset `Notetaker-0.1.0-macOS-arm64-unsigned.zip` (714,175,868 bytes). Shared JavaScript/desktop tests and focused backend host tests passed on the runner before packaging. Real-Mac fixes found by CI: resolved-path containment for runtime copies (`/var` → `/private/var`), top-level-only `models`/`standalone-library` refusal, Windows path rules in PowerShell discovery, a simulated Windows flag in host tests, and dylib install names no longer treated as missing dependencies. A brief non-blocking-test change was reverted; that run did not publish.

**Not yet verified:** the app has not been launched on a Mac. Next: the user installs it (unzip, move to Applications, `xattr -dr com.apple.quarantine /Applications/Notetaker.app`), creates a new standalone library, and runs the packaged smoke and [workflow harness](docs/implementation/macos-workflow.md). Signing/notarization/DMG remain 6.9.5.

## Phase 6.9.4 workflow harness and Windows baseline — 2026-10-01

Active phase: **6.9.4 — complete Mac lecture workflow**, at the user's request; the Windows priority repair is delivered and macOS resumes. 6.9.1–6.9.3 native Mac qualification remains open because no Mac app has been built. `scripts/test-windows-host.py` now runs on Windows or Mac and drives one synthetic lecture through the frozen host: material, speech readiness, missing-note-model refusal, paced verified capture, live passages/streamed notes, citations/source audio, protected edit → regeneration → merge → undo, recall/self-assessment/catch-up, exports, finalization and byte-identical audio. Without a speech model it checks the missing-model path. [Behavior, baseline and Mac commands](docs/implementation/macos-workflow.md).

Executed on Windows standalone runtime `.local/audio-retention/runtime` with small.en and qwen3:4b: 272 s paced lecture **passed** (first passage 9.5 s, first saved notes 94.3 s, transcript done 89.9 s and notes settled 588.7 s after capture end, max speech backlog 52.2 s); 68 s paced and missing-speech-model runs passed. **39 desktop tests**, **63 JavaScript contracts**, Python lint passed. Three harness defects (heartbeat, escaped marker, stream metrics) were fixed and rerun; no product code changed. The user closed the installed app for the run; their library was not accessed.

**Exact next work:** on the Apple Silicon Mac, finish 6.9.2 runtime preparation, then run both harness modes and the packaged smoke per the linked guide and record Mac limits. Service-failure and low-storage checks need a disposable Mac volume/user. No microphone, download, provider, installer build or push.

## Live transcription and audio storage repair — 2026-09-30

Active phase: **6.8 / M08 — priority repair before macOS**; 6.9.3 stays paused. Root cause of "audio saves but never transcribes": the bundled SeaweedFS default `-volume.max=8` was full, so every chunk upload was refused and no speech jobs existed. SeaweedFS now starts with `-volume.max=0`; capture runs at 16 kHz; live cores are 4 s. New lectures delete transcribed audio behind final live passages unless **Keep lecture audio** is on; finalizing offers keep-all or delete-all. Migration 0018 is additive and keeps audio for existing lectures. [Behavior, evidence and limits](docs/implementation/live-transcription-storage.md).

Executed: full backend **266 passed, 2 existing skips**; **63 JavaScript contracts**, **39 desktop tests**; typecheck/lint/production build, Python lint, whitespace; real bundled SeaweedFS cap reproduction; real Chrome 16 kHz capture/recovery/restart; production-renderer retention UI. No microphone, student-library change, download, packaging or push.

Cloud-processing confirmation now closes once confirmed and is remembered per provider on this device; Withdraw restores it (production-renderer check in real Chrome). Commits: `70af3aa` (audio), consent in the following commit.

Claude subscription models were requested but not built: Anthropic's Agent SDK documentation (checked 2026-09-30) still states that, unless previously approved, third-party developers may not offer claude.ai login or subscription rate limits. Claude models remain available through a Claude API key in Accounts & API keys; subscription linking needs Anthropic approval for this app.

Installer delivered: `.local/audio-retention/installer/Notetaker-0.1.0-Windows-Standalone-Setup.exe` (407,220,688 bytes, SHA-256 `A942955F172BA2899822D33B7F0AE16A2AFB84A494DF18F816641E71897F867C`), unsigned, not installed automatically. Packaged synthetic smoke passed; see the linked report.

**Next:** close Notetaker normally, install this build retaining the existing library, and confirm recording now uploads and transcribes. Then resume macOS 6.9.3.

## Performance/restart Windows update delivered � 2026-09-30

Active phase: **6.8 / M08 � shared performance and stop/restart repair**; macOS 6.9.3 remains paused. Source commits `3743011` and `7214afb` are packaged in `.local/restart-speed/installer/Notetaker-0.1.0-Windows-Standalone-Setup.exe` (**407,285,900 bytes**, SHA-256 `F717209E63E766A8905AFBAAD245E3205E7FC4116BA8C3FB2D7BDFF5ECA437F6`). Unsigned; **not automatically installed**. [Full behavior, evidence and limits](docs/implementation/live-speed-restart.md).

Executed: **260 backend passed, 2 existing skips**, **63 JavaScript contracts**, **39 desktop tests**; frontend typecheck/lint/production build, Python lint, docs/whitespace checks; deterministic stop/upload and pause/resume regressions failed before and passed after fixes. Real Chromium passed offline recovery and three recorder restarts; production renderer passed three note pause/resume cycles and existing draft/revision/deletion checks. Fresh frozen service, staged web integrity/hydration, 1,806 reused runtime hashes and installer build passed. Actual packaged Electron passed **three recording stop/restart cycles using real API/storage**, synthetic saved audio, Quit/reopen/identical readback, isolation, themes, native controls and exports. Isolated profile `.local/standalone-smoke-f6eef723-9659-4367-a67b-ba6f29219e14`.

Local small.en CPU/int8 synthetic warm decode improved from 3.096 to 2.729 seconds on a ten-second sample, with identical text. Live beam defaults to 1, configurable back to 5; saved-only windows retain 5. Notes retain 6,000 output tokens and source checks while using bounded context and coalesced previews. Queue polling is 0.5 seconds. No real-lecture accuracy or end-to-end note-throughput claim. Cancellation fences stale work immediately; an executing provider unwinds at a preview/check or timeout while role locks prevent overlapping calls.

**Exact next work:** close Notetaker normally and install the new update retaining the existing library selection; qualify installed upgrade and the user's workflow before returning to macOS. No microphone, student-library changes, model downloads, cloud inference, automatic installation or push. Existing human-quality/hardware/release and native Mac gates remain open. Earlier entries below describe intermediate/historical states.


## Stop/restart fixes verified in shared source � 2026-09-30

Active phase: **6.8 / M08 � shared performance and stop/restart repair**. macOS 6.9.3 remains paused. Speed increment committed as `3743011`; recording stop/upload ordering and note pause/resume fencing now pass regressions that failed on the old code. Resume has an explicit button label and notes requests release busy controls after a bounded timeout. [Behavior and evidence](docs/implementation/live-speed-restart.md).

Executed: **260 backend passed, 2 existing skips**, **63 JavaScript contracts**, **39 desktop tests**; frontend typecheck/lint/build and Python lint; production browser note pause/resume (three cycles), streamed revisions/protected drafts/deletion; actual Chromium synthetic audio offline recovery and three recorder stop/restart cycles without reload; staged web hashes/hydration/assets. Synthetic local speech benchmark and quality limits are recorded below. No microphone, student-library change, downloads, external inference or push.

Next: finish the fresh frozen Windows service, stage it with the newly built web component and verified existing vendor binaries, build the unsigned installer, and run isolated packaged save/restart/Quit/reopen checks. The installed app is not yet replaced. Provider cancellation still waits for the executing call to reach a fenced preview/check or timeout; role locks prevent overlap. Earlier human-quality/hardware/release and native Mac qualification remain open.


## Speed first, then stop/restart repair — 2026-09-30

Active phase: **6.8 / M08 — shared performance and stop/restart repair**. The user pauses macOS 6.9.3 until these regressions are fixed. Speed changes use live speech beam 1 (configurable 1–5), half-second idle reconciliation, bounded note context allocation with the unchanged 6,000-token output allowance, and coalesced streaming preview parsing. [Evidence and remaining work](docs/implementation/live-speed-restart.md).

Executed: initial 71 focused backend checks and Python lint passed. Existing local small.en on newly generated 10-second synthetic speech: beam 5 took 3.517/3.096 seconds, beam 1 took 2.787/2.729 seconds, identical recognized text in these four runs. This is narrow synthetic evidence, not real-lecture accuracy or latency qualification. Final context-allocation regression run: 44 passed. Documentation and whitespace checks passed. No microphone, download, student-data change, installed binary replacement or push.

Next: repair and test recording stop/upload races and note pause/resume cancellation, complete shared checks, and package/qualify the Windows update before returning to Mac work.

## Phase 6.9.3 Mac integration source implemented — 2026-09-30

Active phase: **6.9.3 — macOS integration**, at the user's request. Earlier 6.9.1 native containment, 6.9.2 runtime build/startup and Windows release/human-quality gates remain open. This work is verified on Windows with simulated Mac contracts; it does not complete native Mac qualification. [Behavior, evidence, limitations and exact next checks](docs/implementation/macos-integration.md).

Implemented standard Mac window controls, native menus/Command shortcuts, close-to-hide preserving the renderer, Dock/second-instance restoration and guarded Quit using existing service cleanup. Mac microphone permission requests handle unknown/denied/restricted status with Settings/restart recovery and bundled purpose text. Protected credentials retain the existing Keychain-backed Electron/official-helper path with no plaintext fallback; newly written credential files use private POSIX modes. Suspend/resume events reach the recorder through a narrow preload subscription, stop/flush available capture, cancel pending starts, retain unknown-extent gaps and never automatically resume recording. Setup paths and labels are platform-neutral.

Executed on Windows: **39 desktop tests**, **62 JavaScript contracts**, **20 backend capture tests**; frontend typecheck/lint/production build, Python lint, docs and whitespace checks. Actual Chromium generated-tone AudioWorklet/worker/IndexedDB capture passed interruption while offline, retained bytes/gap, wake without restart, checksum-matching retry and saved-journal reopen (97,536 samples). Actual isolated Electron setup, hardened preload power subscription and clean Quit passed. Initial edit-encoding/test-mock failures were corrected and rerun. Backend tests retain existing deprecation/cache warnings. Full backend and packaged startup suites were not rerun. No physical microphone, OS sleep, native Mac/Keychain execution, live provider, model download, student-library change, installed app/installer replacement, installation or push.

**Exact next work:** finish 6.9.1/6.9.2 runtime prerequisites on the Apple Silicon Mac using the [build guide](docs/implementation/macos-standalone.md). Run isolated packaged synthetic save/Quit/reopen; then qualify native menu/controls/themes, hidden/minimized Dock reopening, cancel/confirm Quit, microphone denial/Settings recovery, disposable-secret Keychain failure/reopen and synthetic sleep/wake/offline gaps. Actual microphone testing still requires explicit authorization. Keep 6.9.3 active pending native evidence; 6.9.4 full workflow/performance and 6.9.5 signed/notarized distribution remain next. Quit advises waiting for confirmed saves and does not promise retention of RAM-only audio; sudden sleep may preempt flush, requiring marked recovery.

## Phase 6.9.2 runtime build preparation — 2026-09-29

Active phase: **6.9.2 — standalone Mac runtime**, Apple Silicon first. The user requested this transition; earlier 6.9.1 native lifecycle/containment qualification and Windows release/human-quality gaps remain open. This increment implements the Mac build path on the Windows development host, not a completed native runtime. [Build guide, dependency layout, evidence and commands](docs/implementation/macos-standalone.md).

Implemented native-arm64 host/Python preflight, a fresh-output frozen-service build using the shared spec and existing universal dependency locks, explicit local component provenance/inventory locking, safe staging of PostgreSQL 17/SeaweedFS/Ollama/service/account-helper components, web integrity checks, arm64 Mach-O/dependency checks, and unpacked Electron Mac packaging with the staged helper. Mixed Windows/Linux binaries, external absolute load paths, missing/changed files, missing notices, private configuration and escaping/cyclic links fail preparation. Safe internal links are materialized. Failed stages are retained without a runtime manifest. Local inventory locks detect changes but do not authenticate publisher downloads; relative dyld dependency checks still require native execution evidence.

The existing synthetic native smoke now supports Mac Electron/Playwright paths, preserves Windows overlay assertions, and reports the tested platform. It still checks synthetic audio save → Quit → reopen → identical readback, renderer isolation, themes and final-snapshot exports in an isolated new profile. It has not been run against a Mac build. Writable library/web files remain outside the app through the existing shared runtime; no product data contracts changed.

Executed on Windows: **31 desktop tests**, **60 JavaScript contracts**, **11 focused backend platform/host tests passed, 1 real POSIX test skipped**; frontend typecheck/lint/production build, Python lint, documentation and whitespace checks passed. The focused pytest run emitted an existing cache-directory permission warning. Full backend and packaged startup suites were not rerun; backend implementation is unchanged. No actual Mac tools/binaries were executed. No native dependency download, model download, microphone access, live provider, student-library change, installed app/installer replacement, installation or push.

**Exact next work:** move the checkout to the user's Apple Silicon Mac; use the guide to synchronize Bun/uv dependencies and run the real POSIX test. Build the arm64 service and web component. Obtain publisher-verified native PostgreSQL 17, SeaweedFS, Ollama and pinned Codex 0.154.0 components, relocate dependencies and gather the actual Mac licenses/notices. Record exact source/archive hashes and any build recipe, generate the local inventory lock, stage the runtime and build the unpacked app. Run the isolated packaged synthetic save/Quit/reopen smoke, then partial-start failure, parent-disconnect, leftover-descendant and clean-runtime-machine checks. Resolve native build or loader failures before claiming 6.9.2 complete. Mac native UI/permissions/Keychain/Dock/sleep follows in 6.9.3; DMG/signing/notarization follows in 6.9.5.

## Phase 6.9.1 platform foundation implemented — 2026-09-29

Active phase remains **6.9.1 — macOS platform foundation**, Apple Silicon first. Shared source preparation is implemented and verified on Windows with simulated Mac contracts; native Mac foundation qualification is still open. Windows is accepted for the current development scope with its earlier release/hardware/human-quality gaps retained. Earlier active-phase entries below are historical.

Implemented platform-specific service/account-helper paths and matching packaging resource selection, runtime target checks with legacy Windows bundle compatibility, Mac service launch/private-library permissions, cancellation-aware setup commands and owned process-group cleanup. Windows keeps Job Objects, ACLs and its Docker startup path. Workers stop before PostgreSQL; parent disconnect/signals request shutdown. Mac provider helpers receive group cleanup on completion/cancellation. No migrations, student-library changes, model downloads, microphone access, live providers, installer replacement or push.

Executed: **255 backend passed, 2 skipped** (existing service-only case and real POSIX group test); **60 JavaScript contracts**, **25 desktop tests**; frontend typecheck/lint/production build, Python lint, documentation/whitespace checks. Actual isolated Windows Electron first-launch setup, hardened renderer and clean Quit passed without opening a library. Initial new-test harness failures were corrected and rerun. [Detailed implementation/evidence](docs/implementation/phase-6-9-macos.md) records limits and the synthetic profile.

**Exact next work:** on the user's Apple Silicon Mac, set up Bun/uv and run shared tests plus the real POSIX owned-tree test. Prepare the 6.9.2 arm64 frozen service and PostgreSQL/SeaweedFS/Ollama/account-helper bundle with explicit Mac manifest metadata. Then verify isolated synthetic audio save → Quit → reopen → identical audio readback, parent disconnect, startup failure and descendant cleanup. This Windows session has not built or tested a native Mac app. Sudden supervisor SIGKILL/descendants escaping their group remain a Mac containment qualification gap; native menus/permissions/Keychain/Dock/sleep behavior follow in 6.9.3. Existing Windows installers remain unchanged.

## macOS delivery plan and phase transition — 2026-09-29

Active development phase: **6.9 — macOS delivery**, starting with **6.9.1 — Platform foundation**. The user accepts the Windows version as finished for the current development scope and requests moving on from 6.8 / M08. Earlier Windows installed-upgrade, signing, hardware, accessibility, endurance, backup/restore and human-quality qualification gaps remain recorded; this transition does not claim those checks passed. Earlier active-phase and next-work entries below are historical.

The user has access to an **Apple Silicon Mac for building and testing**. Target **macOS arm64 first**, preserving the Windows app's features and standalone installation experience through the existing Electron/React/FastAPI architecture. Intel Mac support is a possible follow-up, not part of this first target. Keep one shared application with platform-specific packaging and operating-system integration; preserve existing Windows and Docker libraries.

### Sequential milestones

| Milestone | Planned work | Completion condition |
| --- | --- | --- |
| **6.9.1 — Platform foundation** | Separate Windows executable paths, account-helper selection and service controls from shared logic. Add macOS startup, shutdown and owned-child-process cleanup. Verify Windows behavior remains intact. | The desktop host supports distinct Windows and macOS configurations with relevant regression checks. |
| **6.9.2 — Standalone Mac runtime** | Set up the project on the Mac using Bun and uv. Build the Python backend and speech workers for arm64; bundle compatible PostgreSQL, SeaweedFS, Ollama and account-helper executables. Keep the library and writable files outside the installed app and retain explicit local model selection. | The Mac app starts its bundled services without requiring end users to install Docker, Python or developer tools. |
| **6.9.3 — macOS integration** | Add microphone permission requests and denial recovery, Keychain-backed credentials, Mac window controls, menus and Command-key shortcuts. Handle Dock reopening, window close versus Quit, and sleep/wake interruptions while preserving saved audio and disclosing gaps. | Native Mac interactions and application lifecycle protect recordings and library data. |
| **6.9.4 — Complete lecture workflow** | Verify synthetic capture, durable saves and quit/reopen recovery; timestamped transcription and streamed notes with selected local models; citations, protected edits, regeneration, materials, study tools and exports. Exercise missing models, service failures and low storage. Measure concurrent transcription and note generation on the Mac. | An installed Mac build completes the lecture workflow with recorded evidence and measured performance limits. |
| **6.9.5 — Installer and distribution** | Produce the arm64 app and drag-to-Applications DMG with icon, version metadata and dependency notices. Configure Apple Developer signing for the app and bundled executables, notarization and downloaded-app checks. Test replacing an older build while retaining its library. | A signed, notarized installer launches successfully in a clean Mac environment. |
| **6.9.6 — Release qualification** | Test extended sessions, interruption recovery, backup/restore, accessibility, keyboard navigation, display scaling and upgrade preservation. Test real microphone behavior only with explicit authorization. Document supported macOS versions, measured hardware requirements and installation steps. | The Mac release passes agreed acceptance checks and is ready to distribute. |

### Environment, constraints and next work

Shared-code preparation can proceed on Windows; native Mac runtime builds, packaging and macOS validation require the Mac or a macOS build runner. Device qualification requires actual Mac hardware. Apple Developer signing credentials are needed for the planned public signed/notarized distribution; their availability is not yet established.

Keep models user-selected, with no automatic model downloads or external-provider fallback. Initially plan CPU transcription with the existing faster-whisper/CTranslate2 stack; measure Apple Silicon performance before deciding whether an alternative speech backend is needed. Existing cloud choices remain explicit per lecture. Use synthetic audio only unless the user authorizes physical microphone testing.

**Exact next work:** begin 6.9.1 by auditing desktop/runtime packaging and extracting platform-specific executable resolution and service lifecycle behavior, with meaningful Windows regression checks. Then prepare the arm64 runtime build on the user's Mac. The first end-to-end foundation target is an isolated Mac library that saves synthetic audio, quits cleanly and reopens with identical audio intact; the full lecture workflow follows.

**Evidence:** this entry records the agreed plan only. No macOS implementation, build, installation, recording or release qualification has been performed in this update. Executed: `bun run verify:docs` passed (43 planning Markdown files, 251 local links); `git diff --check` passed. Application tests were not run for this documentation-only change.

## Glass scrollbar installer delivered — 2026-09-25

Active phase **6.8 / M08**. The sidebar join and theme-accent scrollbar refinement is packaged in `.local/glass-scrollbar-update/installer/Notetaker-0.1.0-Windows-Standalone-Setup.exe` (407,273,058 bytes; SHA-256 `5148A1C94CAE24837948DA6AA8AC559CAA386E828DAA8D2D90443B4B65328039`). Unsigned, not automatically installed. [Delivery evidence](docs/implementation/paged-notes-and-motion.md#glass-scrollbar-installer--2026-09-25).

Fresh standalone web build/integrity/hydration checks and 21 desktop tests passed. All 5,239 reused native files matched their prior hashes before/after staging. Actual packaged startup, synthetic audio save/Quit/reopen/identical readback, theme persistence, native controls, renderer isolation and snapshot exports passed in isolated profile `.local/standalone-smoke-1e92f7be-43b0-4acb-ac89-80298c1a5176`. Packaged screenshot inspected; five packaged host/setup files match source.

Next: close Notetaker normally and install this build retaining the existing library selection; qualify installed upgrade. Earlier release gates remain open. No student-library access, microphone, provider calls, model downloads, automatic installation or push.

## Sidebar join and glass scrollbars — 2026-09-25

Active phase **6.8 / M08**. Removed the sidebar's upper-right rounded gap at the header. Native scrollbars now use transparent tracks, rounded translucent theme-accent handles, hover/pressed feedback and system-color fallback. [Evidence](docs/implementation/paged-notes-and-motion.md#sidebar-join-and-glass-scrollbars--2026-09-25).

Executed: 60 contracts, frontend typecheck/lint/build, synthetic Chromium four-theme appearance/persistence/narrow-layout/sidebar/recorder checks, both-axis overflow and forced-colors probes, documentation/whitespace. Midnight join and visible scrollbar screenshots inspected. No backend or student-data changes, microphone or providers.

Next: package the updated renderer with the verified standalone runtime and qualify packaged/installed upgrade. **This refinement is not yet in the installer or installed application.** Earlier M08 qualification gaps remain open.

## UI update installer delivered — 2026-09-24

Active phase **6.8 / M08**. Paged notes, integrated header/sidebar animation and liquid-glass/loading changes are packaged at `.local/paged-ui-update/installer/Notetaker-0.1.0-Windows-Standalone-Setup.exe` (407,272,519 bytes; SHA-256 `92613B65191C286AB844A33506C6539645BB78F78E127075014B5527889F7203`). [Delivery evidence](docs/implementation/paged-notes-and-motion.md#installer-delivery--2026-09-24).

Fresh standalone web build/hash/hydration checks passed. All 5,239 reused native files verified before/after staging; packaged host/setup files match source. Actual packaged startup, synthetic audio save/Quit/reopen/identical readback, native overlay, theme persistence and snapshot exports passed in isolated profile `.local/standalone-smoke-c6aada68-9f3b-4090-a7b8-f77e56222834`. A first-test finalization cursor conflict was handled by a bounded refetch/retry in the test; full rerun passed. Product fencing unchanged.

The installer is unsigned and has not been automatically installed. Next: close Notetaker normally, install this update and retain the existing library selection; qualify installed upgrade. No student data, microphone, live providers or models accessed. Earlier M08 release gates remain open.

## Paged notes and liquid glass — 2026-09-24

Active phase **6.8 / M08**. All three requested source increments are implemented: bounded numbered notes with continued content and smooth horizontal navigation; integrated native window controls and animated/inert sidebar; stronger glass surfaces, interaction feedback and gradient loading progress. First two commits: `6b2b05d`, `f87056d`; glass/final evidence is committed with this entry. [Detailed evidence](docs/implementation/paged-notes-and-motion.md).

Executed: 60 JavaScript contracts, 21 desktop tests, typecheck/lint/production web build, four-theme Chromium appearance, 32 focused contrast pairs, setup loading/recovery/reduced motion. Production-renderer tests passed long-note pagination/live growth/current section preservation, source links, protected drafts, automatic revisions and deletion. Actual isolated Electron passed overlay/top alignment/dragging/control clearance at 760/1100/1360px and recorder retention. No backend changes; Python suite not rerun. No microphone, provider calls, student-library modification, installation or push.

Next: rebuild the standalone web/runtime installer and qualify installed upgrade with the existing library selection. **The installed application and installer have not been updated for these three commits.** Earlier M08 release/hardware/human-quality/restore/accessibility gates remain open.

## Integrated header and sidebar — 2026-09-24

Active phase **6.8 / M08**. Section 2 integrates native controls into the workspace header and animates the inert hidden sidebar while retaining recording. Actual isolated Electron and Chromium checks, 21 desktop tests and frontend typecheck/lint passed. [Evidence](docs/implementation/paged-notes-and-motion.md). Section 1 committed as 6b2b05d. Next: glass/loading polish and final build checks. Installer remains unchanged.

## Paged notes — 2026-09-24

Active phase **6.8 / M08**. Section 1 adds a bounded numbered note reader with continued text, horizontal swipe/scroll, keyboard navigation, source links and reduced motion. Windows Chromium long-note/narrow-layout/source checks and frontend typecheck/lint passed. See [evidence and next sections](docs/implementation/paged-notes-and-motion.md). No installed app or student data changed. Next: integrated window header/sidebar motion, then glass/loading polish; build and installer qualification remain pending.

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
