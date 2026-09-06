# Phase 3: API, event, and synchronization contracts

This document defines the boundary behavior for the [architecture](phase-3-architecture.md) and [data model](phase-3-data-model.md). It is not a generated OpenAPI specification or a deployed endpoint list.

## Common rules

- Authenticate every REST and WebSocket request; authorize parent lecture/course ownership before processing IDs or serving versions.
- Mutations carry an idempotency key. A reused key with the same request fingerprint yields the existing result, after current authorization/liveness checks. A different fingerprint yields `409 Conflict`.
- Edits, seals, and proposal resolutions carry explicit expected versions; `409` returns safe current revision metadata. Missing required version preconditions yield `428 Precondition Required`.
- `401` means no valid session; inaccessible resources use a consistent `404` policy to avoid leaking existence. Schema/metadata validation returns `422`; conflicting immutable chunk content returns `409`; oversized chunks return `413`.
- API acceptance of asynchronous work returns `202` with a job/status reference. It never labels inference completed. Error bodies contain a stable code, retryability, safe message, and trace ID without lecture text or credentials.

## Representative endpoints

| Endpoint | Input and behavior | Result |
| --- | --- | --- |
| POST /session/bootstrap | One-use local bootstrap secret; same-origin check. | Owner session cookie; secret invalidated. |
| POST /courses; GET /courses | Name/default settings or listing. | Owner-scoped course data. |
| POST /courses/{id}/lectures | Title and chosen settings snapshot. | Unstarted lecture and revision. |
| GET /lectures/{id}/snapshot | Authorized consistent state. | Course/lecture summary, note/transcript revisions, independent statuses, update cursor. |
| POST /lectures/{id}/capture-runs | Acquire authorized ownership, create run/sample format. | Run ID, capture epoch, bounded grant, admission information. |
| POST /lectures/{id}/capture-takeover | Explicit request with expected capture epoch. | New run/epoch; former live owner fenced. |
| POST /lectures/{id}/capture-runs/{run}/heartbeat | Owner grant and epoch. | Current owner/lifecycle state; heartbeat alone grants no takeover. |
| PUT /lectures/{id}/capture-runs/{run}/chunks/{sequence} | Binary WAV with declared hash/size/sample metadata and grant. | Verified acknowledgement only after object validation and DB/job/outbox commit; retry returns matching acknowledgement. |
| GET /lectures/{id}/capture-runs/{run}/manifest | Compare local chunk journal with server state. | Received identities/hashes, contiguous saved coverage, seal/version, gaps, pending entries. |
| POST /lectures/{id}/capture-runs/{run}/seal | Last sequence/sample count, expected version, known gaps. | Idempotent sealed manifest or explicit conflict. |
| POST /lectures/{id}/capture-recovery | Journal inventory for an old/interrupted run, expected manifest version. | Authorized recovery plan; does not reactivate the old live owner. Conflicting/overlapping fragments remain quarantined for resolution. |
| POST /lectures/{id}/finalizations | Source/manifest settings revisions; explicit incomplete-evidence decision if needed. | A logical job or existing equivalent job; pending evidence returns actionable waiting state. |
| GET /lectures/{id}/sources/{version} | Pinned transcript version and authorized span. | Source text/metadata or unavailable; never silently substitutes the latest version. |
| GET /lectures/{id}/audio/{chunk} | Authorized read of retained object. | Stream audio from server; no public bucket URL. |
| PATCH /lectures/{id}/transcript/{segment} | Corrected text and expected version. | New human-corrected version and dependency-invalidated artifact IDs. |
| PATCH /lectures/{id}/notes/{block} | Structured content and expected block/document versions. | New protected human version or conflict. |
| POST /lectures/{id}/regenerations | Scope and pinned source/settings/base revisions. | Job that produces a new revision/proposal. |
| POST /lectures/{id}/proposals/{proposal}/resolve | Keep/replace/merge and expected bases. | New resolved revision or stale-proposal conflict. |
| GET /lectures/{id}/exports/{revision}.md | Saved detailed/overview revision. | Self-contained Markdown with source appendix, not raw audio. |
| POST /lectures/{id}/audio-removals | Explicit audio removal confirmation and expected epoch. | Deletion job; transcript/notes retained. |
| DELETE /lectures/{id} | Explicit lecture deletion confirmation and expected epoch. | Tombstone/deletion job; not immediate completed-deletion claim. |
| GET /deletions/{id}; GET /jobs/{id} | Owner-scoped progress request. | Scope-specific progress, failures, safe retry options. |

Exact request schemas and frontend adapters belong to implementation planning. State and version requirements above must survive that translation.

## Chunk identity example

```json
{
  "run_id": "run-A",
  "capture_epoch": 3,
  "sequence": 12,
  "start_sample": 1152000,
  "sample_count": 96000,
  "sample_rate": 48000,
  "channels": 1,
  "encoding": "pcm_s16le_wav",
  "sha256": "<verified-content-hash>",
  "byte_length": 192044
}
```

The byte length is illustrative for a simple two-second mono PCM WAV header; the parser validates actual file structure and limits rather than trusting the header size. Upload identity does not depend on upload time. Acknowledgements return the same immutable identity plus storage state and a manifest revision.

## Kafka physical topics

| Topic | Events | Key and consumers |
| --- | --- | --- |
| work.audio.v1 | speech.job.available | lecture ID; speech dispatch consumer group. |
| work.notes.v1 | notes.job.available; finalization.job.available | lecture ID; note/finalization dispatch consumer group. |
| lecture.events.v1 | capture state, transcript revision, note revision, deletion state references | lecture ID; diagnostic/reconciliation consumers as needed. UI correctness uses the DB update journal. |
| work.failures.v1 | job.exhausted; contract.rejected | lecture ID when valid, otherwise event ID; inspection/retry tooling. |

Start with one partition per work topic for one-student development. Increase partitions only with a migration/ordering plan and measured multi-lecture workloads. Initial local broker replication is one, so the broker is not a host-loss backup. PostgreSQL ledger reconciliation must recover pending work after broker loss/retention expiry.

Avoid a separate physical topic for every domain event. Producer acknowledgement and consumer offset settings must be explicitly configured and verified during deployment; do not infer end-to-end ordering or exactly-once effects from the topic key.

## Envelope

```json
{
  "event_id": "event-A",
  "event_type": "speech.job.available",
  "schema_version": 1,
  "occurred_at": "2026-09-05T20:00:00Z",
  "producer": "outbox-dispatcher",
  "lecture_id": "lecture-A",
  "lifecycle_epoch": 1,
  "correlation_id": "capture-run-A",
  "traceparent": "<W3C-trace-context>",
  "payload": { "job_id": "job-A", "input_revision": "manifest-7" }
}
```

Opaque IDs and trace placeholders above are illustrative. Validate event type/version, required fields, maximum size, and referenced job existence. Unknown incompatible versions become durable contract failures and are not blindly consumed. Additive optional fields are the initial compatible evolution rule; removal/meaning changes require a new version and migration.

Never put raw text, audio, source excerpts, credentials, provider URLs with secrets, or exception dumps in an event or DLQ. Failed events preserve only validated safe metadata and a payload hash/error code when the input is malformed. The consumer derives authority and actual input from the database, not the message.

## Dispatch and retry semantics

1. Notification arrives; validate envelope and check the consumer-specific inbox entry.
2. In one transaction, check referenced job and current lecture state, record inbox outcome, and make the durable scheduling effect. Commit the broker offset after that transaction.
3. Runner claims due work using a lease/attempt token. The reconciler follows the same claim path, so an extra notification does not launch authoritative duplicate work.
4. Commit output only if job attempt, lifecycle/audio epoch, and input/base revisions remain eligible. Stale results cannot mutate visible state.
5. Persist retry eligibility and failure information before emitting any retry/failure notification. Broker absence does not lose retry timing.

## WebSocket contract

The socket subscribes to one authorized lecture with `after_cursor`. Messages contain `lecture_id`, `update_seq`, `kind`, `entity_id`, and `entity_version`, with a bounded payload of authorized UI data or an instruction to fetch it. WebSocket content is private and is not copied into Kafka or telemetry.

Send updates only after their database transaction commits. The client applies increasing sequence numbers, ignores duplicate/older ones, and requests replay on gaps. If a cursor has expired, send `snapshot_required`; the client fetches a consistent snapshot then resumes from its cursor. Heartbeats are connection health, not recording or save acknowledgements.

Reauthorize on subscription and periodically/session invalidation. Deletion revokes access immediately in the authoritative state, sends an unavailable notice when possible, and ends content delivery. A lost connection cannot guarantee recall of content already received.
