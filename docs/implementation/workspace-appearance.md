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

Next delivery work after the packaging result below: qualify the installed upgrade with the existing library retained. Earlier M08 hardware, endurance, accessibility, human quality and release gates remain open.

## Blue theme pre-packaging review

The requested Blue palette is implemented throughout the shared renderer, including the updated geometric typography, glass cards, spacing and navigation. Its primary-button hover now darkens instead of brightening so white text retains at least 4.5:1 contrast; native checkbox/radio accents also follow Blue.

Executed on Windows: the expanded appearance browser check passes all seven lecture destinations at 1440px and 400px, course creation and Accounts & API keys dialog rendering, Blue hover contrast, theme persistence and the previous font/animation/recorder checks. Synthetic empty-state fixtures supply learning, terminology and account inventories; initial test attempts omitted those response shapes and incorrectly waited for Capture's empty content panel instead of its persistently mounted recorder. These test-harness assumptions were corrected before the successful run. No student data, microphone, provider or model was used. Dashboard, materials, study tools and account screenshots were visually reviewed. Focused four-theme contrast checks, lint, typecheck and production build pass. Documentation/whitespace checks pass. Installer remains unbuilt for this appearance increment.

## Installer delivery — 2026-09-24

The appearance increment is now packaged. Unsigned Windows x64 installer: `.local/appearance-package/installer/Notetaker-0.1.0-Windows-Standalone-Setup.exe`, **397,878,582 bytes**. SHA-256: `8E6AA9B2FFF8636E67B881EA801B3CFAD34E31785E330E77C8FFE8A75EB2D7CA`. Close Notetaker normally before installing and retain the existing library selection. No automatic installation or push was performed.

The new standalone web build is `.local/desktop-web/eb709f56-a045-48ac-9650-40b1b361f3bc`, build ID `KibrVjYnQ54yljghxi0-h`. Runtime: `.local/appearance-package/runtime`. All 4,957 non-web files from the previous verified `.local/notes-fix/runtime` were checked against its manifest before reuse and again after copying. Backend and desktop sources have no changes since `7dbce42`; no new frozen-service build was needed. The refreshed manifest inventories 6,198 files. Packaged service SHA-256 remains `789195F46B90A4107AD7B813B2C4EFCEF9C50C373693DACAE0843A3A829937A3`; staged/packaged web manifests match at `B12EEF243BC6F1310B815D2C098564DC8E75762E77DE085C361D7DFA1B186BB6`.

Executed for delivery:

- `bun run prepare:desktop-web`; isolated bundle smoke confirms manifest hashes, hydration and all five capture assets.
- Appearance and existing live transcript/note browser checks pass against the staged production server, using synthetic API responses.
- 60 JavaScript contracts and 18 desktop tests pass.
- `bun run build:desktop --config.directories.output=.local/appearance-package/installer` with `NOTETAKER_NATIVE_RESOURCES` pointing to the staged runtime completes successfully.
- The actual packaged `win-unpacked/Notetaker.exe` passes fresh-library setup/migrations, verified synthetic PCM save, normal Quit/reopen, preserved course and identical audio readback, Blue persistence/Pink selection, and renderer isolation. Profile: `.local/standalone-smoke-c066b215-fbea-4098-a8a6-e773444cd4d4`; packaged Blue screenshot inspected.
- Documentation and whitespace checks pass. Previous renderer lint/typecheck checks remain applicable; no renderer changes were made during packaging.

The first packaged smoke attempt exposed Bun constant-folding `typeof require` in the callback before Playwright sent it to the renderer. The check now sends the expression as text for actual renderer evaluation; the rerun confirms isolation. No application isolation setting was changed. The first isolated test profile is retained.

The executable is unsigned. Clean-machine installer execution, installed-library upgrade, real microphone, human note quality and endurance remain separate qualification gates. This packaging uses existing selected-model behavior, changes no student library, and redistributes no local display-font files or model weights. Implementation commits: `bf4ce96`, `e708588`, `dfc51db`; packaging evidence and updated smoke coverage are committed separately.
