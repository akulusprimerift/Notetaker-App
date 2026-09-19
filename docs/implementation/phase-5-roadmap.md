# Phase 5: Implementation roadmap

Update (2026-09-18): **M08 standalone Windows distribution** remains active. [Native service/runtime packaging](windows-standalone.md) now bundles the Electron web server, Python workers, PostgreSQL, SeaweedFS and CPU Ollama. The separate native library uses database reconciliation; Docker retains Kafka. Release qualification and G01–G06 remain open; Phase 7.4 contention work remains deferred. Earlier entries below are historical.

Latest transition (2026-09-17): move to **M08 standalone Windows distribution**, the recorded follow-on to selected Phase 7 work. [Web component packaging](windows-standalone.md) is the first increment. Phase 7.4 PostgreSQL contention testing is deferred without a completion claim. Retain PostgreSQL authority, the existing Docker library, explicit local models and G01–G06. macOS follows Windows.

Latest selection (2026-09-17): **7.4 — Measured infrastructure** is active. [Processing diagnostics and the isolated SQLite history-growth experiment](phase-7-4.md) establish the first measurement increment. Next: isolated PostgreSQL contention and capture-save overhead comparisons before deciding on indexes, caches or service changes. Earlier quality and G01–G06 release gaps remain open; standalone Windows distribution follows selected 7.4 work. Earlier sequencing entries below are historical.

Phase 7.3 follow-up (2026-09-17): selected-model question/flashcard generation, versioned corrections/quality reviews and learning self-assessments are implemented. Migration 0017 adds pinned requests/results and immutable question edits. Local synthetic evaluation exposed and prompted fixes for unsupported grammar and invented numerical examples; worked-step completeness and human quality/outcome qualification remain open. See [evaluation](../ai/phase-7-3-learning-evaluation.md). Standalone Windows distribution follows, without treating these tests as closure of G01–G06.

Sequencing update (2026-09-16): the user selects **7.3 — Learning tools**, then standalone Windows distribution. The [first learning increment](phase-7-3.md) implements cited recall cards, practice scratch answers and append-only self-assessments with topic/review filters. New migration 0016 is additive. Generated question quality, objective mastery and learning outcomes remain unqualified; G01–G06 remain open. Phase 7.3 is the only active implementation phase; 7.2/7.4 are not prerequisites for the requested standalone Windows follow-on.

Date: 2026-09-06. Status: implementation started; milestone exits require the evidence below.

Implementation checkpoint: [Phase 6 / M01](phase-6-m01.md) is complete for the private course/lecture foundation. [M02 recording and recovery](phase-6-m02.md) is implemented with synthetic browser and real-service evidence; actual microphone/device-failure qualification remains open under the user's synthetic-only testing preference. [M03 saved-audio transcription](phase-6-m03.md) is implemented with synthetic verification; [M04 automatic notes](phase-6-m04.md) is implemented for bounded saved transcripts, with topic processing and qualification still open; [M05 live assistance](phase-6-m05.md) is implemented with synthetic macOS verification and live qualification still open; M06–M08 remain planned; the full note-taking product is not qualified. The exit criteria below remain the baseline.

Current update (2026-09-08): [M06 editing and regeneration](phase-6-m06.md) is implemented, superseding the earlier checkpoint's planned M06 status. It also brings shorter live windows, contextual note batches and streaming output. Detail/layout now use custom prompts. Optional collapsed overviews are deferred. [M07 finalization and data control](phase-6-m07.md) is now the active implemented increment, including late recovery, deletion reconciliation and browser purge. M08 and the remaining release qualification gates stay open.

This is the build backlog for product-development Phase 6. Milestone IDs M01–M08 are build increments, not a restart of the phase numbering. The [consolidated specification](../../multimodal_academic_learning_system_spec.md) controls scope; the [reconciliation record](phase-5-reconciliation.md) explains changes from the originals. Every milestone requires its stated evidence before being called complete.

The [feature and architecture phase plan](../project-phases.md) calls these increments Phase 6.1–6.8 and defines the ongoing build, verify and local-commit workflow. M02's deferred real-device qualification remains open while independent M03 engineering proceeds with synthetic speech; its dependency on working capture/storage remains unchanged, and synthetic evidence cannot satisfy real-lecture release gates.

## Ordered backlog

Priority P0 means required for the first release. P1 means a desired extension after all core gates pass. Dependencies describe merge/integration order; fixture annotation and feasibility research can start during M01. No dates or effort estimates are implied.

| Milestone | Priority | Depends on | Student-visible result |
| --- | --- | --- | --- |
| M01 | P0 | None | Open a private course library and create/reopen a lecture. |
| M02 | P0 | M01 | Record and safely recover saved audio while processing is unavailable. |
| M03 | P0 | M02 | Read timestamped speech, inspect retained audio, and correct transcript errors. |
| M04 | P0 | M03 | Generate detailed notes from a saved transcript and export a source-linked study document. |
| M05 | P0 | M04 | Receive incremental transcript and notes while recording, with honest delay and recovery states. |
| M06 | P0 | M05 | Change preferences, edit notes, and compare regeneration proposals without losing work. |
| M07 | P0 | M06 | Finalize a lecture, preserve revisions, and remove audio or the lecture with visible progress. |
| M08 | P0 | M07 | Install and use the Windows desktop app, completing the lecture workflow with reviewed quality and recovery evidence. |

### M01: Private workspace and service foundation

- Build: Next.js/TypeScript shell and one FastAPI codebase for REST, WebSockets, and separately launched workers. Add Docker Compose for PostgreSQL, SeaweedFS, and Kafka; keep models in an explicit local provisioning profile. Pin versions after checking the actual host. Add health checks, opaque trace IDs, migrations, one-use owner bootstrap, sessions, CSRF/origin checks, course/lecture creation and consistent snapshot reads.
- Persistence: owners/sessions, courses, settings versions, lecture lifecycle/capture/audio epochs, command receipts, job/outbox/inbox/update tables. Implement authorization helpers and tombstone checks before content routes; only health information is public. Do not expose placeholder recording controls as working features.
- Verify: a fresh isolated database migrates, restart preserves a course, duplicate create keys return one result, mismatched reuse conflicts, unauthorized REST/WebSocket/source IDs reveal no content. Real object put/read/checksum and broker publish/consume succeed with persistent volumes. No lecture content in telemetry.
- Exit evidence: pinned environment manifest, reproducible start/test instructions, migration logs, integration results, and a course create/reopen walkthrough. These passed for M01; this does not establish completion of the note-taking product.

### M02: Capture and durable acknowledgement

- Build: microphone admission, Web Lock plus server capture ownership, AudioWorklet/worker PCM WAV packaging, atomic IndexedDB chunk/manifest journal, reservation/upload/readback verification, matching acknowledgements, stop/seal, contiguous coverage, and recovery view. Server-side upload commit includes metadata, a logical speech job, outbox and update; the worker may remain pending.
- Verify: permission denial/retry, double start, two tabs, network interruption, lost acknowledgement, out-of-order/missing chunks, checksum conflict, storage exhaustion, refresh/crash, and microphone/sleep gaps. Restart actual PostgreSQL/SeaweedFS and read acknowledged objects. Never equate that drill to host-loss redundancy or power-loss proof.
- Exit evidence: expected/observed manifests and UI states for each failure, readable recovered WAVs, disk-volume configuration, and recording-with-models-off walkthrough. Capture stops visibly if preservation cannot continue; no unacknowledged audio is evicted.

### M03: Versioned transcription and source inspection

- Build: faster-whisper adapter, job claims with leases and fenced attempts, outbox dispatcher, Kafka dispatch and due-job reconciler sharing the same claim path. Persist transcript versions/snapshots and uncertainty, expose authenticated source/audio reads and transcript correction. Use contiguous windows and original sample coordinates; separate transport chunking from inference.
- Verify: actual recorded speech, silence/noise, rapid CS terminology and negation, overlapping windows without duplicate/lost phrases, worker kill/reclaim, broker outage, source-version lookup, and protected human corrections. An unavailable model leaves audio pending, never a fabricated silent success.
- Exit evidence: source/audio alignment walkthrough and STT baseline with model digest, hardware, WER, term errors, critical meaning errors, timestamps and inference cost. Human annotation and transcription-threshold calibration are assigned to G01/G02; a stub cannot satisfy this exit.

### M04: Detailed notes from saved evidence

- Build: user-selected LLM automatic note writing (manual edits are optional review), topic input budgeting, note provider adapter, canonical server validation and source resolution, persisted note revisions/generation identity, evidence labels, missing-information review list, readable code/equations, source panel, and Markdown export from a saved revision. Start with Detailed/Topic outline and optional AI explanations disabled. Use backend validation equivalent to the Phase 4 contract suite; a provider grammar is never authoritative validation.
- Verify: all development fixtures, correction-first presentation, intermediate algorithm/example steps, zero versus positive conditions, false-positive warnings, exact quotes versus paraphrases, malformed/truncated output, cross-lecture sources, malicious text/rendering, and portable source appendix. Invalid output leaves the last valid notes intact.
- Exit evidence: recorded local-model reports, full v2 comparison or a justified replacement, and human review of generated study notes against annotated excerpts. Record all failures. The first useful vertical slice is saved lecture audio → transcript → detailed source-linked notes → export; it does not yet establish live readiness.

### M05: Live updates and recovery

- Build: stable/provisional speech revisions, topic updates, coalesced note jobs, admission/resource budget, transcript/note progress, durable WebSocket replay and snapshot reset. Preserve reading position, selection and focus; delay is visible independently from capture/save status. Implement the six/two/30-second speech policy and approximately 12-second note trigger only as tunable candidates.
- Verify: simultaneous capture/STT/notes, long topics exceeding context, genuine repetitions versus overlap, Kafka/model outage, dropped/duplicated/out-of-order UI messages, expired cursor, and owner takeover/recovery. No silent cloud fallback or audio-job skipping.
- Exit evidence: timing endpoints and cold/warm sample counts, backlog age, pending bytes, real-time factor and peak RAM/VRAM on the declared host. G03 must establish a usable live configuration. Record-now/process-later is a supported fallback, not grounds to mark the live requirement complete.

### M06: Student edits and preferences

- Build: Detailed/Expanded and outline/prose settings snapshots, optional collapsed overview derived from detailed notes, persistent local edit drafts, protected student versions, comparison/keep/replace/merge, optimistic conflicts and undo as new revisions. Source corrections invalidate affected notes and overviews while retaining original citations.
- Verify: edit while generation runs; open a comparison then make a newer edit; fail/retry saves; regenerate under changed settings; undo replacement; export while unsaved; missing sources; preserved code/equation structure and evidence labels outside the app. No data-destructive format switch.
- Exit evidence: concurrency tests against the real database, keyboard walkthrough of comparison and export, and revision histories proving student edits survive final/automatic work. No last-writer-wins shortcut.

### M07: Finalization and data lifecycle

- Build: final speech then pinned final transcript then final topic notes; ready/pending/incomplete status; explicit finalize-available decision; later recovery offers a new revision. Add audio-removal and lecture-deletion inventory, epochs, reservation reconciliation, local-journal purge, and owner-scoped deletion progress. Deletion write fences already exist in M01–M04; this milestone completes the erasure workflow and UI.
- Verify: stop before all chunks arrive, unsealed crashes, terminal speech failure, no usable transcript, failed final notes, late recovery, concurrent edit/finalize/delete, upload finishing after deletion, obsolete worker attempt, disconnected browser copies, audio removal followed by transcript-only regeneration, and stale URLs/events after deletion.
- Exit evidence: real storage/DB/browser failure drills, readable prior revisions after finalization failure, no post-tombstone content recreation, and accurate deletion-scope reporting. Document that exports/backups are outside app deletion control; no automatic backup is claimed.

### M08: Windows desktop delivery and full lecture qualification

- Build: an installable Windows desktop host with its own window and Start menu entry, reusing the existing UI/backend. Record the host technology and service-distribution decision before packaging; implement local service lifecycle, private endpoints, user-data/model locations and upgrade preservation. Add integration/endurance harness, reproducible local runbook, supported-environment report, and remaining accessibility/recovery fixes. Finish the manual backup/restore procedure with a database/object manifest and separate deletion journal; an unavailable journal means isolated restore review.
- Verify: clean Windows installation, app launch, close/reopen, missing-service recovery, data-preserving upgrade and explicit uninstall data-retention behavior. Test actual desktop-host capture, journal persistence, permissions and accessibility. Execute all 32 UX cases with the desktop app and real services, including a complete 45–60 minute independently annotated CS lecture and interruption; run topic-finding/edit-effort review, concurrent worker/edit/deletion drills, and backup restore without resurrecting deleted content. Include keyboard, assistive technology, zoom, narrow layout and code readability checks. Never call the HTML architecture artifact a tested application.
- Exit evidence: expected/observed outcomes per UX case, all G01–G06 gates resolved with evidence, calibrated quality/performance criteria, supported exact Windows app/runtime versions and install artifact, residual limitations, and zero unflagged critical errors or fabricated lecturer attribution in release fixtures. Failed gates block release, not investigation or fixes.

## Qualification gates and ownership

Roles identify who supplies evidence, not people already assigned. The implementation agent can prepare fixtures/tools and run measurements; an actual human subject reviewer must supply human review. Unanswered qualification inputs do not prevent M01 setup.

| Gate | Required evidence / decision | Accountable role | Due milestone | Current state |
| --- | --- | --- | --- | --- |
| G01 | Human-reviewed development excerpts plus independently annotated held-out recordings, including a 45–60 minute lecture; separate development and held-out material. | Subject reviewer with evaluation implementer | M03, M04, M08 | Open: assistant-authored synthetic text and generated speech exist; independently annotated real lectures and human review remain. |
| G02 | Real STT baseline and calibrated term/timestamp/meaning-error criteria; human assessment of detailed-note coverage, support, retractions, organization and editing effort. | Subject reviewer with AI implementer | M03, M04, M08 | Open: M03 local STT passes short synthetic speech checks; real-lecture term/timestamp/meaning calibration and human note review remain. 90% coverage and 95% support remain proposed gates. |
| G03 | Chosen hardware/model settings meet predeclared live/final delay criteria under simultaneous STT/notes; sample counts, backlog, cold/warm timings and peak memory recorded. | AI/runtime implementer with student workflow review | M05, M08 | Open: note-only trials took 66–214 seconds; no live default qualified. |
| G04 | Real browser/storage/DB failure tests validate acknowledgement, gap reporting, edit/version fences, restart/recovery and scoped deletion. | Application implementer | M02, M06, M07, M08 | Open: M02 synthetic browser recovery, real IndexedDB, PostgreSQL capture tests and storage-restart checks pass; actual device failures and later edit/deletion qualification remain. |
| G05 | Review a representative course for visual-only material; retain disclosed limitations or explicitly move materials/visual capture forward if notes cannot be useful without it. | Subject reviewer with product owner | M04, M08 | Open: synthetic missing-board warnings do not establish course suitability. |
| G06 | Exact supported environment, accessibility walkthrough, Windows installation/upgrade and desktop-host checks, local privacy checks, full-lecture UX results and backup/restore limits documented. | Application implementer with student reviewer | M01, M08 | Open: M01 Windows/container foundation and basic browser walkthrough pass; recording, assistive technology, full lectures and backup/restore remain unqualified. |

Do not reduce gates simply to obtain a passing report. Any threshold or scope change needs a recorded reason, reference data, and a new evaluation; changing runtime candidates does not authorize sending lectures externally.

## Acceptance ownership

Each scenario has one primary completion milestone below. It can receive earlier component checks and is rerun in M08. M01 now has application evidence for course/lecture persistence and the existing authorization boundary; later source routes must extend those checks. Full-scenario and release qualification remain open.

| Scenarios | Primary milestone | Evidence focus |
| --- | --- | --- |
| UX-01, UX-29 | M01 | Persistence and owner authorization, including later-added source routes. |
| UX-02, UX-03, UX-04, UX-13, UX-14, UX-15, UX-16, UX-18, UX-30 | M02 | Admission, durable capture, gaps, ownership and stop/seal. |
| UX-09 | M03 | Version-pinned transcript and explicit retained-audio playback. |
| UX-11, UX-12, UX-25 | M04 | Uncertainty, passage provenance and portable detailed export. |
| UX-06, UX-17 | M05 | Undisrupted reading, progress, delayed processing and replay. |
| UX-07, UX-08, UX-21, UX-22, UX-23, UX-24, UX-26 | M06 | Preferences, overview dependencies, edit conflicts and saved export. |
| UX-10, UX-19, UX-20, UX-27, UX-28 | M07 | Finalization, late evidence, deletion and retained-source behavior. |
| UX-05, UX-31, UX-32 | M08 | End-to-end semantic quality, accessibility and endurance. |

M01 authorization is a rule for every subsequent route; M02 capture safety and M04 evidence validation remain regression requirements in all later increments.

## Migration and interface sequence

These are ordered migration work packages, not SQL that has been applied. Use one backend migration history; generate concrete DDL and API schemas in the owning milestone against the pinned database version. The [logical data model](../architecture/phase-3-data-model.md) and [API/events](../architecture/phase-3-api-events.md) specify fields and transaction rules.

| Order | Owning milestone | Schema / interface work |
| --- | --- | --- |
| DB01 | M01 | Owners/sessions, courses/lectures/settings, epochs, jobs/outbox/inbox/receipts/updates; bootstrap, course, lecture, snapshot and job endpoints. |
| DB02 | M02 | Capture runs/gaps, reservations/chunks/manifests; owner acquire/takeover, upload, seal and recovery endpoints. |
| DB03 | M03 | Transcript segment versions/snapshots, generation runs and invalidations; speech output adapter, source/audio reads and versioned corrections. |
| DB04 | M04 | Topics, note/block/document versions, provenance and ordered membership; note generation/status and saved Markdown export. |
| DB05 | M05 | Finalize replay/index/lease tuning from actual live query patterns; versioned JSON events and WebSocket snapshot/replay schemas. No new broker dependency for UI correctness. |
| DB06 | M06 | Proposals, overview dependencies and resolution history; expected-version edits/preferences/regeneration/resolve endpoints. |
| DB07 | M07 | Deletion inventory and finalization coordination; audio removal, lecture deletion/progress, and immutable final snapshots. |

Enforce same-lecture foreign keys, unique run/sequence, logical jobs, consumer/event inbox keys and expected versions in each owning migration. Test fresh creation and incremental upgrade with existing content. Back up the DB and referenced objects before data-changing upgrades; prefer forward fixes. A down migration must never discard student evidence to simulate rollback. Do not rewrite already-used migrations.

## After the core release

P1: Catch Me Up, Mark Important and optional course glossary, each reusing validated evidence and measured usefulness. P1 after G05 scope decision: document/slide ingestion and visual capture with distinct source types. Later learning work: practice, mastery and personalization after note quality is proven.

Platform experiments follow an explicit workload/failure question: pgvector for demonstrated retrieval, Valkey for measured hot paths, Protobuf/Apicurio for schema evolution, full telemetry for diagnosed needs, then Kubernetes/Strimzi, KEDA/load tests, and optional GitOps/CDC. Outbox, retry, ownership and deletion safety are already core; they are never postponed to a portfolio milestone.

## Sequencing clarification — 2026-09-15

Phase 7.1 is now active following committed theme/account repairs and catalog/disconnect improvements. [Note usefulness](phase-7-1.md) adds student bookmarks, source-linked catch-up and immutable course terminology hints with synthetic engineering evidence. Human usefulness, authenticated provider use and earlier release gates remain unqualified. Continue selected Phase 7 work, then standalone Windows packaging, then macOS. Claude subscription login remains dependent on provider approval. See the [session transfer](../../SESSION_TRANSFER.md).
