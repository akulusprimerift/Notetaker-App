# Workspace layout and persistent recording

## Scope

This is the focused `notetaker-layout` UI and recording-navigation increment. It keeps the current project phase unchanged and does not change database selection, note-generation behavior, the theme palette, or the Study Tools feature set.

## User-visible behavior

- The workspace header stays at the top while scrolling and retains the actual recording controller, input choice, elapsed time, Start/Stop action, save status, and recovery link across library, course, and lecture views.
- With no recording lecture selected, **Record** opens a safe destination picker. The student chooses a course and lecture first; recording starts only after an explicit Start action. Lectures whose audio was removed cannot be selected for another recording.
- Recording keeps one controller mounted through same-workspace hash navigation. The Capture side section portals recovery actions, retention controls, saved segments, and playback details from that controller.
- **Notes** and **Finish** are the prominent lecture links. Transcript, Capture, Materials, Visual notes, and Study tools are quiet side links. Native links with `aria-current="page"` provide navigation semantics and browser keyboard behavior.
- The Notes section remains the main reading area and retains its compact live transcript preview. Data-removal progress and errors appear in the library sidebar; audio removal, lecture deletion, and finalization remain available from Finish.

## Follow-on boundaries

Settings relocation and broad palette/theme work remain with the accepted settings task. Flashcard and catch-up changes remain outside this increment. These boundaries preserve the shared header and lecture layout as extension points without changing those separate behaviors here.

## Verification

The browser scenario uses synthetic API responses and an oscillator-backed media stream. It exercises safe destination selection, pinned controls while long notes scroll, active capture through transcript/Capture/home/course navigation, chunk save and seal, a 400 px viewport, keyboard focus, a protected note draft, and Finish access. It does not access a physical microphone.

Executed:

- `NOTETAKER_UI_ORIGIN=http://127.0.0.1:3018 NOTETAKER_PLAYWRIGHT_DRIVER=<uv Playwright driver package> node tests/desktop/layout-recording-ui.cjs` passed. The synthetic recording created and sealed one verified audio chunk; route navigation kept the same recorder mounted.
- `bun run typecheck` passed.
- `bun run lint` passed.
- `bun run test` passed: 63 contracts, 0 failures.
- `bun run build:web` passed: optimized Next.js production build, TypeScript, and static generation for `/`, `/_not-found`, and `/capture-check`.
- `NOTETAKER_PLAYWRIGHT_DRIVER=<uv Playwright driver package> node tests/desktop/theme-contrast.cjs` passed across light, dark, pink, and blue: all 10 measured navigation and workspace text/surface pairs met 4.5:1 contrast.
- `git diff --check` passed.

`bun run verify:docs` could not run because `pwsh` is not installed in this environment. No physical microphone or native Electron recording session was used. These checks do not qualify Windows packaging or native Mac permissions, sleep/wake, or release readiness.
