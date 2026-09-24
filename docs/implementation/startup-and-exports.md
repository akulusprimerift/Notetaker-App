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

Unsigned Windows x64 installer: `.local/startup-export/installer/Notetaker-0.1.0-Windows-Standalone-Setup.exe` (**407,266,757 bytes**), SHA-256 `035508E527CCB4567231D712409CD818E99D991FEFAD1D3BAB3B43B0913B4772`. Build completed successfully. Close Notetaker normally before installing and retain the existing library selection.

Runtime: `.local/startup-export/runtime-release`; web bundle: `.local/desktop-web/dc4079ea-af2c-410f-a972-f9d659506a62`, build ID `O3QDYD1z3buM0Hxk9K1BD`. All 1,610 reused vendor files were verified against the previous runtime manifest. The newly frozen and packaged service executable matches SHA-256 `EAFF0B3E46EB6ED7213FA615E57417C27E070AE63D2610384E604AB10B71ED57`. Final packaged desktop files match source, including the setup contrast correction. Final isolated web hash/hydration/capture-asset checks passed.

The packaged app passed initial library setup, native window-controls overlay/drag region, Blue theme selection/persistence, synthetic verified audio save, normal Quit/automatic reopen, identical audio readback, and DOCX/PPTX/TXT downloads from a finalized synthetic lecture. Profile: `.local/standalone-smoke-baeed003-8e10-42a0-80c2-f97fed545b75`. Exported Office files reopened through their document libraries and retained the lecture title. Packaged screenshot inspected.

A final Blue setup-button contrast correction was then checked in Chromium across all four palettes (at least 4.5:1), and the installer was rebuilt. The subsequent full repeat in `.local/standalone-smoke-694dccec-6351-4458-a64a-34fe89ed5083` correctly refused port 3000 because the user's installed Notetaker was running. That repeat was stopped; the installed app and its services were left untouched. Earlier full packaged behavior evidence applies to the unchanged runtime/workspace; final setup CSS is verified separately. The smoke test now reports startup failures promptly instead of waiting for a ready message.

Implementation commit: `ca90cd7`; delivery/contrast evidence is committed separately. No automatic installation, push, microphone access or existing student-library modification. Real-device audio, Office application visual review, installed upgrade, accessibility, human quality, endurance, coordinated restore and signing remain open.
