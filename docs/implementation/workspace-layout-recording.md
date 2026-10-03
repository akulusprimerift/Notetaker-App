# Workspace layout and persistent recording

## Scope

This is the focused `notetaker-layout` UI and recording-navigation increment. It keeps the current project phase unchanged and does not change database selection, note-generation behavior, the theme palette, or the Flash Cards feature.

## User-visible behavior

- The workspace header stays at the top while scrolling and retains the actual recording controller, input choice, elapsed time, Start/Stop action, save status, and recovery link across library, course, and lecture views.
- With no recording lecture selected, **Record** opens a safe destination picker. The student chooses a course and lecture first; recording starts only after an explicit Start action. Lectures whose audio was removed cannot be selected for another recording.
- Recording keeps one controller mounted through same-workspace hash navigation. The Capture side section portals recovery actions, retention controls, saved segments, and playback details from that controller.
- **Notes** and **Finish** are the prominent lecture links. Transcript, Materials, Capture, Visual notes, and Flash Cards are quiet side links. Native links with `aria-current="page"` provide navigation semantics and browser keyboard behavior.
- The Notes section leads with the selected saved revision. On desktop the live transcript is a small secondary card beside the notes; on narrow screens it follows the note content. Open full transcript remains a direct link.
- Speech-model setup and processing details stay live in a compact disclosure. Missing-model and worker errors appear in its summary and full explanations and controls remain inside. Note model selection, cloud consent, prompt profiles and writing preferences remain available in the Notes settings disclosure.
- Data-removal progress and errors appear in the library sidebar; audio removal, lecture deletion, and finalization remain available from Finish. The persistent Record bar, bottom-left Settings control, keyboard navigation and pastel themes remain available.

## Follow-on boundaries

Settings relocation and the focused palette/theme refresh are described in [workspace appearance](workspace-appearance.md#settings-and-theme-follow-up--2026-10-03). Flash Cards behavior is documented in [Flash Cards](flash-cards.md). These boundaries preserve the shared header and lecture layout without changing those features.

## Verification

The browser scenarios use synthetic API responses. The Notes-focus case checks a populated saved revision and transcript at 1280×900 and 400px, Notes/Finish and side navigation, compact speech diagnostics and transcript preview, keyboard access, model selection, source links, protected draft recovery, persistent Record and contrast in all four themes. The recording-navigation check additionally uses an oscillator-backed synthetic stream; neither case opens a physical microphone.

Executed:

- `NOTETAKER_UI_ORIGIN=http://127.0.0.1:3020 NOTETAKER_PLAYWRIGHT_DRIVER=<uv Playwright driver package> NOTETAKER_NOTES_FOCUS_ARTIFACTS=<task evidence directory> node tests/desktop/notes-focus-ui.cjs` passed. The first saved-note paragraph starts at y591 in the 1280×900 viewport and y570 in the 400×900 viewport. The narrow test starts with the library collapsed, opens it to navigate home and into a course, and confirms Record stays visible while scrolling. It also covers compact transcript and processing details, model selection, source links, draft recovery, Finish, keyboard access and contrast in all four themes. The undimmed screenshots are `notes-desktop-1280x900.png` and `notes-narrow-400px.png` in the task evidence directory.

- `NOTETAKER_UI_ORIGIN=http://127.0.0.1:3020 NOTETAKER_PLAYWRIGHT_DRIVER=<uv Playwright driver package> node tests/desktop/live-transcript-ui.cjs` passed. It exercises saved/live note status, model controls, export formats at 400px, draft preservation, revision behavior and lecture deletion.

- `NOTETAKER_UI_ORIGIN=http://127.0.0.1:3018 NOTETAKER_PLAYWRIGHT_DRIVER=<uv Playwright driver package> node tests/desktop/layout-recording-ui.cjs` passed. The synthetic recording created and sealed one verified audio chunk; route navigation kept the same recorder mounted.
- `bun run typecheck` passed.
- `bun run lint` passed.
- `bun run build:web` passed.
- `git diff --check` passed.
- `bun run verify:docs` was unavailable because `pwsh` is not installed in this environment.
- `bun run test` passed: 63 contracts, 0 failures.
- `bun run build:web` passed: optimized Next.js production build, TypeScript, and static generation for `/`, `/_not-found`, and `/capture-check`.
- `NOTETAKER_PLAYWRIGHT_DRIVER=<uv Playwright driver package> node tests/desktop/theme-contrast.cjs` passed across light, dark, pink, and blue: all 10 measured navigation and workspace text/surface pairs met 4.5:1 contrast.
- `git diff --check` passed.

`bun run verify:docs` could not run because `pwsh` is not installed in this environment. No physical microphone or native Electron recording session was used. These checks do not qualify Windows packaging or native Mac permissions, sleep/wake, or release readiness.
