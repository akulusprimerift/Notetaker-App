# Paged notes and window refinements

Active phase: **6.8 / M08**. Requested 2026-09-24.

## Section 1 — Paged saved notes

Saved generated and selected student revisions flow through a bounded reader (320–640px, responsive to window height). Numbered sections continue the original text, including oversized passages/code, without changing the stored revision or exports. Previous/next, keyboard arrows/Home/End and native horizontal swipe/scroll navigate with smooth settling; reduced motion is immediate. Resize/font/content changes recalculate pages while retaining the current number where possible. Sources and protected editing stay available.

Executed on Windows Chromium: synthetic long notes, oversized passage, code, bounded height, 400px/1440px layouts, exact text preservation, numbered/keyboard navigation, last-page source opening and reduced motion. Screenshot `.local/note-pages.png` inspected. Frontend typecheck/lint passed. The test caught narrow-screen intrinsic sizing and an absolutely positioned source label escaping the column viewport; both were fixed and passed on rerun. No backend changes or student-data access. Full build and broader regression checks follow the remaining sections.

Next: integrate the Windows overlay into the workspace header, animate the sidebar, then strengthen glass surfaces and startup progress. Installer is unchanged; existing M08 release qualification gaps remain open.
