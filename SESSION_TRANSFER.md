# Session transfer

Updated: 2026-09-09. Current increment: **Phase 6.8 / M08 — Electron Windows application**.

## Latest checkpoint

The user requested syllabus/curriculum and PowerPoint uploads before Electron Windows delivery, streaming regeneration, installed local model discovery, tests and local commits. Implemented and verified in local commits: shared-workspace `8580df1` initial materials, `9ba7842` ordered bounded evidence, `71ea732` PDF extraction and mixed transcript/slide batches, `fa0c175` Electron host/installer, and `cb3bec5` existing-workspace reuse and installed-app evidence. See [materials evidence](docs/implementation/course-materials.md) and [M08 evidence](docs/implementation/phase-6-m08.md).

Final artifact: `.local/desktop-dist/Notetaker-0.1.0-Setup.exe`, 111,595,802 bytes, unsigned x64 NSIS. SHA256 `3D3EB8E9ABB177B81D22C8D027B21520DC93DB7FB8F14F0A23F39E590BD91448`. Installed test copy: `.local/desktop-install/Notetaker.exe`; a Notetaker Start menu shortcut exists. Final rebuild, silent install/reinstall and installed-executable smoke passed; reinstall retained the isolated `.local/desktop-smoke-profile` configuration. Smoke verified sandbox/isolation, setup authority, separate setup, outage reporting, existing-workspace selection, local model discovery, window hide/show and synthetic journal recovery. No microphone access.

Final SQLite regression: 149 passed, one service-only skip. Earlier PostgreSQL run: all 148 pre-PDF tests plus real storage/broker probes passed. Final Chromium upload/stream/edit/reconnect/lifecycle regression passed. All 60 JavaScript contracts, two desktop policy/model tests, typecheck, ESLint, Ruff, production build and documentation checks passed. Docker rebuild/rollout passed; existing data volumes retained and all services healthy. Qwen3 4B synthetic transcript-plus-slide generation produced valid source-separated notes in 45.5 seconds with 190 preview callbacks; first callback was empty, so first-visible-prose latency is not qualified. See `evaluations/reports/m08-material-smoke.json`.

Windows prerequisites are Docker Desktop Linux containers, PowerShell 7 and Ollama. Setup's **Use existing workspace folder** can select `C:/ezNote/Notetaker App` to reuse the existing library when starting services. Creating a separate desktop library requires an explicit choice. No model weights were downloaded, no external inference was used and no Git push was performed.

Exact next work: M08 release qualification remains open—clean-machine prerequisite/install checks, versioned upgrade/uninstall retention, signing, automated coordinated backup/restore with deletion-journal replay, full-hour endurance and accessibility. Real microphone/device qualification and human lecture-quality review remain blocked on the user's synthetic-only testing preference and representative review inputs. Do not call this development installer release-ready. All requested implementation changes in this session are committed; see Git history for the final evidence-only commit.

## User request and working rules

The user asked to first add saved prompt profiles and remove the single-use access key, then implement finalization and data control: coordinated final processing, immutable snapshots, incomplete results, retained history, audio/lecture deletion, epoch fencing, object reconciliation and browser-copy purge.

Read [AGENTS.md](AGENTS.md), [README.md](README.md), [project phases](docs/project-phases.md) and [M07 implementation](docs/implementation/phase-6-m07.md). Use Bun and uv. Synthetic audio only; no microphone access. Preserve unrelated local data. Commit locally; do not push. Do not confuse implemented behavior with human quality, device durability or Windows release qualification.

## Completed entry increment

Local commit `ce0bb63` — **Add saved prompt profiles and open local workspace without codes**.

- Migration 0008 adds owner-scoped prompt profiles with all three prompt fields, names, expected-version updates and idempotent creation.
- Profiles load into the lecture form; applying/generating remains explicit. Historical settings are unchanged.
- `/session/open` opens the single local owner without a code. Existing courses and sessions are preserved. Same-origin POST, local-only origin, HTTP-only/same-site session, CSRF and ownership protections remain. The bootstrap endpoint and startup-code flow are removed; the old table remains inert for additive compatibility.
- Browser validation subsequently caught an extra-fields bug in profile submission; the M07 changes include its correction.

## M07 implementation

- Migration 0009: finalization requests, final snapshots, audio-removal flag, deletions and object inventory.
- The API background coordinator resumes finalization/deletion work after restart, independently of browser connection and Kafka delivery.
- Finalize closes audio intake, processes all verified islands, finishes current notes, and freezes transcript, selected notes, settings, issues and Markdown export. Missing data and failures are explicit. Student edits during finalization require review/retry. Available-only creates an incomplete snapshot and cancels pending work.
- Existing sealed manifests and corrected sources are retained. Reopen for late audio permits recovery into a new final revision without mutating earlier snapshots.
- Audio removal fences old uploads/speech/note attempts and pauses generation; transcript, notes, source text, edits and snapshots remain. Retained transcript corrections and explicitly resumed transcript-only generation work.
- Lecture deletion fences reads/writes immediately, then reconciles all reserved/discovered objects and deletes dependent database content. Minimal tombstones and non-content receipts remain. Storage failures retry; completed prefixes are periodically rescanned for late writes.
- Browser deletion polling purges IndexedDB audio, full-lecture note drafts and tab-local transcript corrections. Local tombstones fence stale writes. A disconnected browser keeps its copy until reconnect and then purges it. Temporary audio URLs are revoked. Exports/backups and physically remnant disk blocks are outside logical app deletion.
- SSE distinguishes deleted content from an expired session, preventing reconnect cleanup from mistakenly returning to the workspace-opening screen.

## Verification checkpoint

- 144 backend tests passed on PostgreSQL 17.11 in isolated schemas, including real object deletion and late-object reconciliation in a separate synthetic bucket. Synthetic SeaweedFS readback and Kafka round trip passed.
- Final full SQLite run: **143 passed, one skipped** (the real-object drill runs in the PostgreSQL service check). A subsequent finalization wording regression run passed 11 lifecycle tests with that same one service-only skip.
- 60 JavaScript contracts passed. Type checks, ESLint, Ruff, production Next.js build, whitespace checks and documentation verification passed (194 local file links, 32 scenarios, eight milestones, six open gates).
- Chromium integration passed: all previous M06 reconnect/edit/stream behavior, saved profiles, no-cookie access, immutable snapshot reading, audio removal, lecture deletion and disconnected-draft purge on reconnect. The final rerun after UI placement and recorder cleanup changes passed. Screenshots inspected: `.local/m07-finalization.png` and `.local/m07-browser-mobile.png`.
- Local Docker rebuild/rollout passed; API, web, speech, notes and storage services are healthy. Existing student data volumes are retained. The final API/worker refresh applies clearer incomplete-result wording.

## Environment

Bun 1.3.10: `.local/tools/bun/bun-windows-x64/bun.exe`; add its directory to PATH. uv is installed; set `UV_CACHE_DIR` to the project's `.local/uv-cache` and `PYTHONUTF8=1` on Windows. Use `uv run --no-project` with the existing `.venv`. Set `PYTHONPATH=apps/api;apps/api/tests` for browser tests.

Run backend tests with `uv run --no-project python -m pytest apps/api/tests -q`. `scripts/Test-Services.ps1` uses temporary PostgreSQL schemas and synthetic storage/broker probes. The browser test starts isolated loopback API/Next ports and uses synthetic providers; use a fresh project-local `--basetemp` with `-p no:cacheprovider` to avoid Windows temp ownership conflicts. Only its own subprocess tree is stopped.

Docker: `%LOCALAPPDATA%/Programs/DockerDesktop/resources/bin/docker.exe`. Start/apply with `scripts/Start-App.ps1 -WithSpeech` (no unlock-code parameter). App: `http://127.0.0.1:3000`. No microphone, cloud inference, model download or Git push was performed.

## Local commits

The entry increment is `ce0bb63`. During verification, the shared workspace received commit `33a0da3` (titled “Phase 6.6”), containing the M07 implementation; it was preserved. The final local follow-up records evidence and clarifies incomplete-result wording. Use Git history for its exact hash. No push was performed by this task.

## Prior checkpoint and next work

M06 commit `ea5c7fa` implemented protected edits and genuine live streaming. Keep its evidence in [M06 implementation](docs/implementation/phase-6-m06.md) and [real-model synthetic smoke](evaluations/reports/m06-live-smoke.json). Its final synthetic 60-second input gave first transcript at 12.14 seconds and streamed prose at 57.67 seconds; those were not full-hour performance qualification.

M08 Windows host/installer, service lifecycle, upgrade/backup/restore and release qualification follow M07. Actual microphone/device failure, representative lecture recognition, human educational-quality review, RAM/VRAM/cold-warm distributions and full-hour endurance remain open. Optional collapsed overview and semantic topic decomposition remain deferred. M07 does not authorize deleting existing student lectures as a verification shortcut.

## Native Windows change (2026-09-09)

The user selected a browser-free native Windows rebuild. M08 remains active. Course deletion now tombstones the course and all children atomically, checks the reviewed lecture list, and uses existing durable audio deletion reconciliation. Slate/Midnight themes and revision-specific dismissible review notices are implemented in the existing development UI. Two new deletion tests, all 60 JavaScript contracts, typecheck, ESLint and Ruff passed. Native Qt Widgets delivery with bundled services is in progress; the old Electron installer is not the requested final deliverable.
