# Phase 6.9 — macOS delivery

Current phase (2026-09-30): **6.9.3 — macOS integration** is the single active implementation phase, at the user’s request. Native menus, window/Dock behavior, microphone permission recovery and sleep/wake recorder handling are implemented in shared source with Windows and synthetic evidence. Keychain uses the existing protected-storage bridge. Native Mac qualification remains open, including earlier 6.9.1 containment and 6.9.2 runtime build/startup gates. See [integration behavior, evidence and exact next work](macos-integration.md). Earlier dated active-phase entries below are historical.

## 6.9.1 platform foundation — 2026-09-29

Active phase: **6.9.1**, targeting Apple Silicon. The user accepts Windows for the current development scope; earlier Windows release and human-quality qualification gaps remain open. This increment prepares the shared source on Windows. It is not a Mac installer or a claim of native Mac qualification.

### Implemented

- Shared desktop platform configuration selects Windows x64 or macOS arm64 service and account-helper paths. Unsupported targets fail explicitly. Packaging selects the matching helper resource directory on its native build host; Windows packaging paths are unchanged. Mac helper binaries and native packaging are not supplied by this increment.
- Runtime manifests must match the machine's platform/architecture and include the selected service executable before library credentials are read or services start. Existing Windows manifests retain compatibility through their explicit Windows profile; new Windows manifests include target metadata. Mac bundles must declare `platform: darwin`, `arch: arm64`.
- The shared Python supervisor selects executable suffixes, launch options, permissions and socket handling by platform. Windows retains its owned Job Object and ACLs. Mac libraries use private directory permissions and a restrictive file-creation mask; service children start in independent owned sessions.
- Parent input closure and termination requests initiate shutdown. Setup commands support cancellation and bounded timeouts. Workers stop before PostgreSQL's fast shutdown; cleanup escalates only against owned children/groups. The desktop allows up to 60 seconds for orderly host cleanup and avoids waiting on an already exited host. Cancellation during bundle preparation prevents subsequent service launch.
- Mac account helpers use owned process groups, including cleanup after the group leader exits. Bridge shutdown stops its active helper processes. Credentials continue through Electron protected storage; live Keychain/account qualification belongs to the Mac integration work.
- Docker startup remains the existing Windows PowerShell path. Mac attempts receive a direct standalone-runtime message rather than attempting Windows scripts. This does not modify any existing Docker library.

The existing `windows_host.py` and `windows_service.py` module names remain compatibility entrypoints for the Windows freeze scripts. No schema migration, source-history change, model download, external-provider fallback or student-library modification is involved.

### Executed evidence — Windows development host

- Full backend suite: **255 passed, 2 skipped**. Skips are the existing service-only test and the new real POSIX process-group check. Two existing framework deprecation warnings remain.
- Focused platform/host/process tests: **12 passed, 1 skipped**. Includes real Windows child cancellation and Job Object cleanup, occupied-port refusal, simulated Windows/Mac startup and partial-start failure, database-last cleanup, and unchanged synthetic library sentinel bytes.
- JavaScript contracts: **60 passed**. Desktop tests: **25 passed**, including helper selection, target mismatch/legacy compatibility, Mac group signaling, shutdown timing, existing startup/recovery and provider contracts.
- Actual isolated Windows Electron setup, renderer sandbox/context isolation, absence of renderer Node access, and clean Quit passed. Profile: `.local/foundation-smoke-79bb1670-d4bd-4e97-b94a-ed96c871bd9d`. The test did not open a library, run services or access a microphone.
- Frontend typecheck, lint and production build; Python lint; documentation links and whitespace checks passed.

Initial focused runs exposed test-harness assumptions: the VM loader did not resolve the new platform module, and the simulated Mac signal test lacked Windows' nonexistent SIGKILL constant. Both harnesses were corrected and the focused checks rerun successfully. No test doubles qualify native Mac behavior.

### Remaining evidence and exact next work

1. On the Apple Silicon Mac, prepare Bun/uv and the platform dependencies, run the shared regression suites and the real POSIX process-tree test. Native binaries are deliberately not downloaded or built on this Windows host.
2. In 6.9.2, build the arm64 frozen service and verified PostgreSQL 17, SeaweedFS, Ollama and account-helper bundle. Match the platform manifest and service paths above. Adapt packaging and notices for Mac; the existing builder still describes Windows installer artifacts.
3. Run isolated Mac startup → synthetic audio save → Quit → reopen → byte-identical audio readback. Check partial startup, parent disconnect, signals, database restart and leftover descendants on actual macOS before closing foundation qualification.
4. Sudden supervisor SIGKILL and descendants that create their own sessions are not covered by POSIX group cleanup. Qualify those cases and add a Mac watchdog/containment mechanism if needed. Windows retains kernel Job Object cleanup. No abrupt-Mac-crash equivalence is claimed.
5. Native menus/window controls, microphone permission/denial handling, Keychain verification, Dock and sleep/wake behavior belong to 6.9.3. Complete workflow/performance, DMG/signing/notarization and release gates follow as 6.9.4–6.9.6.

No Mac build, installed upgrade, packaged Windows rerun, real microphone test, live provider request or public release was performed. The installed Windows application and existing installer are unchanged. Synthetic engineering checks do not establish educational usefulness, hardware performance or release readiness.
