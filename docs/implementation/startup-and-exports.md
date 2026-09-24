# Startup, window appearance and portable note exports

Active phase: **6.8 / M08**, 2026-09-24.

Returning users see a themed, reduced-motion-aware loading view while their saved native or Docker library starts. First launch still requires an explicit library choice. Failed startup reveals the setup controls; Workspace settings remains available during use. Setup shares the four palettes and includes model preparation and first-lecture steps. No model downloads or automatic library migration are introduced.

The Windows title bar uses Electron's native window-controls overlay with a draggable app strip and persisted theme colors. Native minimize/maximize/close and existing recording-aware close behavior remain intact. Rounded window corners follow Windows support (Windows 11 in this environment); maximized windows follow normal OS behavior. A persisted Hide/Show library control removes only the sidebar, preserving the recorder. Slate reading/capture surfaces now share the glass treatment.

Export Markdown is prominent above note preferences. More formats provides DOCX, PPTX, TXT and existing HTML (with browser print to PDF). The guide explains file use, explicit external uploads and a copyable source-constrained study prompt. Exports use the selected saved generated/student revision; unsaved drafts are excluded and labeled. Finish exposes the latest immutable snapshot and historical snapshot exports.

All formats share the existing owned-lecture/revision/snapshot checks and deletion fences. DOCX and slides decode escaped Markdown safely into text, retaining source appendices and literal code. Word has heading styles. Slides are a paginated full-text reading deck, not generated summaries: fixed row/column limits, wide-Unicode wrapping and continuation pages avoid truncation. Supported diagrams remain visual in HTML; other formats preserve their text descriptions. No provider is invoked. New document dependencies are hash-pinned across all runtime locks; their templates and notices are included in frozen packaging.

## Executed checks

- 60 JavaScript contracts and 21 desktop tests, including first launch, returning native startup, failure recovery, theme persistence/allowlisting and foreign-frame rejection.
- Full SQLite backend suite: 245 passed, 1 service-only skip. The final wide-Unicode pagination adjustment then passed all 9 focused export tests (generated/student revisions, source retention, frozen snapshots, unsupported/missing/unauthenticated requests, long content, literal code and wide characters).
- Chromium appearance, retained-recorder/sidebar persistence, existing live transcript/note/draft flows, export controls/help/Escape, 400px layout, setup/loading/failure/help, all four palettes and reduced motion. Eight focused contrast pairs pass 4.5:1 in each theme. Screenshots under `.local/appearance-review`, `.local/setup-*.png`, `.local/startup-loading.png` and `.local/export-mobile.png` were inspected.
- Frontend typecheck/lint, Python lint, normal web build and standalone web build passed. Initial export tests caught escaped punctuation; safe Markdown parsing fixed this. A startup test double initially tried setup-only IPC after workspace navigation; its fixture was corrected. One browser command used the wrong default test port; it passed against the correct isolated server.

## Delivery and remaining gates

Windows package rebuild and packaged synthetic verification are in progress. Record exact output and evidence here after completion. No automatic installation, push, microphone access or existing student-library modification. Real-device audio, Office application visual review, installed upgrade, accessibility, human quality, endurance, coordinated restore and signing remain open.
