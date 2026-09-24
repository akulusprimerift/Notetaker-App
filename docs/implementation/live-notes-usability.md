# Live notes and lecture deletion — 2026-09-23

Active phase: **6.8 / M08 — Standalone Windows distribution**.

## Behavior

Study notes automatically follows the latest saved generated revision without a “Show updated notes” action. The existing live draft shows model prose before validation and structured publication. The desktop provider bridge now forwards incremental OpenAI/Anthropic API and ChatGPT/legacy Claude subscription text through authenticated NDJSON to the note worker and existing fenced SSE preview. Local Ollama retains its streaming path. Interrupted streams cannot publish a completed response; final source/format validation remains authoritative. Queue/warm-up status still appears when the model has not produced any text.

Student revisions remain selected, with comparison, keep/merge/replace and undo for generated suggestions. Unsaved drafts retain their base revision and conflict handling while the reader advances. “Worth reviewing” dismissal is now lecture-scoped and persists across revisions, tab changes and reloads until reopened.

A Delete lecture action in the lecture header opens the existing permanent-deletion confirmation under Finish. It is disabled during capture/saving or transcript editing. Confirmation uses the existing authenticated, CSRF/idempotency/cursor-fenced deletion service, tombstones and browser cleanup. Deletion removes cached sidebar links and returns to the library from any lecture tab. No migration or existing student-data modification is involved.

## Executed checks

- Full existing backend suite: 233 passed, 1 service-only skip. Four new desktop-bridge streaming/error tests passed separately.
- 60 JavaScript contracts and 18 desktop tests passed. New tests hold provider completion until a preview is observed, split UTF-8/SSE frames at byte boundaries, and reject truncated/tool streams.
- Chromium with synthetic responses passed automatic saved revisions, persistent dismissal/reopening, preserved unsaved draft, deletion cancel/confirm and sidebar cleanup; prior live transcript, retained recorder, help and narrow-theme checks also passed.
- Typecheck, frontend lint, Python lint and standalone production web build passed.
- The first desktop-stream test failed during duplicate test cleanup; cleanup was corrected and the suite rerun successfully. A targeted backend invocation named a nonexistent test file and ran no tests; the full suite above supersedes it.

No microphone, model download, paid inference, installed-library access or push. Live provider entitlement/inference, educational quality, installed upgrade and earlier M08 release gates remain unqualified. The production web bundle also passed the same browser flow plus isolated hydration, capture assets and inventory/hash verification. Packaging results will be recorded below.


## Packaged checks

The frozen service built successfully and passed native-host PostgreSQL/API startup and write/read in `.local/host-smoke-e9d94a44d42f494fb61d977dd415a999`. The staged production web bundle is `.local/desktop-web/8c58fe9e-8d69-4e68-90c2-ce30c3d395e4`; runtime: `.local/notes-fix/runtime`. Unchanged vendor files were verified against their prior SHA-256 manifest before reuse.

The actual packaged Electron app passed first-library setup, PostgreSQL migrations, synthetic PCM verified storage, normal Quit/reopen and identical audio readback in `.local/standalone-smoke-e3c205fa-b236-463f-bc59-c4c3a08cde4d`. Renderer isolation remained enabled. Packaged service SHA-256 matches the tested frozen executable: `789195F46B90A4107AD7B813B2C4EFCEF9C50C373693DACAE0843A3A829937A3`.

The legacy Python browser scenario's revision expectations were updated but that full scenario was not rerun; the executed browser evidence is the current Chromium synthetic flow described above. Documentation/whitespace checks passed. No installed app or student library was changed.


## Delivery

Unsigned Windows x64 installer: `.local/notes-fix/installer/Notetaker-0.1.0-Windows-Standalone-Setup.exe`, **397,873,440 bytes**, SHA-256 `8C4808EC2A7E66A7E6833A3D9EC60E180B7EF46AAAE1D9D69AB3CB8CBC729157`. Installer build exited successfully. Close Notetaker normally before installing and retain the existing library selection. Actual installed upgrade and live connected-provider inference remain separate qualification steps.

Source increment: `7dbce42`. No push or automatic installation was performed.
