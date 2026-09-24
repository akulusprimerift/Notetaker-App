# Workspace appearance — 2026-09-24

Active phase: **6.8 / M08**. This increment implements the requested visual refresh only. Note generation, speech processing, recording, revision protection, source content and service code are unchanged.

After user review, the workspace uses installed TikTok Sans for cleaner geometric headings and interface copy, with Lemon Milk reserved for small section labels. The initial Wayfinder heading treatment was removed. Local-only font faces include readable fallback families; no font assets are copied, bundled or downloaded. Generated note sections, streaming text, transcript passages/previews/corrections, source quotations and note draft/comparison text keep their existing system reading font; code retains monospace.

Pink and Blue are available alongside Slate and Midnight in the existing theme selector and persist across reloads. Each new palette includes all five user-supplied colors, with darker supporting text colors for contrast. Rounded surfaces, translucent cards, background glow and blurred navigation draw on the supplied reference. Reading surfaces stay solid. Lecture panels slide horizontally for 380 ms according to tab order without changing component keys or recorder ownership. Capture expansion has a matching reveal. Reduced-motion preferences disable these animations.

The second appearance pass increases spacing between cards and page sections, removes truncated tab descriptions in favor of clear labels with descriptive tooltips, and adds a sliding glass selection highlight that follows responsive tab layout. Library/course/lecture navigation has a 420 ms entrance without remounting content. Glass surfaces now use lower-opacity fills, blurred colored backgrounds, soft shadows and luminous edges. These remain restrained around the solid note/transcript reading surfaces.

## Executed evidence

On Windows with local Chromium and synthetic API responses:

- `bun tests/desktop/appearance-ui.cjs`: all four themes persist; actual TikTok Sans font rendering confirmed through Chromium's platform-font inspection; streaming text retains system font; 400px layouts fit; forward/backward animation direction and reduced motion pass; selection highlight aligns with its tab; glass blur is present; recorder DOM survives tab changes. Dashboard and lecture screenshots saved under `.local/appearance-review` and dashboard/narrow/lecture images visually inspected.
- `bun tests/desktop/theme-contrast.cjs`: eight nested text/surface pairs pass 4.5:1 in each of four themes. This is a focused contrast check, not a full accessibility audit.
- Existing `live-transcript-ui.cjs` against the isolated development server: live transcript/notes, automatic revisions, persistent review dismissal, draft preservation and lecture deletion pass.
- `bun run test`: 60 contracts pass; `bun run test:desktop`: 18 tests pass.
- Frontend lint, typecheck and production web build pass. Documentation and whitespace checks pass.

The refinement reran appearance, contrast, existing live transcript/note flows, frontend lint/typecheck/build and documentation/whitespace checks. The 60 contract and 18 desktop-test results above are from the first appearance pass; those unrelated suites were not repeated for the refinement.

No student-library access, microphone use, backend changes, model downloads, provider calls, installation or push. Backend tests were not rerun for this presentation-only increment. The Windows installer has not been rebuilt; the existing installed binary will retain its previous appearance until a new package is prepared and installed. Fonts on other machines depend on their installed local faces; demo/commercial fonts are not redistributed.

Next delivery work: package this renderer into the standalone installer using the existing runtime, then qualify the installed upgrade with the existing library retained. Earlier M08 hardware, endurance, accessibility, human quality and release gates remain open.
