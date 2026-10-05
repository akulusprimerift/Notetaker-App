# macOS standalone runtime — Phase 6.9.2

Current direction (2026-10-05): **SQLite standalone only**. PostgreSQL, SeaweedFS, Kafka and Docker are retired from the app. The Mac runtime bundles SQLite through Python, FastAPI, speech/notes workers, the shared React web component and Ollama. See [current build, storage, explicit conversion and executed evidence](sqlite-standalone.md).

The remaining entries are historical PostgreSQL packaging evidence. Their commands and library-selection directions are superseded; preserve earlier libraries until explicit conversion succeeds. Earlier Mac/Windows hardware and release qualification remains open.

## Historical distribution notes

Status (2026-09-29): **6.9.2 is active**. Native build/staging commands, dependency checks and an unpacked Electron app target are implemented. Their cross-platform contracts pass on Windows. No native Mac runtime, app or installer has been produced in this session. Completion still requires Apple Silicon builds and actual bundled-service startup without developer dependencies on the runtime machine.

## Build-machine preparation

Use an Apple Silicon Mac, native arm64 Node 22 or later, Bun 1.3.10, uv and Apple's command-line tools (`lipo`/`otool`). These are build requirements, not intended end-user requirements. Rosetta builds and cross-building from Windows are refused before launching a build. Use a fresh checkout and retain any existing library separately.

```sh
bun install --frozen-lockfile
uv venv --python 3.12
uv pip sync apps/api/requirements-windows.lock apps/api/requirements-dev.lock
bun run test
bun run test:desktop
PYTHONPATH=apps/api uv run --no-project python -m pytest apps/api/tests/test_runtime_platform.py apps/api/tests/test_windows_host.py -q
bun run build:macos-service
bun run prepare:desktop-web
```

The historically named `requirements-windows.lock` is universal and includes macOS markers for macholib; it already pins the speech stack and PyInstaller. The development lock supplies test tools. Do not replace the locks or silently choose other package versions if an arm64 wheel is unavailable: record the missing dependency and resolve it explicitly. Existing environments should be synchronized, not recreated. The service command requires the repository's `.venv`, checks its native architecture, and creates a fresh `.local/macos-service/<uuid>` output. It shares the existing service spec and explicitly sets `target_arch='arm64'` as supported by [PyInstaller's architecture documentation](https://pyinstaller.org/en/stable/feature-notes.html#macos-multi-arch-support). No model is needed to build.

## Supply and lock native components

Native vendor acquisition and relocation still need to be performed and recorded on the Mac. The scripts consume explicit local component folders; they do not download executables, models or student data. Obtain arm64 components from their publishers, verify archive/source checksums independently, and record exact versions, source URLs, archive hashes and any build/relocation procedure in each component's `source` field. The generated local inventory lock detects subsequent file changes; it does **not** authenticate a publisher or replace upstream checksum verification.

Required layout within the selected folders:

| Component | Required files and supporting content |
| --- | --- |
| `service` | `NotetakerService`, the entire generated `_internal` tree, Python and bundled package license/notice files collected from the actual Mac build environment. |
| `postgres` | PostgreSQL **17.x**: `bin/postgres`, `bin/initdb`, `bin/pg_ctl`, `share/postgresql/postgres.bki`, all other required share files, extensions and relocated libraries, publisher licenses. |
| `seaweed` | `weed`, its runtime dependencies and license. Validate the supervisor's server flags against the selected build. |
| `ollama` | `ollama`, the matching Mac runtime libraries/runners and license. Do not include `~/.ollama/models` or other model weights. |
| `account-client` | Pinned Codex **0.154.0** arm64 vendor tree with `bin/codex`, plus license and notice files. Bun installs its platform package under `node_modules/@openai/codex-darwin-arm64/vendor/aarch64-apple-darwin`; copy it to a separate staging folder before adding notices. |

Preserve upstream framework/library layout. All symbolic links must remain within their component and must not form cycles. The staging tool materializes safe links and retains file permission bits. Executables must already have executable permission. Do not point at a Homebrew installation directory and assume it is portable: required libraries must be packaged with relative loader paths. Do not reuse the committed Windows Python notices as evidence for different Mac dependencies. The script checks for notice presence, not legal completeness.

Create an ignored `.local/mac-component-sources.json` with this shape, replacing every placeholder with real build evidence. Directories resolve relative to this JSON file; absolute paths also work.

```json
{
  "components": {
    "service": {"directory": "/absolute/frozen-service", "version": "0.1.0", "source": "local build: git commit, lock hashes, Python version; Mac dependency notices"},
    "postgres": {"directory": "/absolute/postgres", "version": "17.REPLACE", "source": "publisher URL, verified SHA-256 and relocation recipe"},
    "seaweed": {"directory": "/absolute/seaweed", "version": "REPLACE", "source": "publisher URL and verified SHA-256"},
    "ollama": {"directory": "/absolute/ollama", "version": "REPLACE", "source": "publisher URL and verified SHA-256"},
    "account-client": {"directory": "/absolute/account-client", "version": "0.154.0", "source": "Bun frozen lock; arm64 vendor tree plus upstream license/notice"}
  }
}
```

```sh
bun run lock:macos-runtime .local/mac-component-sources.json
bun run prepare:macos-runtime /absolute/desktop-web-bundle /absolute/generated/component-lock.json
bun run build:macos-app /absolute/prepared-macos-runtime
```

Use the paths printed by the preceding commands. Each inventory/staging operation creates a new UUID directory. Sources are left intact. A failed stage stays available for inspection and receives no runnable runtime manifest. Lock files contain local build paths; retain them under `.local`, not in Git. Record sanitized versions/checksums in implementation evidence once actual Mac components are selected.

Staging requires the full locked inventory to match, verifies the web component's inventory, rejects missing files, notices and incompatible database/helper versions, and checks every Mach-O file for an arm64 slice. It rejects absolute load paths/search paths outside macOS system directories, missing bundled dependency suffixes, and missing/escaping loader-relative dependencies. It does not rewrite libraries or signatures. Suffix presence for `@rpath`/`@executable_path` is a preliminary check, **not proof that dyld can resolve the complete graph**. Actual startup from the packaged location, library/framework signatures and clean-machine tests remain mandatory. An executable version string alone is also not proof of compatibility.

The manifest records `darwin/arm64`, per-file hashes, component provenance, CPU speech processing and that native startup is unverified. Electron packaging rechecks integrity and native dependencies and uses the staged account helper. It emits an **unpacked development app** under `.local/macos-standalone-dist`; signing identity discovery is disabled. DMG, icons, signing, notarization and public distribution belong to 6.9.5.

The shared runtime already stores PostgreSQL, audio objects, credentials, logs, speech status and the writable web copy under the selected Electron user-data folder, outside the app bundle. The Docker and Windows libraries are not migrated. Note models and speech folders remain explicit local choices; no speech model is selected by these scripts. Missing models must leave saved audio intact and processing visibly retryable.

## Native verification to execute

Close other Notetaker service instances normally first; occupied service ports must cause a visible refusal. Use only a newly created synthetic profile. The existing smoke test now selects the correct Electron executable and discovers Playwright through uv on Mac:

```sh
NOTETAKER_TEST_EXECUTABLE="$PWD/.local/macos-standalone-dist/mac-arm64/Notetaker.app/Contents/MacOS/Notetaker" \
  bun tests/desktop/native-smoke.cjs /absolute/prepared-macos-runtime
```

The packaged app reads its own bundled resources; the supplied runtime path is for the development-launch variant. Confirm the actual app output path before running. The test creates a unique `.local/standalone-smoke-*` profile, prohibits microphone access, saves synthetic PCM, exports final-snapshot artifacts, quits, reopens and verifies byte-identical audio. It also checks theme persistence and renderer isolation. Windows titlebar overlay checks stay Windows-only; native Mac chrome is deferred to 6.9.3. The adapted smoke has not run against a native Mac bundle yet.

Then verify service readiness on a Mac without Homebrew/Python/Node/Docker on PATH, parent-input closure, partial startup failure, service shutdown order, database reopen and remaining descendants. Run the real POSIX group test (skipped on Windows). Record macOS version, hardware, component versions/hashes, app path and logs. CPU speech/local note performance and the full lecture workflow follow in 6.9.4. Earlier 6.9.1 abrupt-supervisor-death/escaped-process containment gaps remain open.

## Executed evidence in this increment

- Windows: **31 desktop tests passed**, including six Mac build/staging test groups covering host refusal, locked copy and integrity, component failure paths, source preservation, symlink escapes/cycles, private-data refusal, foreign Windows/Linux native modules, and simulated Mach-O architecture/load-path failures. These tests use synthetic files and mocked Mac tool output.
- **60 JavaScript contracts** passed; frontend typecheck, lint and production build passed; Python lint passed.
- Focused backend platform/host tests: **11 passed, 1 skipped** (real POSIX group test). An existing pytest cache-directory permission warning did not affect results. The backend implementation was unchanged; the full backend suite was not rerun.
- Documentation links/structure and whitespace checks passed.

No native Mac build, runtime launch, dependency download, microphone access, live-provider inference, student-library mutation, Windows installer replacement, installation or push occurred. Phase 6.9.2 remains active until the bundled Mac startup acceptance condition has actual native evidence.
