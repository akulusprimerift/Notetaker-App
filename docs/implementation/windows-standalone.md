# Standalone Windows distribution — web bundle increment

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
