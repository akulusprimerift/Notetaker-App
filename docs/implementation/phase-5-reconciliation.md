# Phase 5: Reconciliation record

Date: 2026-09-06. Decision status: implementation baseline; no new release claims.

The [consolidated specification](../../multimodal_academic_learning_system_spec.md) replaces the original first-release blueprint. The [v0.2 specification](../archive/original-spec-v0.2.md) and [v0.2 HTML](../archive/original-architecture-v0.2.html) preserve the source content unchanged; Git history also retains the originals. The root HTML filename remains stable, while its title/version and content now describe the current design.

## Decisions carried into the baseline

| Earlier source / conflict | Consolidated decision | Rationale and evidence |
| --- | --- | --- |
| Original spec §§1–4, 67: Capture → Understand → Practice → Measure → Personalize and wide feature checklist | Capture → Transcribe → Organize → Verify → Study from the notes. Keep ten core requirements; learning tools are later. | User prioritized excellent lecture notes above the other capabilities; Phase 1 formalized this scope. |
| Original §61 Phases 3–5: RAG and phone capture precede final STT/notes | Finalization and source-linked export are core; RAG/vision depend on course evidence. | A student needs usable completed notes before expansion. G05 explicitly checks whether visual evidence must move forward. |
| Original §§6, 57: separate realtime service and broad worker tree | One FastAPI application for REST/WebSocket, one shared Python codebase with separate worker processes. | Phase 3 modular boundaries avoid premature service coordination; no empty worker directories in Phase 5. |
| Original §§1, 61: Valkey, pgvector and registry in early stack | No initial Valkey/vector/document/vision dependency; versioned JSON events first. | Existing ownership/version/job state belongs in PostgreSQL. Measure need before cache, retrieval or schema-registry expansion. |
| Original §61 Phase 6: transactional outbox appears with later reliability work | Job ledger, outbox, immutable upload reservations, epochs and authorization are foundational. | Acknowledgement and recovery cannot rely on best-effort notification or later hardening. M01–M04 implement the relevant contracts as content is introduced. |
| Original §55: Kafka consumer lag as primary backlog signal | Track time behind the lecture, pending bytes and per-stage jobs alongside broker lag. | Capture, speech and notes have different work sizes; DB reconciliation must survive broker outages. |
| Original §§4, 56: Fully Local / Hybrid / Cloud choices | First release exposes Fully Local only; process-later is a schedule. | Phase 3 privacy decision; no tested external provider adapter and no implicit fallback. |
| Original §59: transcript and notes each target p95 under three seconds | No certified latency target. Define endpoints and calibrate before held-out qualification. | Phase 4 short note trials took 66–214 seconds; live cadence remains unresolved, not removed. |
| Phase 1: CS a candidate domain | CS algorithms/code is the first sample domain; English remains an assumption. | User selected the course type during Phase 2. |
| Phase 3: host details unavailable | Record observed i7-13700H, approximately 32 GB RAM and zero model VRAM residency in the note trial. | Phase 4 read-only host/model observations; not minimum sizing, absence-of-GPU proof or simultaneous-STT qualification. |
| Phase 3: Phase 5 will turn the schema into migrations | Phase 5 orders migration/interface packages; executable DDL and generated APIs are owned by M01–M07 in Phase 6. | Logical contracts exist; a pinned runtime/service implementation does not. Avoid unsupported SQL or a claim that migrations ran. |
| Phase 4 intended human-reviewed fixtures/calibrated gates | Mark those completion conditions open in G01–G03/G05. Design/harness progress is distinct from qualification. | Only synthetic text fixtures, assistant inspection and a targeted v2 trial exist. Planning can continue without certifying quality. |
| Original §§61–64: platform stack and resume examples | Retain as historical ambitions and evidence-driven later experiments. | No Kubernetes, autoscaling, learning effectiveness or production claim without implementation and measurement. |

## Model-output lessons that must survive implementation

- Exact citations can support badly presented notes: v1 placed a retracted incorrect statement first in a definition block. Test semantic content and correction presentation, not only schema validity.
- A cited source marked omitted is a rejected proposal; do not relax coverage consistency to improve acceptance counts.
- V2 improved one tuned correction fixture and added an unnecessary missing-information warning. It is not a three-case or held-out pass.
- CPU-resident short note trials are inadequate evidence for live lecture throughput. G03 requires simultaneous speech/note measurements and a declared workable configuration.
- A missing-board warning identifies a limitation; it does not recover the board. G05 has an owner and must be resolved on representative course evidence.

## Current authority and change control

Use the root consolidated specification for scope and the [roadmap](phase-5-roadmap.md) for priority/exit evidence. The Phase 2 workflow and Phase 3/4 technical documents retain detailed contract authority where incorporated. Earlier phase status statements are historical observations; the current specification and measured results state what is known now.

Product-development phases remain 1–7. M01–M08 are implementation increments inside Phase 6. The original zero-based Phases 0–9 are archived and no longer an active build order.

Record future scope/contract changes with motivation, impacted requirement/UX IDs, evidence and revised gates. Do not weaken a source, edit-protection, privacy or quality requirement merely because a candidate fails. No user approval of an unmeasured numerical threshold is implied by proceeding to the next phase.

## 2026-09-07: Windows desktop delivery

The user explicitly requires a Windows application by the end of development. The current browser UI becomes the development preview; M08 now owns an installable desktop host, service startup/shutdown, user-data/model paths, upgrade preservation and clean-machine qualification. This extends delivery and G06 evidence without moving optional learning tools ahead of note quality. CAP-01, CAP-02, PRIV-01 and UX-01/UX-02/UX-29/UX-31/UX-32 must be exercised in the selected desktop runtime. Wrapper technology and service bundling remain a recorded architecture decision before packaging; no installer or desktop capture support is claimed today. Earlier browser-only scope statements are historical.
