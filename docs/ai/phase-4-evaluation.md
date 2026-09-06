# Phase 4: Evaluation protocol

## Evidence levels

| Level | What it tests | What it does not establish |
| --- | --- | --- |
| Contract tests | JSON shape, source resolution, version binding, confidence representation, review arithmetic. | Semantic truth, model quality, browser capture, or distributed correctness. |
| Synthetic note trial | Actual local inference on known text covering detailed notes, corrections, and adversarial/ambiguous evidence. | Real speech recognition, representative student experience, or full-lecture coverage. |
| Human-reviewed real lecture | Transcription and note quality against annotated recording/source evidence, with subject review. | Broad generalization without multiple courses and held-out examples. |
| Endurance/integration | Capture, STT, notes, edits, finalization, latency, resources, and failures over a complete lecture. | Learning benefit without a separate student study. |

## Included development fixtures

The [fixture collection](../../evaluations/fixtures/cs-notes-v1.json) contains three synthetic English CS excerpts with 12 source records and 13 rubric items. Timestamps are illustrative and have no associated recording. Dataset metadata explicitly marks human review pending.

| Case | Purpose | Expected concerns |
| --- | --- | --- |
| binary-search-detail | Definitions, loop/pseudocode, worked steps, complexity conditions, exam emphasis. | Preserve half-open bounds, sorting exclusion and duplicate behavior; flag the unavailable board proof. |
| correction-and-conditions | Lecturer corrects a claim about Dijkstra's algorithm, then explains relaxation. | Retain the correction and zero-weight allowance, and preserve predecessor updates. |
| quoted-instruction-and-ambiguity | Lecture quotes an attack string and includes an inaudible term/absent diagram. | Treat the string as evidence rather than instructions; do not invent missing content. |

All three cases are development fixtures. Do not tune a prompt on them and later call them a held-out test set. Before release, add independently reviewed recordings covering rapid/noisy speech, technical identifiers, negation, equations, code, missing audio, and a complete 45–60 minute lecture. Annotate sources and key items before exposing candidate output to reviewers.

## Metrics and reviewer procedure

1. Freeze fixture, transcript, prompt, schema, model digest, and settings. Record hashes and environment, with model residency reported separately from total system RAM.
2. Run every eligible fixture and keep failures/timeouts in the denominator. Report first-attempt structural validity and citation resolution. Do not discard a failed runtime/grammar configuration from the historical record.
3. For note quality, inspect each rubric item against the actual note and source. Mark covered/missing/ambiguous with passage references and a reason. Require full coverage of a multi-part item to count it covered; otherwise split the item before comparing candidates, not after seeing results.
4. Review claim-level source support, including qualifiers and corrections, and mark critical errors separately. A valid exact substring is insufficient when it is cited for a contradictory paraphrase.
5. Record reviewer identity type: human or assistant. Assistant review is useful diagnosis and must not be reported as independent human approval. The [review summarizer](../../evaluations/lib/contracts.mjs) refuses incomplete/invalid counts and never grants release eligibility from a fixture score.
6. Track correction time, editing categories, missing intermediate steps, and readability alongside numeric coverage. Prefer a blind comparison of candidates on identical evidence/settings when enough data exists.

Proposed Phase 1 gates remain: at least 90% annotated key-item coverage, every recoverable critical item, at least 95% reviewed claim support, and zero unflagged critical errors/fabricated lecturer attribution. These thresholds are **not calibrated** by three synthetic examples. A small multi-part rubric can change drastically with one missing item; report raw counts and uncertainty instead of presenting a precise universal quality score.

For STT, report WER, exact domain-term/identifier errors, meaning-changing errors, and timestamp alignment separately. The provided WER helper uses NFKC, lowercase, and letter/number/underscore tokens; it ignores punctuation/operators, so it must never stand in for equation or code correctness. Empty reference text produces null WER plus insertion counts, not an artificial perfect score.

Measure real-time factor as inference seconds divided by unique source-audio seconds processed, and also report overlap-induced work separately. End-to-end delay includes capture-window waiting, upload, queue, inference, and UI delivery. Report cold/warm runs and p50/p95 only with a stated sample count; three different short fixtures do not support a meaningful classroom p95 claim.

## Run the local note trial

```powershell
npm ci --ignore-scripts
npm test
npm run verify:docs
npm run eval:notes -- qwen3:4b
```

To repeat the targeted v2 development check, use `npm run eval:notes -- qwen3:4b correction-and-conditions v2`. Use `all v2` for a new full v2 run; that full run has not been executed in the recorded results. The default prompt remains v1 so the original baseline is reproducible.

The model must already exist at the loopback Ollama endpoint. The runner permits the two named Qwen candidates, rejects cloud-backed model metadata, and does not download models, accept remote endpoints, or fall back externally. It submits only the synthetic `input` fields; rubrics are excluded. It makes no production database writes.

Each run creates an ignored `evaluations/local-runs/<timestamp>/report.json`, retaining output, validation failure, completion reason, hashes, model digest, CPU/RAM metadata, provider timing, and reported model RAM/VRAM residency. A false `release_eligible` value is intentional. Nonzero exit means execution/contract failure, not an educational score.

Fixture and prompt hashes use UTF-8 text with LF line endings; schema hashes use the parsed schema serialized by `JSON.stringify`. This avoids changing evidence identity merely because Git checks out Windows line endings. Existing reports predate explicit prompt-version/selected-case fields where noted in the results; their hashes and recorded cases identify that configuration.

Before promoting a run to Git, verify that it contains only synthetic material and no private paths, credentials, or user lecture data. Keep selected evidence in `evaluations/reports/` and link its review from the results document. Model weights, npm caches, and routine raw run directories remain ignored.

## Phase 5 handoff gates

- Preserve validated contract behavior and the Phase 3 publication boundary when designing actual provider adapters.
- Require human review of development fixtures and separately annotated held-out audio before labeling thresholds calibrated.
- Implement and test live overlap/prefix handling, silence behavior, terminology hints, full-lecture topic partitioning, and final speech revision protection.
- Benchmark candidate speech models and simultaneous STT/note work on declared hardware; no STT or full-lecture timing is inferred from a note-only trial.
- Decide whether course materials/visual capture must move earlier based on a representative course, not the synthetic warning behavior alone.
