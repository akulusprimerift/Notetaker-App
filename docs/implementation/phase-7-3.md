# Phase 7.3 — Learning tools

Active implementation phase, updated 2026-09-17, at the user's request. Extractive recall practice and generated-question increments are implemented. Standalone Windows distribution is the follow-on priority; Phase 7.2 and 7.4 are not prerequisites. This is not educational qualification or completion of every Phase 7.3 quality gate. Earlier note-quality and M08 release gates remain open.

## Generated question increment — 2026-09-17

Study tools → **Generated questions & flashcards** accepts one eligible saved note section, a requested kind (mixed/flashcards/practice), up to eight questions and an optional study focus. It displays the selected note model; cloud models require explicit confirmation for this request's note text, sources and focus. No alternative provider or model is chosen automatically. A new set is saved separately; the student can reopen older sets without generation overwriting edits. Fewer questions may be returned if evidence is limited. Requests larger than the bounded context fail visibly; at most one pending request and 100 retained question requests per lecture are allowed.

The existing note worker processes durable `learning.generate` jobs after note work and shares the notes inference slot. Lease renewal, reclaim tokens, current selected note revision, settings/model identity, source versions and lifecycle/audio epochs fence preview and publication. Cancellation prevents late publication; failed/invalid requests retain previous valid sets. Previews are explicitly unvalidated and separate from saved questions. Output checks run both in the provider adapter and at persistence. They reject unknown/nonliteral citations, duplicate/blank questions, wrong kind/count and invented numeric literals. They do not establish semantic support, source quality or pedagogical value.

Migration **0017** adds pinned question sets and append-only question edits. Question wording, answers, four quality scores and feedback can be revised with expected-version/idempotency protection. Conflicts preserve the open draft; saved versions can be inspected and either loaded or explicitly used as the base for retaining the draft. Undo loads an earlier version into a new revision; it never destroys history. Citations remain pinned and student-edited answers are labeled honestly. Unsaved question drafts and scratch answers are temporary to the open card; their limits are displayed.

Each question has self-assessments distinct from **Source support**, **Answerability**, **Clarity** and **Study usefulness** quality scores. Ratings start fresh after any saved question/quality revision. Flagged quality scores pause practice assessment; stale note/source selections block it as well. Old sets and their original evidence remain readable. Lecture deletion erases sets, previews, edits and assessments and fences late writes/replays. Final note snapshots and note exports remain unchanged.

New API routes below `/lectures/{lecture_id}/study/questions`: GET inventory and POST enqueue; GET `/{set_id}` and POST `/{set_id}/cancel`; GET `/{set_id}/{question_id}/history`; POST `/{set_id}/{question_id}/edits` and `/reviews`. All reads require owned live lectures; all writes retain CSRF, receipts and lecture locks.

### Evaluation and engineering evidence

See the [separate evaluation report and human-review protocol](../ai/phase-7-3-learning-evaluation.md). The installed `qwen3:4b` final synthetic run returned **8 questions across 4 successful requests**, with all structural/citation checks passing and **3/4** fixture pattern checks passing. The physics answer still lacks its intermediate calculation. Assistant inspection also identifies wording/redundancy refinements; human rubric fields remain unfilled. Original failed/adverse runs are retained rather than replaced by only passing results. No model was downloaded, no real lecture data or microphone was used, and no paid provider was exercised.

Chromium checks pass on the actual React UI with mocked APIs: explicit cloud consent; request retry preserves ID/body; unvalidated preview; cited answer reveal; self-assessment; conflict/compare preserves drafts; quality gating; saved history/undo; stale-source blocking; Midnight and 400px layout. The narrow generated-question screenshot was inspected. Existing study UI checks also pass. Frontend typecheck/lint, production web build, 60 JavaScript contracts and 12 desktop policy tests passed. The stable backend suite passed **216 tests, with 1 service-dependent skip**, including 26 new question/adapter/evaluation tests. Python lint, documentation and whitespace checks passed. An initial UI check exposed verbose textarea accessible names; explicit control labels fixed them. A long-running backend run spanned the grammar edit and observed a mixed-import failure; the stable final run supersedes it.

## Implemented student workflow

Study tools now includes **Recall practice**. Each eligible saved note section becomes a topic recall card. The student can recall mentally or type an optional scratch answer, reveal the complete saved section, and inspect its exact cited source text and recording timestamp or material label. Prompts are templates, not new model-generated questions. Answers preserve paragraph, code and equation whitespace, and student edits are labeled as not independently verified.

Students record **Needs review**, **Developing** or **Confident**, or reset an assessment. Saved ratings persist across reloads. All topics, a needs-practice filter (including unreviewed topics), and topic search support personal study focus. The displayed count is self-reported confidence, never an objective mastery score. Scratch answers are explicitly temporary and ungraded; changing cards, filtering, refreshing or leaving clears them.

Cards use the selected student revision when present, otherwise the latest generated revision. A visible source-revision disclosure identifies the exact selection. Complete blocks are retained: if any passage lacks supported citations, refers to a superseded transcript, includes uncited AI explanation or contains a visual diagram, omit the whole block rather than remove a qualification from an answer. Source warnings and omitted counts are displayed. No transcript-only fallback invents study answers. Topic prompts can be broad, and a citation does not itself establish semantic correctness.

## Persistence and API

Additive migration **0016** creates `learning_reviews`. Reviews append immutable events keyed by lecture, exact note revision, block and version; resetting appends an `unreviewed` event. An answer change starts fresh assessments while retaining prior history. Revision IDs can reference generated or selected student notes and are checked through the current owned lecture, never accepted as arbitrary content references.

- `GET /lectures/{lecture_id}/study/learning`: selected revision, eligible cards, source evidence, warnings, latest assessment for each card.
- `POST /lectures/{lecture_id}/study/learning/reviews`: strict revision/block/rating/expected-version input; ownership, CSRF, mutation receipt, lecture lock and tombstone protection. Recheck selected revision and current sources before accepting a rating. Return 409 for stale content or another window's assessment.
- Retry uses the same request key and body after an uncertain save; a replay returns the original assessment without another history row. Lecture deletion removes review history through the existing dependency-ordered erasure; even an old successful receipt cannot bypass a tombstone.

Recall practice is independent of recording and inference. No new worker or provider call, model download, microphone use, existing-library migration, installation or external publishing occurred. Detailed notes, exports and final snapshots are unchanged. Current selected notes, rather than a chosen historical final snapshot, drive practice in this increment.

## Executed engineering evidence

Windows development environment, synthetic sources/audio only:

- Full backend suite: **189 passed, 1 skipped** on isolated SQLite databases. The skip needs real PostgreSQL/object services. After adding the explicit pre-0016 upgrade preservation check and unauthenticated access assertion, all **5 learning tests** passed. Existing dependency deprecation warnings remain.
- Tests exercise complete answer preservation, CSRF/authentication, same-lecture scoping, append-only assessment/reset history, idempotent replay, changed-payload rejection, optimistic conflict, source-correction exclusion, selected student edits, revision reset, deletion/tombstone replay, mixed unsupported evidence, and additive upgrade from 0015 preserving an existing lecture.
- **60 JavaScript contracts**, **12 desktop tests** passed.
- Chromium against the real React UI with synthetic API responses: reveal and inspect evidence, edited-answer label, save failure/retry identity, retained scratch answer during retry, saved-rating refresh, review filter, conflict blocking/recovery and reset. Existing marker, catch-up and glossary flows also pass. Midnight and 400px layout passed; the narrow screenshot was visually inspected under `.local/study-review`.
- TypeScript, frontend lint, Python lint, final production web build, documentation and whitespace verification passed.

The first mixed-evidence fixture used a shallow JSON copy, so SQLAlchemy did not persist its synthetic modification. A deep copy fixed the test fixture; the complete-block exclusion test then passed in the full and focused runs.

## Remaining work and standalone handoff

Generated questions, individual flashcards, protected revisions and a reproducible synthetic evaluation are now implemented as described above. Remaining Phase 7.3 qualification: improve worked-step coverage, review questions on human-verified and held-out notes, calibrate question-quality criteria, and evaluate whether personalized practice improves recall. No automated grading, spaced-repetition schedule or calibrated mastery model is claimed. The next user-selected delivery priority is standalone Windows distribution; explicitly retain these earlier qualification gaps while proceeding with independent packaging work.

Then prioritize standalone Windows distribution using the existing Electron/React/FastAPI boundaries. Resolve packaged service/runtime prerequisites and an explicit existing-library reuse/import path while preserving Docker/PostgreSQL data. Model files remain user-selected; no silent download or external fallback. The current installer still requires Docker Desktop, PowerShell 7, Ollama and a local speech model, and does not include this increment until rebuilt. Clean installation, upgrade/data retention, coordinated restore, endurance, accessibility and real-device qualification remain required. Do not restore the removed Qt application. macOS remains after Windows.
