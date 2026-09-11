# Project phases

Current priority (2026-09-11): M08 remains the single active phase. The user selected Electron as the Windows host and requests a cleaner, NotebookLM-inspired workspace. Visual notes and both API-key/subscription connections remain in the shared service scope; account/provider and scientific-quality qualification remain open. See [evidence and limitations](implementation/visual-notes-providers.md). Earlier release gaps remain open.

Current priority (2026-09-10): M08 incremental note sections. Audio/transcription are accepted by the user. Pin small source groups per note request, save cumulative immutable sections during capture, continue through backlogs, display saved-section progress, and retain student edits. Migration 0013 preserves existing library history. See [M08 evidence](implementation/phase-6-m08.md).

Current priority (2026-09-09): M08 recording/live-workflow repair. The Electron renderer uses browser capture with input selection and recovery, streams speech previews beside notes, protects reading position and exposes individual lecture deletion. Note models remain local user selections. See [M08 evidence](implementation/phase-6-m08.md).

Sequencing update (2026-09-11): the user accepts M07 implementation, brings syllabus/curriculum and PowerPoint uploads and visual note rendering forward, and selects Electron as the only Windows host. Course materials, protected edits, source-linked notes and the existing Electron service lifecycle remain in scope. See [M08 evidence](implementation/phase-6-m08.md) and [materials evidence](implementation/course-materials.md). Existing synthetic-only testing and release gates remain unchanged.

Updated: 2026-09-08. This is the working phase plan for future development. Each build phase delivers student-facing features, the architecture needed to support them, and recorded completion evidence.

This roadmap reflects the current priority: the user-selected LLM automatically writes excellent notes from lecture transcripts, for any subject and content-heavy course. CS is a test anchor, not a product restriction. Manual editing is optional review. The user accepts the [M05 live workflow](implementation/phase-6-m05.md). The [M06 increment](implementation/phase-6-m06.md) improves speech latency, contextual batching and streaming, removes redundant preference dropdowns, and implements protected editing/regeneration. The active [M07 increment](implementation/phase-6-m07.md) adds finalization and data control after saved prompt profiles and automatic local access. Actual model performance, semantic topic quality and Windows release qualification remain open.

These are product-development phases. They are distinct from the older, zero-based implementation phases in the archived specification and HTML artifact. Phase 5 replaces that original build order with M01–M08 inside product-development Phase 6.

| Phase | Focus | Deliverable and completion condition |
| --- | --- | --- |
| 1. Product definition and scope | Establish the initial audience, core note-taking promise, first-release boundaries, and quality expectations. | A product brief records requirements, working assumptions, deferred features, and measurable proposed acceptance gates. |
| 2. Student experience | Design preparation, recording, live notes, source inspection, correction, finalization, and export, including interruption recovery. | User flows and screen requirements cover both successful use and degraded operation. |
| 3. Architecture and data design | Resolve capture durability, transcript and note revisions, provider responsibilities, privacy, deployment, and asynchronous processing. | One consistent architecture and data model explain the major decisions and failure handling. |
| 4. AI pipeline and evaluation | Define streaming transcription, note generation, terminology handling, evidence linking, and quality evaluation. | Provider contracts, human-reviewed lecture fixtures, and calibrated quality and performance gates support comparison of candidate approaches. |
| 5. Consolidated specification and implementation roadmap | Reconcile the source documents and turn the agreed design into small implementation milestones. | An updated specification, architecture artifact, and prioritized backlog have testable exit criteria. |
| 6. Build and validate core note-taking | Implement capture, transcription, detailed live/final notes, source inspection, editing, and export. | Complete content-heavy lectures pass the agreed note-quality and recovery checks on declared hardware. |
| 7. Expand and demonstrate | Add features that improve notes, then learning tools and staged infrastructure demonstrations. | Each addition has evidence of usefulness, correctness, or measured operational benefit. |

## Sequencing rules

- The first useful end-to-end delivery is saved lecture audio → timestamped transcript → detailed source-linked notes → export in Phase 6.4. Foundation and recording increments precede it. Practice generation is not a release dependency.
- Bring course materials or visual capture forward only when evaluation shows they are necessary for the selected lecture type; update scope explicitly.
- Infrastructure work should support a current product requirement or a named engineering experiment. The portfolio objective remains part of the longer-term project.
- Phase 1 documentation does not establish application accuracy, hardware feasibility, or production readiness.
- Record unresolved decisions and carry them into their assigned phase rather than silently treating assumptions as confirmed requirements.

## Phase 6: Feature and architecture build plan

Use **6.1–6.8** when discussing build phases. These are readable aliases for the existing **M01–M08**, respectively; they do not renumber historical Phases 1–5 or create a second backlog. The [implementation roadmap](implementation/phase-5-roadmap.md) retains the detailed acceptance cases, migration order and release gates.

| Build phase | Student features | Architecture delivered in this phase | Completion evidence |
| --- | --- | --- | --- |
| 6.1 / M01 — Private workspace | Unlock a local workspace, organize courses, create and reopen lectures, choose initial note preferences. | Next.js/TypeScript UI; one modular FastAPI backend; PostgreSQL records, sessions and migrations; private SeaweedFS audio storage and Kafka services under Docker Compose. Establish ownership, authorization and job/outbox foundations. | Course/lecture persistence, access controls, migrations and real service/restart checks pass. |
| 6.2 / M02 — Reliable lecture recording | Start/stop recording, see confirmed saves, recover buffered audio after interruption, and listen to saved excerpts. | Browser AudioWorklet and worker; atomic IndexedDB recovery journal; verified immutable audio uploads; server recording ownership; sample-based manifests and explicit gaps. | Recording and recovery scenarios preserve acknowledged audio, expose missing intervals, and stop visibly when preservation fails. Synthetic checks are distinguished from actual microphone/device qualification. |
| 6.3 / M03 — Transcription and source inspection | Read timestamped speech, play the corresponding audio, inspect uncertain passages, and correct transcript errors. | Local faster-whisper adapter; independently running speech worker; durable job claims, retries and dispatcher/reconciler; versioned transcript snapshots and corrections. Combine transport chunks into suitable speech windows while preserving source positions. | Speech/timestamp alignment, technical terminology, negation, retry/reclaim and correction protection are tested. Record an actual speech baseline; synthetic speech can exercise the pipeline but cannot qualify real lectures. |
| 6.4 / M04 — Detailed study notes | Choose a local LLM, note depth, layout and writing preferences for any subject; automatically write organized notes from a saved transcript, follow sources, review missing information, and export Markdown. Preserve definitions, reasoning, algorithm steps, worked examples and complexity explanations when present in the lecture. | Local Ollama note adapter; topic/context budgeting; validated structured output; immutable note revisions tied to transcript/settings versions; evidence links and deterministic saved-revision export. | The complete saved-audio-to-notes workflow runs. Invalid output preserves prior valid notes. CS note fixtures and human review assess coverage, source support and usefulness. Unsupported board/code details remain marked as missing. |
| 6.5 / M05 — Live lecture assistance | Receive transcript and note updates during recording; see processing delay separately from save progress; reconnect without losing the reading position. | Provisional/stable transcript revisions; coalesced note jobs; shared model resource budget; durable WebSocket replay and snapshot recovery. Capture remains independent of inference availability. | Simultaneous recording/transcription/notes, reconnects and model/broker outages pass. Measure cold/warm latency, backlog and memory on the actual machine before qualifying a live configuration. |
| 6.6 / M06 — Editing and regeneration | Edit notes, describe detail and format with custom prompts, compare regenerated suggestions, keep/merge/replace changes, and undo. Redundant preset dropdowns are removed at the user's request. | Durable local drafts; protected student revisions; expected-version writes; generation proposals and conflict resolution; settings snapshots and source-change invalidation. M05 improvements add short speech windows, bounded note batches and visible streaming. | Concurrent edits and generation cannot overwrite student work. Save/retry, comparison, undo and export preserve the selected revision and readable code/equations. |
| 6.7 / M07 — Finalization and data control | Finalize available lecture content, see incomplete results, retain revision history, remove audio or delete a lecture with visible progress. | Final speech/transcript/note coordination; immutable final snapshots; deletion inventory, epoch checks and object reconciliation; browser-copy purge and deletion progress. | Late audio, failed finalization, concurrent edits/deletion and stale worker results behave correctly. Deletion cannot recreate content and accurately describes disconnected copies and external exports. |
| 6.8 / M08 — Windows application and release testing | Install and launch a Windows app with its own window; use the entire lecture workflow and documented recovery/backup process. | Desktop host and installer; local service lifecycle and user-data/model paths; safe upgrade handling; endurance harness and coordinated database/object restore. Select the packaging approach before implementation and reuse the existing UI/backend. | Clean Windows install, launch, close/reopen, service failure, upgrade and uninstall data-retention checks, plus all 32 scenarios and six release gates including the annotated full lecture, accessibility and restore tests. |

### Architecture boundaries throughout the build

- **Browser:** presentation, capture, bounded local recovery storage and edit drafts. A successful recording save and completed transcription/note generation are separate states.
- **FastAPI:** one modular codebase owns authorization and domain rules. Speech and note workers run as separate processes using those rules; this does not require separate microservices.
- **PostgreSQL:** authoritative metadata, source/settings versions, note revisions, job state and outbox. **SeaweedFS:** private audio objects. **Kafka:** work notifications containing references; database reconciliation recovers missed notifications.
- **Model adapters:** faster-whisper for speech and Ollama for notes, processed locally. Candidate model sizes remain subject to measured quality and hardware capacity. No automatic external-provider fallback.
- **Windows delivery:** an installable Windows app is a release requirement, added by the user on 2026-09-07. The current browser UI is a development preview. M08 must qualify the desktop host’s actual microphone, audio, storage and focus behavior; browser tests do not automatically qualify the desktop shell. Service bundling versus clearly disclosed prerequisites is decided before packaging.
- **Development deployment:** retain the existing local Docker Compose foundation. Add infrastructure only for a requirement or measured limitation. Do not introduce vector search, caches, orchestration clusters or extra service boundaries merely because a later phase might use them.

Every new feature must extend authorization, source provenance, revision protection and failure reporting where applicable. Those protections are part of its implementation phase, even when the full lifecycle workflow is completed later.

### How we execute each build phase

1. State the phase ID, user-visible result, included features, deferred features and required architecture changes before implementation. Use the existing detailed milestone as the baseline.
2. Build small, reviewable increments. Include concrete database/API/event changes, migration compatibility and UI behavior in the same feature's scope. Preserve existing student data.
3. Run checks appropriate to the change. For a feature, exercise the working user flow and relevant failures; for documentation-only edits, verify links and roadmap consistency. Never present planned checks as executed results.
4. Record what is implemented, what was tested, and what remains unqualified. **Implemented** means the feature exists; **verified** names the environment and checks that passed; **complete** requires the milestone's exit evidence. **Release-ready** requires the cross-phase gates as well.
5. Locally commit every change, including small fixes and documentation updates, with a short description. Do not push unless requested. End each increment with a concise outcome, evidence, limitations, commit and next step.
6. Keep one active implementation phase. A deferred qualification check may remain open while independent later work proceeds if its missing evidence is not required for safe implementation. Record that dependency explicitly; do not claim the earlier phase complete or silently relax a release gate.

Routine implementation choices and reversible fixes can proceed within the requested phase. Changes to the core product scope, external processing or user-controlled resources must follow the user's instructions; the plan does not add a new approval pause for every small change.

### Current position and next work

| Phase | Current state | Next action |
| --- | --- | --- |
| 6.1 / M01 | Complete for the private workspace foundation, with real-service evidence. | Preserve its behavior as later features are added. |
| 6.2 / M02 | Recording and recovery implemented; synthetic browser and real storage checks verified. Full device qualification is open. | Retain the actual microphone, physical failure and endurance checks as explicit remaining evidence. |
| 6.3 / M03 | Saved-audio transcription, source playback and corrections implemented; synthetic engineering checks verified. | Use the M03 verification report; retain representative real-speech and human review requirements as open. |
| 6.4 / M04 | Bounded automatic notes and source-linked exports implemented; accepted as working by the user. | Retain long-lecture topic/context handling and human quality qualification as open evidence. |
| 6.5 / M05 | Live assistance accepted by the user; M06 improves timing, removes presets and adds streaming/batching. | Preserve [historical M05 evidence](implementation/phase-6-m05.md); actual live hardware performance and human quality qualification remain open. |
| 6.6 / M06 | Protected editing and regeneration implemented, with live pipeline improvements. | See [M06 behavior/evidence](implementation/phase-6-m06.md) and [session transfer](../SESSION_TRANSFER.md) for executed checks. Qualify actual model performance and educational quality separately. |
| 6.7 / M07 | Implemented: finalization, immutable snapshots, late recovery, deletion reconciliation and browser purge implemented. Saved prompt profiles and automatic local access precede it. | See [M07 behavior/evidence](implementation/phase-6-m07.md) and the session transfer for executed checks. |
| 6.8 / M08 | Active: user-selected Electron Windows rebuild with a cleaner lecture workspace, native-feature parity in the shared React UI, local model discovery and course/lecture data controls. | Electron installer and installed launch are the delivery path. Complete UI flow, service lifecycle, clean-machine, hardware, endurance and restore gates. |

The user's current testing preference is **synthetic audio only**. No real microphone access is authorized by this plan. Controlled synthetic speech can support M03 engineering; representative real recordings and human review remain necessary to qualify transcription and educational quality. Missing real-device evidence does not prevent building that synthetic pipeline, but it prevents claiming those checks passed.

## Phase 7: Expansion after the core workflow

These are staged options, not additional first-release dependencies. Each selected expansion gets its own feature scope, architecture delta and completion evidence before implementation.

| Expansion stage | Features | Architecture trigger and evidence |
| --- | --- | --- |
| 7.1 — Note usefulness | Mark Important, Catch Me Up and course terminology support. | Reuse saved sources and note revisions; demonstrate that the addition improves studying without weakening evidence attribution. |
| 7.2 — Course materials and visuals | Slides, documents, board/code images and links between spoken and visual explanations. | Add source types, ingestion and multimodal alignment when course evaluation establishes the need. If visual evidence is essential for the first CS workflow, explicitly revise core scope rather than pretending audio captures it. |
| 7.3 — Learning tools | Practice questions, flashcards, mastery tracking and personalization. | Build on qualified notes, with separate question-quality and learning-state evaluation. |
| 7.4 — Scale and infrastructure demonstrations | Retrieval, caching, richer monitoring or multi-service/cloud orchestration where justified. | Introduce pgvector, Valkey, schema tooling or Kubernetes only for a named experiment or measured workload; publish benefit and operational cost. |

## Current checkpoint

The [Phase 1 product brief](product/phase-1-product-brief.md) establishes the initial scope. The [Phase 2 student experience](product/phase-2-student-experience.md) defines the workflows and screen requirements, with [acceptance scenarios](product/phase-2-acceptance-scenarios.md) covering the core scope. [Verification notes](product/phase-2-verification.md) distinguish documentation validation from application tests that have not yet run.

The [Phase 3 architecture](architecture/phase-3-architecture.md), [data model](architecture/phase-3-data-model.md), and [API/event contracts](architecture/phase-3-api-events.md) define the implementation baseline. [Phase 3 verification](architecture/phase-3-verification.md) maps all student acceptance cases to architecture responsibilities and distinguishes reference-model checks from integration tests.

The [Phase 4 pipeline](ai/phase-4-pipeline.md) and [evaluation plan](ai/phase-4-evaluation.md) define the AI contracts and candidate settings. The [Phase 4 results](ai/phase-4-results.md) distinguish executed contract checks and synthetic local-model trials from uncompleted human review, real-audio STT, and full-lecture evaluation.

The [consolidated specification](../multimodal_academic_learning_system_spec.md), [updated architecture artifact](../multimodal_academic_learning_system_architecture_v2.html), and [Phase 5 roadmap](implementation/phase-5-roadmap.md) reconcile the original documents. [Reconciliation](implementation/phase-5-reconciliation.md) records the decisions; [verification](implementation/phase-5-verification.md) records executed checks. M01–M08 map all 32 UX scenarios and carry six unresolved qualification gates into implementation. Phase 4's human-reviewed fixtures and calibrated quality/performance completion conditions remain open.

Phase 6 / M01 has a [verified private workspace foundation](implementation/phase-6-m01.md), including PostgreSQL/object/broker and restart checks. [M02 recording and recovery](implementation/phase-6-m02.md) is implemented with synthetic browser and real-service evidence. [M03 saved-audio transcription](implementation/phase-6-m03.md) is implemented with synthetic verification; actual microphone/device and full-lecture qualification remain open. Windows desktop delivery is required in M08. Synthetic results and passing design checks do not establish release readiness or physical storage durability.

## Later provider connections

The user brought optional user-owned OpenAI/ChatGPT and Claude model connections into M08. The Electron host now provides the protected-storage bridge, official-client sign-in path and explicit per-lecture cloud-processing choice; account login, paid inference and subscription compatibility still require live provider qualification. Phase 7 retains advanced provider expansion, measured cost controls and broader account support. This does not defer automatic local note writing. See [M04 provider requirements](implementation/phase-6-m04.md#later-openai-and-claude-connections).

## Windows host next step

The [desktop direction](architecture/windows-desktop-direction.md) records the user-selected Electron host, hardened renderer boundary, local service lifecycle and current installer approach. Complete Windows installer, upgrade and release qualification remains M08. Basic note-writing preferences were brought into M04 at the user’s request; M06 still owns protected manual editing, compare/merge and undo.

## User-selected Electron Windows profile — 2026-09-11

The user superseded the native Qt direction and selected Electron as the only Windows host. Electron uses the existing hardened loopback Next.js renderer, FastAPI domain contracts, Docker service lifecycle, browser capture journal and local model discovery. No Qt, PySide6, standalone native library or native packaging workflow remains in the repository. Existing Docker/PostgreSQL student data is preserved and reused only through the explicit existing-workspace choice. Clean-machine, physical audio, endurance, accessibility, restore and educational-quality qualification remain open.
