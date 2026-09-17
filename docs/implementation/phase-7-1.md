# Phase 7.1 — Note usefulness

Implemented increment, 2026-09-15; active work moved to Phase 7.3 on 2026-09-16. Mark Important, Catch Me Up and course terminology are implemented. Engineering checks below do not establish educational usefulness or release readiness. Earlier M08 hardware, install/upgrade, accessibility, endurance and restore gates remain open while this independent work proceeds.

## Student workflow

- **Mark Important** beside the recording controls stores the recording and sample timestamp. The timestamp is held across a failed request and explicit retry; audio recording is independent. A stopped lecture can bookmark the end of its saved recording. Study tools offers review, removal and undo with version-conflict reporting. Marks are student bookmarks, not claims of professor emphasis, and never alter source or note history.
- **Catch Me Up** in Study tools displays up to four complete saved note passages for the chosen recent interval of the latest transcribed recording. It uses the selected student revision when present and keeps source inspection/audio links. Passages tied to superseded transcript versions are omitted. When notes are unavailable, up to three exact transcript excerpts are labelled clearly. No model request, paraphrase or automatic replacement of the reading view occurs. Bookmarks retrieve the minute leading to the marked moment; processing lag and missing-source warnings stay visible. Detailed notes are unchanged.
- **Course terminology**, on the course page and Study tools, accepts up to 40 unique names/terms, 60 characters each and 1,000 characters total. Saves append an immutable version. Conflicts preserve the open draft; loading saved terms allows comparison before explicit replacement or resaving. An empty list clears hints for future batches.
- Terminology is pinned when each speech window is scheduled, passed as faster-whisper's `initial_prompt`, and recorded in inference metadata. Queued windows and previous transcripts/corrections do not change. Hints influence recognition; they are not evidence a word was spoken and can introduce errors. See the [adapter's documented interface](https://github.com/SYSTRAN/faster-whisper/blob/master/faster_whisper/transcribe.py).

## Persistence and boundaries

Migration 0014 adds student marks with recording ownership and sample bounds; 0015 adds immutable course-term versions and an empty hint snapshot on existing speech windows. Both are additive and refuse destructive downgrade. New writes retain session ownership, CSRF, idempotency and expected-version fences. Term writes share the owner/course mutation locks; speech scheduling reads immutable versions without a reverse lock dependency. Lecture deletion removes marks and window hints, and course deletion removes course terminology. Final snapshots freeze active bookmarks with an explicitly labelled student-bookmark export appendix.

The existing Docker/PostgreSQL library is preserved. No real student data was migrated, no microphone used, no model downloaded and no provider inference invoked during verification. Pending unsaved marker retries are kept only while the lecture component stays open; unsaved terminology drafts are kept in the open form, not across app restart. Catch-up is a bounded excerpt reader, not a validated semantic summary.

## Executed evidence — Windows development environment

- Backend suite: **185 passed, 1 skipped** on fresh SQLite test databases, including migrations. The skipped test requires real PostgreSQL/object services; these were not exercised in this run. Nine new study/terminology tests cover marker idempotency, ownership and bounds, removal conflicts/undo, corrected-source exclusion, student revision selection, immutable final snapshots, deletion, term validation/conflicts, pinned future-window hints and the actual adapter call with a synthetic model. Two existing dependency deprecation warnings remain.
- JavaScript contracts: **60 passed**; desktop tests: **12 passed**, including full paginated/hidden model catalog requests and disconnect with unavailable clients.
- Chromium against the actual React workspace with synthetic API responses: marker failure/retry retains timestamp and request ID; catch-up source text/audio controls and stable reading; remove/undo; glossary conflict preserves draft; Midnight and 400px layout. Screenshots inspected locally under `.local/study-review`.
- TypeScript, frontend lint, Python lint, production web build, documentation links/coverage and whitespace checks passed. Nine study/terminology tests passed again after the final source-order and saved-boundary adjustments. Unsigned Windows x64 NSIS packaging also passed; selected packaged feature/migration sources match the working files. Installer hash and qualification limits are recorded in the session transfer.
- Account browser checks passed for refresh and both subscription disconnect controls. The existing UI mock initially lacked the new terminology response; its fixture was updated and the check rerun successfully.

## Provider follow-up before this phase

Commit `47c5b9f` loads every page of the official ChatGPT/Codex catalog with hidden models included, adds refresh and visible model IDs, and ensures local disconnect works even if official-client logout fails. An unconfirmed logout is reported. Legacy Claude subscription rows can also be disconnected. This does **not** provide every model offered on the consumer ChatGPT website. New Claude subscription login remains unavailable without Anthropic approval. Live account entitlement and successful inference across models remain untested; never represent catalog discovery as proof of every model's availability.

## Remaining qualification and next work

Review usefulness with representative course material: mark actual important moments, assess whether catch-up preserves necessary context/qualifications, and compare terminology accuracy with and without hints. Do not treat synthetic tests as a learning-outcome or real-speech result. Phase 7.2 is not started. Follow the user's ordering: remaining selected Phase 7 work, standalone Windows distribution, then macOS. Existing release gates remain unchanged.
