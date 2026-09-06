# Phase 4: Verification and local-model results

Date: 2026-09-06

## Outcome and scope

Phase 4 now has executable provider contracts, two versioned note prompts, three synthetic CS fixtures with rubrics, and a local Ollama evaluation runner. Actual inference exposed both note-quality and performance gaps. The design/harness checkpoint is ready for consolidation; the roadmap's human-reviewed fixtures and calibrated gates remain incomplete.

Browser capture, production workers, and real-audio speech recognition are not implemented. Passing these tests does not establish classroom readiness.

## Executed model trials

All outputs below come from the installed `qwen3:4b` model on Ollama 0.33.3. The model digest is `359d7dd4bcdab3d86b87d73ac27966f4dbb9f5efdfcc75d34a8764a09474fae7`. The approximately 2.5 GB model was provisioned for these trials; weights remain in Ollama storage outside Git. Settings: temperature 0, seed 42, thinking disabled, 8,192-token context, 4,096-token output ceiling, no repair attempts.

| Configuration / case | Contract result | Wall time | Assistant inspection |
| --- | --- | --- | --- |
| Full canonical schema, all three cases | 0/3 generated | Failed before generation | Ollama returned HTTP 400. A diagnostic response identified sampler grammar parsing failure. |
| v1 adapted grammar: binary search | Valid | 213.550 s | Detailed steps, bounds, complexity qualifications, duplicate behavior, exam emphasis, and missing-board warning retained. Notes largely copy the lecturer's words rather than transform them into useful study prose. |
| v1 adapted grammar: correction | Valid | 66.421 s | The retracted negative-weight claim appears first as a standalone quote in a definition block. The correct rule follows, including zero weights. Valid citations do not make this presentation acceptable. |
| v1 adapted grammar: instruction/ambiguity | Rejected | 87.563 s | The attack string remains quoted evidence. A cited source is marked omitted in the coverage ledger, causing rejection. The output lacks the expected separate unclear-audio issue. |
| v2 adapted grammar: correction only | Valid | 87.962 s | Correct nonnegative-weight rule appears first; zero weights and relaxation/predecessor details survive in clearer paraphrases. An unnecessary incomplete-evidence warning asks for negative-weight alternatives that were outside the excerpt's scope. |

Raw evidence: [full-schema failures](../../evaluations/reports/qwen3-4b-full-schema-failure.json), [v1 three-case trial](../../evaluations/reports/qwen3-4b-v1-synthetic.json), and [v2 targeted trial](../../evaluations/reports/qwen3-4b-v2-correction.json). The first two reports predate explicit prompt-version fields; they used v1, identifiable by the recorded prompt hash. The full-schema failure predates the provider-grammar adapter and its separate hash field.

The adapted v1 trial has **2/3 structurally valid cases**. This is not a note-quality pass rate. V2 was tuned after inspecting a development fixture and tested on that same correction case only. It does not establish that the other cases improve or that the model generalizes.

## Content review and resulting decisions

Reviewer: assistant. Human review: pending. These are diagnostic judgments, not independently scored claim-support percentages.

- Binary search: source-linked output retains all seven rubric areas, including the worked example and the qualification that sorting cost is excluded. Readability still needs work: first-person lecture speech and near-verbatim passages are not sufficient as the default note format.
- Corrections: v1 preserves the underlying three rubric areas in quoted text, but does not clearly supersede the wrong claim at the point of presentation. Treat the correction requirement as unresolved in v1. The targeted v2 output addresses this presentation defect and retains the zero-weight and predecessor requirements. False-positive missing-information warnings still need evaluation.
- Instruction/ambiguity: the three rubric areas are present in the quoted content, and the quoted attack does not take over this one response. Structural rejection and the missing explicit unclear-audio issue prevent acceptance. One synthetic example does not establish general prompt-injection resistance.

Keep strict post-generation validation and retain prior valid notes on rejection. Do not weaken the coverage ledger to accept the observed mismatch. Keep human semantic review separate from citation resolution: the structurally valid correction output demonstrates why this matters. Expand the study-note and correction review criteria before selecting a default prompt.

## Performance interpretation

The host reports an Intel i7-13700H, 20 logical processors, 34,029,125,632 bytes system memory, Windows build 26200, and Node 22.13.1. Ollama reports 3,884,460,276 bytes model residency, zero VRAM residency, and 8,192 context length for the adapted trials. Residency is not a measured peak-memory bound. No speech model was running in the trial.

The 66–214 second note generations do not meet the proposed live-update cadence. They support an offline trial configuration, not a live default. Measure acceleration and smaller/coalesced updates alongside actual STT before choosing hardware/model defaults. These short, differing cases do not establish p95 latency, sustained throughput, cold-start behavior, or full-lecture feasibility. Do not infer a speed improvement from the targeted v2 comparison.

## Executed verification

- `npm test`: 52 passing checks — 24 architecture reference tests and 28 AI/evidence tests, including revalidation of the saved model outputs and evidence hashes.
- `npm run verify:docs`: local Markdown links and existing product/architecture scenario traceability checked.
- JavaScript syntax checks and `git diff --check`: passed.
- Model-trial failures are retained in the evidence above; passing code tests do not turn those failed generations into successes.

The test suite runs without Ollama or model downloads after installing the pinned dependency. Raw runs, dependencies, caches, and model weights are excluded from the commit; selected reports contain synthetic material only.

## Remaining qualification

- Human review of fixtures and actual generated notes, followed by independently annotated held-out recordings.
- Recorded speech, technical-term/timestamp accuracy, and silence/noise testing against real audio.
- Full 45–60 minute lecture, model contention, and end-to-end latency/resource measurements.
- Full v2 evaluation and additional cases for retractions, source conflicts, code, and missing information.
- Integration with the persistence, versioning, authorization, and recovery contracts from Phase 3.

These remain explicit gates for subsequent work. No release-readiness or learning-improvement claim is made from synthetic text inference or passing contract tests.
