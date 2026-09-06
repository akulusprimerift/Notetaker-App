# Project phases

This roadmap reflects the current priority: reliable transcription and excellent lecture notes, especially for content-heavy courses.

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

- The first application milestone is a usable lecture-to-notes experience. Practice generation is not a release dependency.
- Bring course materials or visual capture forward only when evaluation shows they are necessary for the selected lecture type; update scope explicitly.
- Infrastructure work should support a current product requirement or a named engineering experiment. The portfolio objective remains part of the longer-term project.
- Phase 1 documentation does not establish application accuracy, hardware feasibility, or production readiness.
- Record unresolved decisions and carry them into their assigned phase rather than silently treating assumptions as confirmed requirements.

## Current checkpoint

The [Phase 1 product brief](product/phase-1-product-brief.md) establishes the initial scope. The [Phase 2 student experience](product/phase-2-student-experience.md) defines the workflows and screen requirements, with [acceptance scenarios](product/phase-2-acceptance-scenarios.md) covering the core scope. [Verification notes](product/phase-2-verification.md) distinguish documentation validation from application tests that have not yet run.

The [Phase 3 architecture](architecture/phase-3-architecture.md), [data model](architecture/phase-3-data-model.md), and [API/event contracts](architecture/phase-3-api-events.md) define the implementation baseline. [Phase 3 verification](architecture/phase-3-verification.md) maps all student acceptance cases to architecture responsibilities and distinguishes reference-model checks from integration tests.

The [Phase 4 pipeline](ai/phase-4-pipeline.md) and [evaluation plan](ai/phase-4-evaluation.md) define the AI contracts and candidate settings. The [Phase 4 results](ai/phase-4-results.md) distinguish executed contract checks and synthetic local-model trials from uncompleted human review, real-audio STT, and full-lecture evaluation.

The [consolidated specification](../multimodal_academic_learning_system_spec.md), [updated architecture artifact](../multimodal_academic_learning_system_architecture_v2.html), and [Phase 5 roadmap](implementation/phase-5-roadmap.md) reconcile the original documents. [Reconciliation](implementation/phase-5-reconciliation.md) records the decisions; [verification](implementation/phase-5-verification.md) records executed checks. M01–M08 map all 32 UX scenarios and carry six unresolved qualification gates into implementation. Phase 4's human-reviewed fixtures and calibrated quality/performance completion conditions remain open.

Phase 6 / M01 now has a [runnable private workspace preview](implementation/phase-6-m01.md), migrations and backend tests. M01's real-service exit is pending Docker's WSL prerequisite. Next: run PostgreSQL/object/broker and restart checks, then M02 capture. Synthetic results, preview tests and passing design checks do not establish release readiness, browser recovery, or physical storage durability.
