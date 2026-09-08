# Phase 6.7 / M07: finalization and data control

Implemented 2026-09-08, following the user-requested prompt-profile and access-flow increment. Windows application packaging remains M08; prior real-lecture and release qualification gaps remain open.

## Before M07: profiles and automatic local access

The local workspace opens automatically through a same-origin `POST /session/open`, without an access key. Existing ownership and courses are retained. HTTP-only, same-site sessions, origin checks, CSRF and idempotency still protect requests. Automatic access is limited to a loopback web origin. Startup scripts no longer issue keys or revoke existing sessions. The former bootstrap API is removed; its historical database table remains inert for additive migration compatibility.

Prompt profiles save a name plus the detail, layout and writing prompts. Profiles are owner-scoped and stored in PostgreSQL (SQLite in explicit preview). Creation/retry is idempotent; updates require the expected profile version. Loading copies fields into the lecture form; applying remains a separate decision. Historical lecture settings and notes do not change when a saved profile changes. Migration 0008 adds profiles.

## Finalization

Migration 0009 adds durable finalization requests, immutable final snapshots, audio-removal state, deletion records and object inventories. The API's background coordinator resumes pending work after restart and runs without an open browser or Kafka notification.

- Finalize closes new and in-flight audio intake. Verified audio islands, including audio after missing chunks, are scheduled for speech. Unknown tails and unsaved intervals are explicitly incomplete. Fully sealed source manifests keep their identities so corrections are not overwritten by fresh speech output.
- Finalization waits for speech and then current note output. Saved student notes remain selected. Edits made during processing require review and a new explicit finalization request; they cannot silently change the requested selection.
- Failed processing exposes a needs-attention state. Retry and **Finalize available results now** are separate actions. Available-only cancels pending jobs and saves the existing result with omissions and incompleteness visible.
- A final snapshot copies the transcript membership/text, selected notes, settings, provenance, issues and rendered export. Subsequent corrections, preferences, generation or editing cannot change it. Snapshot history provides reading and Markdown export independently of the current reading copy.
- **Reopen for late audio** explicitly reopens recovery or another segment. Recovering and finalizing again creates another snapshot; the earlier one remains unchanged. Audio removed by the student cannot be reopened.
- Unsaved browser note drafts are excluded from final snapshots; the confirmation explains this. A final snapshot is a saved state, not a quality certification.

## Audio removal and lecture deletion

Audio removal advances the audio epoch, cancels old work, pauses automatic notes and blocks recording/recovery/playback. Transcript, notes, student revisions, source text and final snapshots remain readable. A retained transcript snapshot supports corrections and explicit transcript-only note regeneration after choosing to resume notes.

Lecture deletion first writes a tombstone, advances lifecycle/audio/capture epochs, cancels jobs and clears previews. Reads, uploads and stale worker publication are fenced before physical cleanup. The deletion inventory includes every upload reservation, including unverified objects. A background pass discovers additional objects under the lecture prefix, deletes and verifies them, then removes dependent content in foreign-key order. A minimal lecture tombstone and non-content deletion/idempotency records remain to prevent recreation and explain progress.

Failed storage cleanup is retried. Completed deletions are periodically reconciled again to remove writes that landed after a previous inventory pass. Progress counts refer to objects, and completion requires an empty storage prefix rather than trusting a delete response. Audio-only cleanup keeps immutable source metadata; lecture cleanup removes transcript, settings, notes, edits, snapshots, jobs, manifests and reservations.

The browser checks owner-scoped deletion records on opening, online events and periodic refresh. It stops affected readers/recorders, revokes temporary audio URLs, and atomically purges audio journal records. Lecture deletion also purges note drafts and that tab's transcript correction. IndexedDB tombstones fence delayed draft writes or recorder setup from recreating local copies. Disconnected browsers remove their copies on reconnection; the interface does not claim they were remotely erased. Exports and backups are outside app deletion control. This is logical deletion through application/database/object APIs, not a physical-media secure-erase guarantee.

## Verification

Executed evidence and final counts are recorded in [SESSION_TRANSFER.md](../../SESSION_TRANSFER.md). Tests cover available islands, immutable snapshot/export history, late recovery, version conflicts, edits during finalization, failed notes, audio-only regeneration, deletion during upload, obsolete speech/note attempts, storage retry, and reconciliation of late objects.

The browser integration uses real Chromium, IndexedDB, Next.js, FastAPI, WebSocket and SSE with synthetic providers. It exercises all prior M06 editing/reconnect/streaming behavior plus saved profiles, a browser with no access cookie, final snapshots, audio removal, lecture deletion and a disconnected draft's purge after reconnect. No microphone access is used.

PostgreSQL tests use temporary schemas. The real object-deletion drill uses its own uniquely named synthetic bucket; it verifies deletion and inserts a late object to prove reconciliation removes it. No student lectures or data volumes are deleted by verification.

Full lecture endurance, actual device failure, representative speech quality, human educational review, Windows packaging and backup/restore qualification remain open. Chronological note batches remain the existing M06 behavior; M07 does not qualify semantic topic quality.
