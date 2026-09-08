# Session transfer

Updated: 2026-09-08.

## Current request

The user accepts Phase 6.5 as working and requests these improvements before Phase 6.6: remove Note detail/Note layout dropdowns in favor of custom prompts; transcribe short segments while recording; accumulate several segments for contextual notes; stream model-written note text; support lectures longer than an hour. Then implement Phase 6.6 protected editing and regeneration, compare/keep/merge/replace, undo, durable drafts, optimistic conflicts, settings snapshots and source invalidation.

## Working rules

Read [AGENTS.md](AGENTS.md), [README.md](README.md) and [project phases](docs/project-phases.md). Use Bun and uv. Synthetic audio only; no microphone access. Preserve local data. Commit locally, do not push. Keep implemented behavior separate from actual hardware and human quality qualification.

## Entry checkpoint

- Clean working tree at session start.
- Existing M05 uses 24-second speech cores with 2-second right context, nonstreaming whole-transcript note generation and a single shared inference slot.
- Existing M04/M05 evidence documents outstanding long-lecture, Windows performance and human-review gates.
- Phase 6.7 finalization/deletion and Phase 6.8 Windows installer remain subsequent work.

## Implemented

- `AGENTS.md` covers the product, stack, style, workflow, phases, Bun/uv, tests and linting.
- Removed Note detail/Note layout dropdowns; custom prompts govern preferences. Historical settings remain readable.
- Live speech: six-second cores, two-second context, first eligibility at eight saved seconds. Note batches wait for 24 seconds of recognized windows or 100 new words; sealed tails flush. Speech and notes have independent bounded inference slots.
- Chronological bounded note batches reuse unchanged sources; a 750-source / 75-minute synthetic transcript-shape test passes without one oversized model request.
- Genuine Ollama NDJSON output flows through persisted previews and authenticated SSE. Disabled Next.js gzip after the browser test proved it buffered text. Scroll-follow keeps the current writing visible without scrolling the whole page.
- M06: durable IndexedDB drafts; optimistic/idempotent saves; immutable student revisions; comparison, keep/merge/replace, undo; settings/source invalidation; preserved source links and saved-revision export. Migration 0007 is additive.
- Speech model loading now happens at service startup. No automatic weight downloads or cloud fallback.
- Bun lock replaces the npm lock. Docker builds use Bun/uv. Added pinned ESLint, Ruff and Playwright dev tooling.

## Executed evidence

- 131 backend tests passed on SQLite and on PostgreSQL 17.11 in isolated schemas; object readback and Kafka round-trip passed.
- 60 JavaScript contracts passed. Type checks, ESLint, Ruff, production build, Docker builds and planning verification passed (local links, 32 scenarios, six gates). Focused regressions passed after final changes.
- Browser workflow passed on Windows/Chromium: reconnect/offline reading preservation, removed presets, draft reload/recovery, streamed text before provider completion, edit during generation, compare/merge, restore, and no horizontal overflow at 390px. Screenshots: `.local/m06-browser-desktop.png` and `.local/m06-browser-mobile.png`.
- Real faster-whisper/Qwen3 4B smoke with paced synthetic audio passed. The initial 30-second probe produced first transcript at 24.11s, first streamed prose at 57.47s, saved notes at 115.61s and final current notes/export at 134.38s. The capture was held open until 115.67s; this is not proof that the saved notes arrived during those 30s of input. Raw report: `.local/m06-live-model-check.json`.
- Final speech-preloaded 60-second probe passed: first transcript **12.14s**, streaming prose **57.67s** while input was arriving, first saved notes **117.50s**, final current notes/export **174.23s**, 196 preview updates and 20 source passages. Recording was held open until 117.61s; the note model's resident state was not a controlled benchmark. Raw report: `.local/m06-live-warm-model-check.json`. Durable evidence: [synthetic integration report](evaluations/reports/m06-live-smoke.json).
- The app images were rebuilt and applied with existing sessions/data volumes preserved; no new unlock code was generated. Automatic approval review initially blocked a build because of an account usage limit; after the user requested continuation, the build and rollout succeeded.

## Environment and commands

Bun 1.3.10 is available locally at `.local/tools/bun/bun-windows-x64/bun.exe`; add that folder to the shell's PATH if `bun` is not global. uv is installed in the user's local bin. Set `UV_CACHE_DIR` to the project's `.local/uv-cache` if the default Windows cache is inaccessible. Use the existing `.venv/Scripts/python.exe` with `uv run --no-project`.

Install the full backend/dev lock with `uv pip install --python .venv/Scripts/python.exe --require-hashes -r apps/api/requirements-dev.lock`. The original environment was missing the locked WebSocket package; it is now installed. For browser tests use `PYTHONPATH=apps/api;apps/api/tests` and a fresh project-local `--basetemp` with `-p no:cacheprovider` if elevated and sandboxed processes have conflicting temp-directory ownership. Browser tests choose independent loopback ports and terminate only their own server processes.

Docker executable: `%LOCALAPPDATA%/Programs/DockerDesktop/resources/bin/docker.exe`. The app runs at `http://127.0.0.1:3000`; `scripts/Start-App.ps1 -WithSpeech` rebuilds it, preserving data. Do not request a new unlock code just to apply changes. `scripts/Test-Services.ps1` uses temporary PostgreSQL schemas and synthetic storage/broker probes.

## Next work and remaining qualification

M06 implementation and the requested live improvements are handled. M07 finalization/data control and M08 Windows delivery follow, without treating open qualification gates as passed. Real microphone/device, representative lecture recognition, human educational-quality review, combined RAM/VRAM, cold/warm latency distributions and full-hour endurance remain open release evidence. Batching is chronological with preceding context; semantic topic decomposition and cross-topic quality are not qualified. The older optional collapsed overview work is explicitly deferred. M07 must account for selected student revisions, merged provenance and local draft purge.

Use Git history for the final local commit titled **Add streaming lecture notes and protected editing**. No push is requested. The final app rollout retains data and current unlock sessions. Future work should start from this checkpoint rather than repeating M05/M06.

Detailed behavior and evidence: [M06 implementation](docs/implementation/phase-6-m06.md). Keep this file current when handing off; do not repeat completed implementation or claim the synthetic smoke establishes release readiness.

## M07 entry increment

User now requests saved prompt profiles and removal of the access-code flow first, followed by M07 finalization and data control. Profiles are versioned, reusable copies of all three prompt fields; loading does not apply or regenerate notes until the student chooses. The loopback workspace opens through a same-origin POST with session cookies and CSRF still enforced. Startup no longer creates or requires an unlock code. Existing bootstrap database history remains inert for migration compatibility. Workspace and profile API checks pass; M07 implementation follows.
