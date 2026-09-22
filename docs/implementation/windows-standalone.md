# Standalone Windows distribution

Upload repair (2026-09-22): the frozen service now dispatches the document-reader command used by material uploads. See [cause and regression coverage](course-materials.md#windows-upload-repair--2026-09-22) and the latest [installer evidence](../../SESSION_TRANSFER.md). To exercise a future packaged reader, set `NOTETAKER_TEST_SERVICE_EXECUTABLE` to its absolute `NotetakerService.exe` path and run `uv run --no-project python -m pytest apps/api/tests/test_windows_material_parser.py -q` with `PYTHONPATH=apps/api`. This checks all supported formats and rejects unreadable inputs without opening a student library.

## Native services increment — 2026-09-18

Active phase: **6.8 / M08**. The standalone x64 installer combines Electron/React with frozen Python/FastAPI, speech and note workers, PostgreSQL 17.11, SeaweedFS 4.47 and Ollama 0.33.3 CPU libraries. Electron runs the prebuilt Next server through its utility-process runtime. This profile needs no separate Node, Python, Docker or PowerShell 7 installation. Models remain user-selected local files; the app never downloads weights. Faster-whisper's upstream auxiliary VAD asset accompanies the speech runtime. Earlier entries below describe the preceding web-only increment.

First launch requires an explicit choice: **Create or open standalone library**, or select an existing Docker workspace folder. Once services are ready, select **Open workspace**. Later launches reopen the selected library. Standalone creates a separate PostgreSQL library; it never imports, converts, deletes or modifies the existing Docker library. This remains a development distribution.

The native profile uses existing database reconciliation without Kafka (`NOTETAKER_BROKER_ENABLED=false`). Transactions, leases, outbox rows and retry fencing remain intact; notifications are not falsely marked published. Retained outbox growth and broker-free throughput require endurance qualification. Docker retains Kafka. SQLite remains a test/development preview, not the Windows production authority.

### Data and lifecycle

All mutable state remains under the per-user Electron app-data folder shown in setup, outside installation:

- `standalone-library`: PostgreSQL, audio objects/filer state and service logs; Windows ACLs restrict it to the current user and SYSTEM.
- `standalone-secret.bin`: Windows-protected database/object credential. Preserve it with the library; missing credentials never cause database reinitialization.
- `standalone-web/<build-id>`: writable web component/cache. Existing desktop settings, protected provider connections and Chromium recovery journals remain in the same app-data profile. Uninstall retains app data.

Choose an existing faster-whisper folder in setup and restart services to apply it. Bundled Ollama uses the user's existing `.ollama/models` directory and runs on CPU; no GPU-performance claim is made. Note-model selection stays per lecture. No model pull or external-provider fallback occurs.

All services bind to loopback: web 3000, API 8010, PostgreSQL 55432, Ollama 11435, Seaweed master 19333/29333, volume 18080/28080, filer 18888/28888 and S3 18333/28333. Occupied ports stop startup without terminating the listener. Optional Iceberg/Lance endpoints are disabled. Provider calls use the authenticated Electron bridge's allocated loopback port.

SHA-256 verification precedes bundled execution. Native service children belong to a Windows kill-on-close Job Object. Normal Quit stops the owned web server, workers/object service and PostgreSQL; supervisor exit terminates its owned children. Unrelated Docker services are untouched. Hide keeps recording/processing alive. Finish recording and wait for confirmed saves before Quit or **Pause standalone services**. Pause permits library switching and model changes. Failures retain data and show status; logs stay local. Coordinated backup/restore is unqualified: copying a running database directory is not an accepted backup procedure.

### Build and verification

Build on Windows x64 using Bun, uv and Python 3.12 (tested 3.12.14). Provisioning downloads pinned executables on the build machine, never student models.

```powershell
bun install --frozen-lockfile
uv pip sync apps/api/requirements-windows.lock
pwsh -NoProfile -File scripts/Provision-WindowsRuntimes.ps1
bun run prepare:desktop-web
$env:PYTHONPATH='apps/api'
uv run --no-project python -m PyInstaller --noconfirm --distpath .local/windows-service-dist --workpath .local/windows-service-build scripts/windows-service.spec
bun run prepare:windows-runtime <printed-web-bundle-folder>
$env:NOTETAKER_NATIVE_RESOURCES='<printed-native-runtime-folder>'
bun run build:desktop
```

Run shared web/frozen-service builds sequentially. Preparation creates new UUID directories and retains old artifacts. Vendor archive versions, sources and SHA-256 values are pinned in the scripts. Runtime licenses and Python/package metadata accompany the bundle; see [notices](../../apps/desktop/third-party/native/NOTICE.md). No credentials, user models or lecture data are packaging inputs.

Output: `.local/windows-standalone-dist/Notetaker-0.1.0-Windows-Standalone-Setup.exe`; unpacked app: `.local/windows-standalone-dist/win-unpacked/Notetaker.exe`. Without the native-resources environment variable, the Docker-prerequisite build remains in `.local/desktop-dist`.

The native development installer disables NSIS compression to avoid recompressing the large runtime within the builder's fixed compiler timeout. The initial compressed installer attempt timed out; its already-built application passed the packaged smoke test. This build setting trades installer size for predictable packaging. An unchanged unpacked app can be repackaged with `bun run build:desktop --prepackaged .local/windows-standalone-dist/win-unpacked` and the same native-resources environment variable.

```powershell
uv run --no-project python scripts/test-windows-host.py <native-runtime-folder>
node tests/desktop/native-smoke.cjs <native-runtime-folder>
$env:NOTETAKER_TEST_EXECUTABLE='<absolute-unpacked-app-path>'
node tests/desktop/native-smoke.cjs <native-runtime-folder>
```

Run these tests sequentially because ports are shared. They create isolated `.local/host-smoke-*` / `.local/standalone-smoke-*` profiles, never access the microphone or existing student library. The Electron test selects a new library, writes/seals synthetic PCM through the real API/object store, quits/reopens, and compares audio SHA-256 and persisted course identity.

Executed Windows checks: full backend **220 passed, 1 service-only skip**; **60 JavaScript contracts**, **15 desktop tests**, typecheck, frontend lint and normal production web build passed. Subsequent focused host tests **2 passed** and Python lint passed. Real frozen service smoke passed native PostgreSQL initialization/migrations and API create/read. Final packaged-flow results are recorded in the session transfer.

Early frozen startup attempts exposed migration sharing the supervisor's watched stdin pipe. Child stdin now uses a null handle; frozen startup passes. External executable launches also reset PyInstaller DLL search state. Interrupted attempts and startup allowances do not qualify latency. The first fresh-setup smoke needed an explicit Open workspace step; its interrupted synthetic profile was retained. A pytest cache-permission warning did not affect focused test results.

Next qualification: clean-machine installer/Start menu launch, upgrade/uninstall retention, signing, coordinated backup/restore, worker crash during capture, long-duration audio/outbox behavior, actual speech/note inference in the packaged profile, accessibility and human note/question quality. Real microphone testing remains unauthorized. macOS follows Windows. Phase 7.4 contention work remains deferred.

## Historical web component increment — 2026-09-17

Active delivery work: **6.8 / M08 — Standalone Windows distribution**, following selected Phase 7 work. Phase 7.4's PostgreSQL contention experiment remains deferred, not completed. Earlier note/question quality and release gates remain open.

## Intended result and current boundary

Students should ultimately install and run the Electron lecture companion without building application services themselves. This first increment produces the prebuilt Next.js workspace as a separately testable component. The existing installer still uses Docker/PowerShell/Ollama prerequisites; this increment does not switch the installed app to a standalone service runtime.

Keep Electron/React/FastAPI, PostgreSQL authority and the existing Docker library intact. Do not activate the leftover SQLite standalone configuration as a production replacement. Any new library remains explicitly selected and separate. Models remain user-selected local files. No student data or model weights enter packaging inputs.

## Build and verify

```powershell
bun run prepare:desktop-web
node tests/desktop/web-bundle-smoke.cjs <printed-bundle-folder>
```

The build command enables Next's standalone output only for this build, pins API rewrites to loopback port 8010, and writes to a new UUID directory under `.local/desktop-web`. It adds Next static assets and browser capture files, verifies required entrypoints and records a SHA-256 inventory in `bundle-manifest.json`. Copied `.env` files, `.local`, `.git` and symbolic links are rejected. Existing outputs are retained; the command does not clean any library or build directory outside Next's normal `.next` build output. Run builds sequentially because they share `.next`.

The manifest describes the web component, not a complete offline installer. It records `runtime_bundled: false`: a compatible Node runtime is still needed to execute `apps/web/server.js`. Normal web/Docker builds remain available with their original settings. The current Electron installer is unchanged and does not consume this staged component yet.

The smoke test verifies every recorded hash, copies the bundle to a temporary directory outside the repository, launches its server with a minimal environment on a random loopback port, checks all five capture assets, and loads the actual React workspace in Chromium. API responses are intercepted synthetic fixtures; no student library or microphone is accessed. Opening the course form verifies hydration rather than just checking an HTML response. It shuts down its child and removes only its own temporary directory.

## Next delivery increments

Executed evidence on Windows: component build includes 1,240 files / 27,783,751 bytes excluding the manifest; isolated smoke passed with Node 22.13.1 and Chromium, including all hashes, capture assets and React form interaction. The first smoke attempt's 10-second startup allowance expired; the 60-second allowance passed. This does not qualify startup latency. **60 JavaScript contracts**, **13 desktop tests**, typecheck, frontend lint and normal production web build passed. Backend code was unchanged and its suite was not rerun. No installer rebuild or installation was performed.

1. Package and supervise the prebuilt web server through the Electron runtime, including port collisions, owned-process shutdown and writable cache paths outside the install directory.
2. Package compatible Windows Python/API/speech runtimes and PostgreSQL/audio/broker services with pinned versions, licenses and integrity verification. Preserve the Docker profile and explicit existing-library selection. Decide model-runtime provisioning without downloading weights.
3. Verify isolated synthetic capture, recovery, worker restart, upgrade and uninstall retention through the packaged app. Then qualify clean-machine installation, coordinated backup/restore and the earlier release gates.

No clean-install, actual Electron runtime, backend connection, inference, hardware or release-readiness claim follows from the web-component smoke test.
