# Phase 7.3 — Question and learning-quality evaluation

Updated 2026-09-17. This evaluation separates structural checks, question quality, student self-assessments and learning outcomes. A valid citation is not proof of a correct answer. A confidence rating is not measured mastery.

## Executable evaluation

The [synthetic fixture set](../../evaluations/fixtures/questions-v1.json) covers a CS prerequisite, a biological qualification, a numerical worked example and historical evidence limits. Fixtures and review criteria are assistant-authored development data, not human-calibrated or held-out cases. They contain no student data.

Run from the repository root with an already installed local Ollama model:

```powershell
$env:PYTHONPATH='apps/api'
uv run --no-project python -m notetaker.question_evaluation --model qwen3:4b --output evaluations/local-runs/questions/report.json
```

The harness has no cloud fallback and does not download models. It records model identity, input/prompt/schema hashes, output, elapsed time, deterministic fixture signals, and empty human-review fields. It reports provider failure separately from unexecuted output checks. Per-case reports are saved as they finish. Use `--case` with a fixture ID for a specific rerun.

The runtime checks question count/kind/shape, nonempty and nonduplicate wording, exact source IDs and quotes, and numeric literals against cited source text. The whole generated set fails visibly if one question fails validation; existing sets are retained. Numeric checking is deliberately conservative: alternative numeric formatting or numbered answer lists may also be rejected. It does not establish units, factual accuracy, implied causality or semantic entailment. Set-wide pattern diagnostics detect selected omissions and prohibited phrases in these fixtures; they can miss incorrect paraphrases or flag contextual negation. They never substitute for reviewing each question.

## Quality rubric in the app

Each question has four separate student-entered quality dimensions. Score **0 — fails**, **1 — needs improvement**, **2 — meets criterion**, or leave **not reviewed**.

| Dimension | Review task |
| --- | --- |
| Source support | Check every answer claim against original evidence. Preserve negation, conditions, units and worked steps; reject invented values or visual details. |
| Answerability | Ensure the question can be answered fully from the supplied material. No required outside knowledge, missing diagram or unstated premise. |
| Clarity | Check specificity, unambiguous wording and answer giveaways. A calculation question should ask for the reasoning it expects. |
| Study usefulness | Check the importance of the target idea, appropriate depth and redundancy within the set. |

Saving a quality review or wording correction appends a question revision with feedback. The generated original and all prior revisions remain available for comparison and undo by loading a prior version into a new saved draft. Wording changes clear the editor's quality scores until reassessed. Self-assessments start fresh for each saved question revision. Scores below 2 pause self-assessment until concerns are resolved; unreviewed questions remain clearly labeled as unreviewed. A stale source/selected note revision blocks self-assessment even when its quality scores were previously positive. These controls are tested independently of generation.

## Executed observations and limitations

The [initial model run](../../evaluations/reports/phase-7-3/qwen3-4b-before-grammar-fix.json) failed before generation because Ollama could not compile the full Pydantic schema as a grammar. The adapter now supplies a simplified, inlined grammar and independently enforces the complete contract on output and again at persistence.

The [next run](../../evaluations/reports/phase-7-3/qwen3-4b-before-content-hardening.json) demonstrates why citation validity alone is insufficient. Assistant inspection found an enzyme question inventing a free-energy value and a rate multiplier, then describing equilibrium position as a free-energy value. Its quotes were real, and the fixture's keyword diagnostics passed, but it failed source support and answerability. A physics set gave the correct final distance and constant-speed requirement while omitting the requested worked calculation. These findings led to the numeric-literal rejection check and a stronger instruction to include intermediate steps. A CS provider failure and unusually long interrupted execution times are retained; these runs do not qualify model latency.

The [final rerun](../../evaluations/reports/phase-7-3/qwen3-4b-questions-v1.json) returned **8 questions in 4/4 completed requests**, all passing structural/citation checks. **3/4** cases passed the fixture pattern diagnostics. The physics answer still omits `3 × 4 = 12` even though it gives the correct result and constant-speed assumption. These requests took 26.75–45.17 seconds on this Windows development run; this small sequential fixture trial is not a live-workload latency qualification. All human-review fields remain empty. Assistant inspection and deterministic checks are not a human educational evaluation. No learning outcomes have been measured, no paid provider was exercised, and these development fixtures cannot establish general performance across subjects.

Assistant audit of the final outputs (not human rubric scores): CS q2's wording implies unsorted input always fails, although its answer correctly says correctness is not guaranteed; revise that cue. Biology q2 asks for conditions but answers with a mechanism, and q3 overlaps with q2; refine specificity and reduce redundancy. Physics q1 preserves the result/assumption but needs the intermediate calculation required by the fixture. The history pair preserves the distinction between a request and a confirmed policy change. These findings remain recorded despite passing structural checks and, in most cases, passing keyword diagnostics.

## Human qualification still required

1. Have a subject-competent reviewer verify original notes and sources before rating questions. Keep source errors distinct from question errors. Add representative held-out course sections with uncertainty, exceptions, corrections and genuine worked examples.
2. Review each question using all four rubric dimensions, record the exact saved version, rationale and severe-error flags, and resolve disagreements explicitly. Proposed acceptance for a reviewed question: 2 on every dimension and no invented fact, missing essential qualification or unsupported worked step. The threshold is a development proposal, not a calibrated accuracy claim.
3. Report counts and denominators separately: attempted/failed requests, returned questions, reviewed questions, fully supported questions, excluded questions and objective coverage. Do not hide failures by reporting only accepted outputs or reuse prompt-tuning fixtures as held-out evidence.
4. Test learning-state correctness independently: retry does not double-count; conflicts preserve drafts; source/answer changes invalidate prior confidence; reset appends history; flagged questions cannot be assessed; deletion removes learning content and prevents late revival. Automated synthetic tests exercise these transitions.
5. For an actual learning-outcome pilot, first define comparable unseen recall/application tasks and a scoring rubric. Record baseline performance, study exposure, immediate recall and delayed recall at a prespecified interval. Compare notes-only and question-assisted study with balanced order and comparable material; keep grading separate from self-confidence. Track exclusions and participant count. No pilot, participants, measured effect, optimal interval or causal benefit is claimed here.

Human quality and learning-outcome qualification remain open; they do not authorize microphone testing. The user's follow-on priority is standalone Windows distribution, with existing note/release gates retained.
