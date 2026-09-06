# Phase 3: Verification and implementation gates

## Scope of evidence

Phase 3 defines architecture, data relationships, and API/event behavior. The [reference model](../../tests/architecture/reference-model.mjs) and [tests](../../tests/architecture/reference-model.test.mjs) are dependency-free executable design checks. They do not implement the application, nor do they prove PostgreSQL transactions, browser recovery, object durability, authorization enforcement, or model quality.

The model deliberately treats object verification/commits as boolean inputs, stores chunk/event identity in memory, and compares finite version values. Its finalization example covers one run with a bounded manifest; production must also reconcile multiple runs, sample gaps, failed transcription ranges, and immutable snapshots as specified in the architecture. Do not use the model as a production persistence adapter.

## Student scenario traceability

Contract IDs refer to sections in the [architecture baseline](phase-3-architecture.md). Every [Phase 2 scenario](../product/phase-2-acceptance-scenarios.md) appears exactly once here; a mapping states design responsibility, not a passed application test.

| Scenarios | Contracts | Responsibility and eventual evidence |
| --- | --- | --- |
| UX-01 | ARC-01, ARC-05, ARC-08 | Owner-scoped library and immutable saved revisions; reopen with real persistence. |
| UX-02, UX-03, UX-04 | ARC-01, ARC-02, ARC-08 | Capture admission, one owner, actual processing mode, and denied-input/capture-only browser tests. |
| UX-05 | ARC-04, ARC-05, ARC-10 | Ordered STT context and detailed note generations; human-reviewed lecture fixtures. |
| UX-06 | ARC-06 | Stable UI block identity and deliberate live-following; browser scroll/focus checks. |
| UX-07, UX-08 | ARC-05, ARC-07 | Settings snapshots, preserved detailed notes, separate overview; revision and UI tests. |
| UX-09, UX-10 | ARC-05, ARC-08 | Versioned evidence and authorized retained audio; source inspection/removal tests. |
| UX-11, UX-12 | ARC-05, ARC-10 | Passage-level attribution and explicit uncertainty; semantic evaluation and visual rendering. |
| UX-13, UX-14, UX-15, UX-16 | ARC-01, ARC-02, ARC-03 | Journal recovery, interruption gaps, upload reconciliation, and storage-pressure failure drills. |
| UX-17 | ARC-04, ARC-06 | Durable job retries and cursor replay; model/socket outage integration checks. |
| UX-18, UX-19 | ARC-02, ARC-03 | Contiguous coverage, seals, incomplete decisions, and new snapshots for late audio. |
| UX-20 | ARC-03, ARC-04, ARC-05 | Failed finalization retains prior notes; retry/edit collision checks. |
| UX-21, UX-22, UX-23, UX-24 | ARC-05, ARC-06 | Source invalidation, human protection, expected versions, and local draft recovery. |
| UX-25, UX-26 | ARC-05, ARC-07 | Authorized revision-pinned Markdown with excerpts and issue labels; offline export inspection. |
| UX-27, UX-28, UX-29 | ARC-08, ARC-09 | Deletion fencing, object/browser inventory, access controls, and restore/replay rejection. |
| UX-30 | ARC-01, ARC-08 | Web Lock plus server fencing and explicit takeover; multi-tab and stale-owner tests. |
| UX-31 | ARC-06, ARC-10 | Accessible frontend presentation and bounded announcements; keyboard/assistive-technology testing. |
| UX-32 | ARC-02, ARC-03, ARC-04, ARC-09, ARC-10 | Full lecture integrity, model contention, stage timing, and restart evidence. |

## Reproducible checks

```powershell
pwsh -NoProfile -File scripts/Verify-PlanningDocs.ps1
node --test tests/architecture/reference-model.test.mjs
git diff --check
git diff --cached --check
```

The documentation checker validates file links, core requirement/screen coverage, and the mapping above. It does not validate external URLs, Mermaid rendering, or semantic truth of requirements. The original HTML artifact remains a historical reference rather than an implementation diagram under test.

## Required integration work before release

- Acknowledgement after readback and committed chunk/job/outbox state; crash each step, including object-write success with DB failure and a lost success response.
- Actual browser microphone capture, IndexedDB commit/recovery, denied persistence, quota pressure, device sleep, and duplicate-tab ownership.
- Concurrent duplicate/conflicting uploads, seals with pending data, late recovery, expired jobs, and student edits while finalization runs.
- Kafka unavailable/lost/retention-expired with ledger reconciliation; duplicate and incompatible events; no duplicate authoritative output.
- Concurrent worker publication versus source edits, audio removal, lecture deletion, and reclaimed job attempts using real database locks.
- Cross-owner/version/object authorization, WebSocket revocation, unsafe rendered content, scoped deletion, stale browser journals, and isolated restore with deletion journal.
- Complete 45–60 minute lecture on declared hardware with model quality, RAM/VRAM, latency, and resource contention measurements.

Hardware inspection was denied in this session; minimum capacity and the selected model combination remain unverified. No actual browser, Docker service, PostgreSQL, Kafka, SeaweedFS, or AI inference test ran in Phase 3.

## Execution results

- Reference model: **24 tests passed**, zero failed/skipped, using Node.js v22.13.1. Cases cover acknowledgement preconditions, all six arrival permutations of three chunks, conflicting duplicates, gaps/seals, partial and empty finalization, stale source/edit/attempt fencing, deletion, consumer-specific deduplication, cursor replay, and job lease recovery.
- Documentation: **40 local file links** resolve across 11 planning Markdown files. All 32 student scenarios cover the 10 core requirements and 7 screens, and each maps exactly once to one or more of the 10 architecture contracts.
- Documentation checker negative controls: missing mappings, unknown contract IDs, duplicate mappings, unknown scenario IDs, and malformed mapping rows were each rejected in an isolated temporary copy. The restored copy passed again.
- PowerShell checker syntax parsed successfully. Working-tree and staged whitespace checks passed.
- Technical constraints were checked against the primary documentation linked alongside the relevant architecture decisions. No performance claim is inferred from those sources.

All Phase 2 UX scenarios remain **not executed against an application**. These results validate parts of the written/executable design, not deployed correctness or production readiness.
