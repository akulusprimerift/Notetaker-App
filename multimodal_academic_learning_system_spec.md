# Notetaker App: consolidated product and technical specification

Version: 0.4 • Date: 2026-09-07 • Status: recording and saved-audio transcription implemented; Windows desktop delivery required before release.

Implementation update: M01 private workspace and M02 recording/recovery have real-service evidence. Phase 6.3 / M03 adds local saved-audio transcription, source playback and protected corrections with synthetic speech verification. Detailed notes and the installable Windows shell remain planned. Actual microphone, representative lecture quality and full release qualification remain open.

**Primary promise:** turn dense lectures into detailed, trustworthy, editable notes that a student can study from. Transcription and note quality are the project's highest priorities.

**Product loop:** Capture → Transcribe → Organize → Verify → Study from the notes.

## 1. Authority and current evidence

This specification consolidates product-development Phases 1–5. It supersedes the first-release scope and zero-based build phases in the [original v0.2 specification](docs/archive/original-spec-v0.2.md) and [original architecture](docs/archive/original-architecture-v0.2.html). Those files are preserved unchanged as historical references. Their broader learning/platform ambitions remain future options, not a mandatory first-release checklist.

Use this document for current scope and decisions, the [implementation roadmap](docs/implementation/phase-5-roadmap.md) for execution order and gates, and the [architecture artifact](multimodal_academic_learning_system_architecture_v2.html) for a visual overview. The artifact retains its existing filename for link continuity but displays consolidated version 0.4. The [reconciliation record](docs/implementation/phase-5-reconciliation.md) records conflicts and resolutions.

The detailed [student workflows](docs/product/phase-2-student-experience.md), [architecture contracts](docs/architecture/phase-3-architecture.md), [data model](docs/architecture/phase-3-data-model.md), [API/event contracts](docs/architecture/phase-3-api-events.md), and [AI pipeline](docs/ai/phase-4-pipeline.md) are incorporated by reference. Their historical phase-status observations are superseded by measured later evidence; they do not imply an implementation exists. If an implementation needs to change a contract, record the decision and update its affected specification, tests and acceptance mapping together.

Executed evidence now includes real PostgreSQL application tests, synthetic browser/audio recovery, storage restart checks and local synthetic speech trials, alongside architecture/AI contract tests and earlier note trials. [Phase 4 results](docs/ai/phase-4-results.md) record two structurally valid outputs out of three v1 cases, a rejected coverage mismatch, and an improved correction-only v2 trial. Note generation took 66–214 seconds per short case. No local live configuration, real-audio STT accuracy, human acceptance, or complete lecture workflow has been qualified. G01–G06 in the roadmap preserve these unresolved requirements.

Implementation update (2026-09-07): the [M04 increment](docs/implementation/phase-6-m04.md) makes a user-selected local LLM write notes automatically from the saved transcript and refresh them after corrections. Students do not have to manually author the notes. Long-lecture topic processing remains required; the bounded first increment does not close M04. Optional OpenAI/ChatGPT and Claude connections are planned in Phase 7 through supported provider credentials, with explicit cloud processing and protected Windows secret storage; consumer account/subscription compatibility is not assumed.

## 2. Audience, environment and operating boundaries

- Initial domain: computer science, algorithms and code, selected by the user. English, one student's private workspace and 45–60 minute endurance fixtures are initial assumptions, not permanent course/language/duration limits.
- Delivery target: an installable Windows desktop application with its own window and Start menu entry, required by the user on 2026-09-07. The browser app is the development preview. M08 owns desktop packaging, local service startup/shutdown, storage locations, upgrade preservation and clean-machine installation checks. Select and record the desktop host and service-distribution approach before packaging; no desktop runtime is qualified yet. Narrow layouts must support reading/editing; phone recording and pairing remain deferred.
- Observed host: Intel i7-13700H, 20 logical processors and approximately 32 GB RAM. The note trial reported zero VRAM residency. This is not a minimum hardware specification or proof that no GPU exists. Docker/Python availability has been verified for the local development setup; sustained simultaneous model workloads remain unqualified.
- First supported privacy mode: Fully Local. Record now, process later changes scheduling, not privacy. Downloading a model is provisioning; lecture processing uses only configured local providers. Never silently switch to external inference.
- Start a new lecture/capture only with an authenticated server-created run and working persistence admission. An already authorized run can journal locally during a connection outage. Starting a brand-new offline lecture is outside the first release.
- No device-sleep capture promise, host-loss redundancy, automatic backup, or unlimited browser storage claim. Show measured capacity, gaps, backlog and actual retained data.

## 3. Required product behavior

| ID | Required capability | Acceptance boundary |
| --- | --- | --- |
| CAP-01 | Course/lecture organization | Create, save, reopen and recover a private lecture with its exact note/transcript revisions and issues. |
| CAP-02 | Reliable capture | Start/stop once, distinguish capture/local/server save states, retry/reconcile audio, fence competing recorders and disclose unrecoverable gaps. |
| TRN-01 | Timestamped transcription | Ordered versioned speech, provisional/stable/final status, technical-term uncertainty and protected student corrections. |
| NOTE-01 | Detailed study notes | Preserve recoverable definitions, reasoning, algorithms, code/equations, worked steps, conditions, exceptions, emphasis and corrections with coherent topics. |
| NOTE-02 | Live and final notes | Incremental output with visible delay; refined final revisions only after evidence accounting; keep usable prior notes on failure. |
| NOTE-03 | Note preferences | Detailed/Expanded depth and outline/prose formats; keep detailed content when showing an optional overview. AI explanations are off by default. |
| SRC-01 | Source inspection | Passage-level evidence labels, exact transcript revision and interval, explicit replay while audio is retained, and no substituted source. |
| EDIT-01 | Safe edits/regeneration | Persist drafts and protected human revisions, flag dependent content after source edits, compare suggestions and reject stale replacements. |
| OUT-01 | Portable export | Readable Markdown from a chosen saved revision with source excerpts/intervals/version IDs, issue and completeness labels, code and equations; no private media URLs or credentials. |
| PRIV-01 | Privacy/deletion | Authorized content access, local processing visibility, scoped audio/lecture removal, fenced background work and accurate deletion progress. |

These ten requirements retain their Phase 1 IDs. The [32 UX acceptance scenarios](docs/product/phase-2-acceptance-scenarios.md) provide triggers and expected outcomes; they are the full application qualification baseline, with component checks recorded in the implementation reports. The roadmap assigns each a completion owner and requires a full rerun before release.

Detailed notes are organized compression, not a short summary or a transcript pasted under headings. Preserve a worked problem's setup, intermediate steps and result. Do not add empty boilerplate for material the lecturer never addressed. When the lecturer explicitly retracts a claim, present the corrected rule first and identify the superseded claim where needed. Unresolved contradictions remain visible. An inaudible term or unseen board proof is missing evidence, not permission to reconstruct it.

A supplied glossary may guide recognition but is never proof of what was spoken. Student additions, lecture paraphrases, exact quotes and optional AI explanations have separate passage labels. A correct source URL is not proof that the linked words support the claim.

## 4. Student journey and presentation

1. Course library (S1): create or reopen a lecture; unfinished sessions offer recovery.
2. Preparation (S2): title, microphone/input check, depth/format, actual processing location and admission status. Recording appears only after capture starts successfully.
3. Live workspace (S3): detailed notes are the main surface. Show recording, contiguous saved coverage, transcript progress and note progress separately. New output must not move a reader's focus, scroll or selection.
4. Source panel (S4): inspect the selected claim, pinned excerpt/revision, context and retained audio. Playback is an explicit action; returning preserves the reading position.
5. Completion (S5): stop the microphone immediately, flush/seal capture, show pending/gapped evidence and finalization stages. Explicitly finalize available evidence only after explaining incompleteness.
6. Notes workspace (S6): review detail/overview, inspect issues, correct sources/notes, compare proposals, choose a saved revision and export.
7. Data controls (S7): explain retained audio and deletion consequences, require the workflow's explicit destructive choice, and show progress/failure by storage scope.

Use visible keyboard focus, accessible control names, non-color status cues, readable code/equations, zoom/narrow layouts and focus restoration from panels. Announce interruptions without announcing every transcript update. Accessibility is an application acceptance requirement; the architecture page is not a usability-tested app prototype.

## 5. Selected architecture

| Component | Initial responsibility | Boundary |
| --- | --- | --- |
| Next.js + TypeScript | Shared student UI, AudioWorklet/worker capture, IndexedDB journal, drafts, accessible rendering | Reuse within the planned Windows desktop host; qualify its actual capture/storage behavior. Local journal is not an off-device backup. |
| Windows desktop host (M08) | Installer, app window, private service lifecycle, user data/model paths and update handling | Host technology and bundled-versus-prerequisite services remain an explicit packaging decision. Preserve one backend implementation and its authorization boundary. |
| FastAPI / Python | One modular backend for REST/WebSocket; shared domain code in separately launched workers | Inference/object transfers never hold request-scoped database locks. |
| PostgreSQL | Authoritative ownership, epochs, source/note versions, jobs, outbox/inbox and UI replay | Transactions govern publication; latest timestamps and broker messages do not. |
| SeaweedFS | Immutable audio objects through a private server-side S3 adapter | Verify length/checksum; persistent data and metadata volumes; no public bucket URLs. |
| Kafka | Reference-only work notification, replay and failure metadata | At-least-once; PostgreSQL due-job reconciliation recovers missed notifications. No lecture content in topics. |
| faster-whisper | Local speech adapter | `small.en` CPU/int8 is exercised for saved synthetic speech in M03; live settings and `medium.en` final processing remain unqualified. Real lecture evidence is still required. |
| Ollama | Local structured note proposals | `qwen3:4b` measured offline candidate; `qwen3:8b` untested challenger. No live default qualified. |
| Compose + basic diagnostics | Local services, persistent volumes, health, trace IDs, stage timing, pending-byte/backlog/job views | Full telemetry suite, Kubernetes and autoscaling are later experiments. |

There is no initial Valkey, pgvector, document/vision worker, separate realtime microservice, Protobuf or schema-registry dependency. Versioned JSON event contracts suffice for the initial consumers. Preserve extension points without shipping unused services.

## 6. Capture-to-note contracts

### Capture and acknowledgement

Capture mono PCM16 WAV in independently decodable chunks initially around two seconds, using the actual sample rate. AudioWorklet feeds a packaging/persistence worker. Commit blob and manifest entry in one IndexedDB transaction before upload. Initial configurable limits are 1 GiB journal, 8 MiB in-flight worker buffer and 8 MiB upload; admission budgets use actual format/duration with 25% overhead. Exhaustion or failed persistence stops capture visibly; never evict unacknowledged evidence silently.

Chunk identity is run/sequence plus immutable sample metadata/checksum. Reserve the object, write/readback verify it, then recheck ownership/epochs and atomically commit verified metadata, logical work, outbox and update. Only then acknowledge. The client records the matching receipt before removing its copy. Broker publication is not required to acknowledge a durably scheduled chunk. A repeated identity with different content conflicts.

Saved-through coverage cannot jump across a hole. Stop seals last sequence/sample count and known gaps after stopping the microphone. Crashes can leave unsealed runs; recovery discloses unknown extent. Web Locks prevent same-origin duplicate capture; server capture epochs fence explicit takeovers across contexts. A heartbeat timeout alone does not authorize another recorder or remotely stop an offline microphone.

### Jobs and speech

Use short transactions and database leases with fresh attempt tokens. Outbox dispatch, broker consumers and the due-job reconciler converge on one logical job claim. No model inference inside the Kafka polling transaction. Check lifecycle/audio epochs, attempt token and source/settings bases again before output publication. Duplicate delivery may repeat computation but cannot append authoritative duplicate results.

Prioritize capture/storage, speech, live notes, then background/final work. One active call per model role and a shared resource budget are initial settings. Coalesce obsolete note requests; do not skip audio jobs. Transient retries start at one second, jitter up to a 60-second cap and at most five attempts; permanent format/schema failures need correction. Missing acknowledged objects are integrity incidents. AI output repair is distinct: the trial uses zero repair attempts; production may attempt one bounded smaller-window repair without relaxing validation.

Speech windows use contiguous source audio, overlap and original sample coordinates. Proposed policy: begin with six seconds, refresh with two seconds of new evidence, extend unsettled context up to 30 seconds; stable prefixes require two agreeing decodes. These are candidates requiring measurement, not guarantees. Silence, uncertain speech and provider failure are separate outcomes. Preserve negation/identifiers and genuine repetitions. Final speech may split/merge segments but never retarget old citations or overwrite human corrections.

### Detailed notes and evidence

Group coherent topics, retain reasoning/examples/conditions, and budget actual tokens before inference. The trial uses 8,192 context and a 4,096-token output ceiling. Split oversized topics with explicit carried context; final assembly must not globally compress away lecture detail. A roughly 12-second live-note scheduling trigger is unvalidated and does not promise 12-second delivery.

Apply the [canonical note schema](contracts/ai/note-output.schema.json), [speech schema](contracts/ai/speech-result.schema.json) and semantic reference rules. The Ollama grammar adapter is narrower than canonical validation; all canonical limits still apply after generation. Exact source substrings/occurrences resolve to Unicode code-point offsets on immutable versions. Every source receives a consistent used/unclear/omitted ledger entry, without mistaking accounting for semantic coverage.

Trusted prompts are versioned configuration; source text is untrusted evidence and workers have no tool authority. [V1](prompts/note-generation-v1.txt) is the reproducible baseline; [v2](prompts/note-generation-v2.txt) is a targeted development improvement, not the qualified default. Rubrics and answers stay out of model input. Validate completion, JSON, shape, sources/settings, evidence policy, and current publication bases. Unsupported or truncated output retains the last valid notes and a visible failure. Rendering uses sanitized structured text; model code/HTML/math is never executed.

### Revisions, synchronization and finalization

Immutable transcript snapshots and ordered note-document/block versions pin exact evidence. Human edits are protected; changes to sources mark affected notes and overviews stale while old citations remain readable. Proposals bind every base version; stale comparisons require refresh. Undo appends a revision. Preference/overview changes preserve the detailed version.

REST edits use expected versions and idempotency receipts; conflicting or absent preconditions return clear conflict/precondition errors. UI updates are committed with a per-lecture sequence. WebSocket reconnect replays from a cursor, ignores duplicates and requests a consistent snapshot on a gap/expiry. Retain local drafts during reset. Socket health is not capture/save status.

Automatic finalization requires stopped capture, sealed manifests, verified declared audio and terminal speech outcomes. Pending or failed evidence does not disappear on timeout. Final speech precedes a pinned final transcript and topic-wise final notes. No usable transcript produces an explicit no-notes/error state. Accepted gaps remain labeled incomplete; late audio offers a new revision. Failed final work preserves live/prior final notes and edits.

## 7. Access, retention and recovery

One local owner uses a one-use bootstrap secret exchanged for a server session. Check ownership/liveness on every course, lecture, source/version, media, export and WebSocket request. Use same-origin/CSRF controls, HttpOnly SameSite cookies and Secure cookies on HTTPS. Loopback HTTP is a development exception; broader deployment needs HTTPS and a separate deployment design. Keep infrastructure/model ports private or restricted locally.

Retain audio until explicit removal. Audio removal advances its epoch and cancels audio-dependent work while retaining notes/transcript. Lecture deletion tombstones the lecture and fences all writes before erasing objects/versions. Reconcile reservations and in-flight uploads, verify active-store absence, purge connected browser journals and report unconfirmed offline copies. Late work and stale URLs cannot resurrect content. Exports and user-managed backups are outside deletion control.

There is no automatic backup. A manual backup must quiesce writes and preserve both database and referenced objects with a versioned manifest. Replay a separately retained deletion journal before serving restored data; if unavailable, restore into isolation for review. Process/container restart resilience does not prove disk/host-loss survival or physical secure erasure.

## 8. Release gates and measurement

| Area | Required evaluation |
| --- | --- |
| Detail/faithfulness | Proposed ≥90% human-annotated key-item coverage, all recoverable critical items, ≥95% supported reviewed lecture claims, and zero unflagged critical errors/fabricated attribution. Calibrate on human-reviewed evidence; do not call synthetic fixtures calibrated. |
| STT | Real audio WER, domain/identifier errors, meaning-changing errors and timestamp alignment separately. Numeric STT criteria remain open until baseline review. |
| Organization | Human topic-finding tasks and correction/reorganization effort; copied transcript and excessive warnings can fail usefulness despite valid citations. |
| Live/final performance | Define capture-to-transcript, stable-source-to-note and stop-to-final endpoints; record waiting, transfer, queue, inference and rendering, sample counts, cold/warm runs, backlog and peak memory under contention. Set acceptance thresholds before held-out qualification. |
| Recovery/privacy | Execute real browser/storage/database/worker faults and concurrent edits/deletion. No silently missing acknowledged evidence, false completeness, overwritten human edits or revived deleted content. |
| Complete lecture | Run all UX cases plus an independently annotated 45–60 minute CS recording on exact declared versions, including interruption, export and accessible review. |

The old blanket three-second SLOs are superseded by explicit uncalibrated performance gates. Do not convert Phase 4's slow trial into an acceptable live target. Record-now/process-later can enable a useful early milestone while live capability remains a first-release requirement. Human review, recordings and representative visual dependence are unresolved inputs, with assigned roles and due milestones in the roadmap.

## 9. Delivery sequence and deferred work

Implement M01 private foundation → M02 reliable capture → M03 transcription/source inspection → M04 saved detailed notes/export → M05 live updates → M06 protected editing/preferences → M07 finalization/deletion → M08 full qualification. Final transcription/notes and reliability move ahead of course RAG, phone capture and learning tools.

The roadmap defines small work packages, dependencies, migration/interface ownership and testable exit evidence. It specifies migration order; actual SQL, generated OpenAPI, containers and application code belong to the owning Phase 6 increment. Do not create empty service forests or claim unimplemented commands work.

After core gates: Catch Me Up, Mark Important, optional glossary; course materials/vision only when course evidence justifies the scope; then practice/mastery/personalization. Platform demonstrations require a named workload/failure question and measured value. See the [roadmap](docs/implementation/phase-5-roadmap.md) for deferred stack choices.

## 10. Reproducible checks available today

With the pinned test dependency installed, `npm test` runs architecture/AI contract tests and `npm run verify:docs` checks planning links, requirement/scenario ownership and roadmap/artifact consistency. `npm run eval:notes -- qwen3:4b` runs synthetic v1 evaluation against an already installed local model; it does not download weights or validate real audio. Results/failures are not educational approval.

Application preview, migration and backend test commands now exist; see the [M01 run guide](docs/implementation/phase-6-m01.md). No complete lecture-to-notes end-to-end command exists. [Phase 5 verification](docs/implementation/phase-5-verification.md) retains the historical consolidation checks.
