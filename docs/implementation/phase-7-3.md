# Phase 7.3 — Learning tools

Active implementation phase, 2026-09-16, at the user's request. Standalone Windows distribution is the follow-on priority; Phase 7.2 and 7.4 are not prerequisites. This is the first learning increment, not completion of the whole phase or educational qualification. Earlier note-quality and M08 release gates remain open.

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

Next Phase 7.3 increment: add distinct, source-validated question generation and reusable individual flashcards through the explicitly selected model, with immutable generation inputs and protected student changes; establish a separate human-reviewed question-quality fixture covering definitions, conditions and worked examples. Evaluate learning-state transitions and whether personalized practice improves recall before claiming mastery or learning benefit. This first increment provides extractive topic practice and self-assessments only; no automated grading, spaced-repetition schedule or calibrated mastery model is claimed.

Then prioritize standalone Windows distribution using the existing Electron/React/FastAPI boundaries. Resolve packaged service/runtime prerequisites and an explicit existing-library reuse/import path while preserving Docker/PostgreSQL data. Model files remain user-selected; no silent download or external fallback. The current installer still requires Docker Desktop, PowerShell 7, Ollama and a local speech model, and does not include this increment until rebuilt. Clean installation, upgrade/data retention, coordinated restore, endurance, accessibility and real-device qualification remain required. Do not restore the removed Qt application. macOS remains after Windows.
