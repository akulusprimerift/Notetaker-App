# Phase 4: AI pipeline and provider contracts

Version: 0.1

Date: 2026-09-06

Status: Defined contracts, executable validators, and a local note-model evaluation harness. The full speech/capture pipeline is not implemented.

The [architecture](../architecture/phase-3-architecture.md) remains authoritative for persistence, jobs, revisions, and student-edit protection. This phase defines how source audio becomes transcript evidence and detailed note proposals. Practice, mastery, retrieval, embeddings, and vision remain deferred.

## AI-01: Candidate models and operating modes

| Role | First candidate | Configuration and qualification boundary |
| --- | --- | --- |
| Live speech | faster-whisper `small.en` | CPU `int8` baseline for English. Selected for initial measurement, not claimed to meet live latency or technical-term accuracy. |
| Final speech | faster-whisper `medium.en` | Candidate higher-capacity final pass; compare against the live model on identical audio before selecting it as a default. No speech model was provisioned or benchmarked here. |
| Detailed notes | Ollama `qwen3:4b` | First bounded local trial: temperature 0, seed 42, thinking disabled, 8,192-token context, 4,096-token output ceiling. Pin actual model digest in each report. |
| Later note challenger | Ollama `qwen3:8b` | Compare only after the first candidate and reference data expose a quality gap worth the extra resources. Not installed or benchmarked in this phase. |

These are candidates for the first implementation, not a certified recommendation. faster-whisper documents CPU/GPU execution and explicit transcription options; its performance examples do not establish this app's performance. [Faster-whisper documentation](https://github.com/SYSTRAN/faster-whisper)

The local trial host reports an i7-13700H, 20 logical processors, about 32 GB RAM, and Windows build 26200 through Node's read-only OS interface. This resolves the earlier inability to read basic CPU/RAM details through CIM. Ollama reports version 0.33.3. GPU availability is not inferred from CPU/RAM; the actual model residency reported by Ollama is recorded per trial.

The executed note-only trial reported zero model VRAM residency and took 66–214 seconds per short synthetic case. This configuration has not met the live-note requirement. Keep it as an offline evaluation candidate; measure acceleration, smaller/coalesced updates, and simultaneous speech processing before enabling it as a live default. See the [measured results](phase-4-results.md).

The Qwen3 4B model tag is approximately 2.5 GB in the model registry, and supports a non-thinking path. Model tags can change, so the registry name alone is not a reproducible version. [Ollama Qwen3 4B entry](https://ollama.com/library/qwen3:4b)

Live STT and notes share a memory/inference budget. Start with one active call per role and no speculative parallel final pass. If STT cannot keep up, retain audio, show backlog, defer notes, and offer record-now/process-later. Never switch to external inference silently. CPU/GPU concurrency, RAM/VRAM peaks, and sustained real-time factor remain to be measured together.

## AI-02: Audio windows, provisional text, and final speech

Transport remains independently decodable approximately two-second PCM WAV chunks. Inference does not transcribe each transport chunk in isolation.

Initial live decoding policy to implement and evaluate:

1. Reconstruct only contiguous verified audio for one capture run; map resampled audio back to original sample coordinates.
2. Begin with a six-second speech context and refresh after at least two seconds of new audio, bounded by worker capacity. Extend unresolved context up to 30 seconds without crossing a recorded gap.
3. Enable voice-activity detection as an optimization, preserving sample positions. Silence yields no invented transcript. Noise/uncertainty is distinct from confirmed silence.
4. Publish provisional text immediately after a successful decode. Promote a prefix only after agreement across two consecutive overlapping decodes with consistent timing; normalize whitespace for comparison but preserve spoken negation, numbers, symbols, and identifiers.
5. Retain a short unsettled tail. If ambiguity persists at the window boundary, emit an uncertainty marker and a versioned segment rather than discarding audio or asserting a false stable word.
6. Avoid duplicated overlap by merging on source sample spans and token alignment. A genuine lecturer repetition must not be removed merely because its text matches an earlier sentence.
7. Finalize against the sealed audio snapshot. Preserve human corrections and prior cited versions; model cleanup proposes a new version rather than rewriting evidence.

The six/two/30-second values are tunable starting points, not measured latency guarantees. faster-whisper's ecosystem includes streaming wrappers around the inference backend; selecting the backend alone does not implement this streaming policy. [Faster-whisper streaming integrations](https://github.com/SYSTRAN/faster-whisper)

The [speech result schema](../../contracts/ai/speech-result.schema.json) describes normalized provider output: capture run/window identity, actual source sample rate and interval, ordered segments, provisional/stable state, and silence/speech/uncertain outcome. Its validator rejects overlapping/reversed/out-of-window segments and speech inside a silence result. No source-quality percentage is invented: confidence is unavailable or explicitly an uncalibrated score.

A provider exception is a job failure, not an empty successful speech result. Speech schema validation does not prove the recognized words are correct. Word timestamps and segment boundary policy need real-audio evaluation.

## AI-03: Terminology and corrections

Use an optional explicit course glossary as hints when the chosen backend supports it. Treat glossary text as data and cap its contribution to the prompt. A likely course term is not evidence that it was spoken.

Keep raw recognition and corrected transcript as distinct versions. Suggested term normalization must cite the original audio span, retain uncertainty when unsupported, and never overwrite a student correction. Preserve exact code identifiers and distinguish ambiguous letters/numbers rather than silently applying dictionary spelling.

A later explicit lecturer correction should update the current explanation while preserving that a correction occurred. Contradictory statements with no explicit resolution remain flagged. The synthetic graph fixture distinguishes nonnegative weights from strictly positive weights and tests whether an earlier incorrect claim is superseded.

## AI-04: Topic context and detailed notes

Generate note proposals from stable transcript versions plus a labeled provisional tail where useful. Group by topic continuity, definitions, worked examples, and transitions. Elapsed time alone does not create a topic boundary.

Initial trigger: a completed explanatory passage, a detected transition, or approximately 12 seconds of new stable speech while an active topic develops. Coalesce overlapping note jobs when processing falls behind. This trigger is a scheduling proposal, not a promise of 12-second note latency.

Compute each input budget as model context minus system/schema instructions, reserved output, and a safety margin. The trial reserves 4,096 output tokens within 8,192 total context tokens; production must tokenize actual inputs, not assume characters equal tokens. If a topic is too large, split its source spans into ordered subtopics while carrying definitions and unresolved references forward.

Final notes are generated per coherent topic from the pinned final transcript. Stitch validated blocks deterministically, preserve examples and conditions, and deduplicate only genuine redundancy. Do not run a global compression step that removes detail simply to fit the entire lecture into one model call. A source-coverage ledger tracks which evidence was used, unclear, or deliberately omitted with a reason; it does not prove all important facts were captured.

## AI-05: Structured note output and provenance

The [note schema](../../contracts/ai/note-output.schema.json) describes a **proposal**, not a published note revision. Source and settings versions are echoed and checked before acceptance. Each block contains passages with evidence kinds; model output cannot claim student authorship or approval.

Each lecture passage cites an exact substring and occurrence within a supplied immutable source version. The server resolves these references to Unicode code-point offsets. The model does not calculate offsets. A paraphrase can cite an exact supporting excerpt; a passage labeled exact_quote must itself equal that excerpt verbatim.

The [validators](../../evaluations/lib/contracts.mjs) reject unknown source IDs, absent quoted text, duplicate block/passage IDs, missing coverage entries, unauthorized AI explanations, and stale source/settings metadata. They validate shape with pinned Ajv and JSON Schema 2020-12. [Ajv schema documentation](https://ajv.js.org/json-schema.html)

Ollama accepts a schema through its `format` field, but its generation grammar is not a substitute for application validation. The tested runtime rejected the full canonical schema while initializing the sampler. The adapter therefore inlines local references and omits size/range/uniqueness limits from the provider grammar; the original canonical schema and semantic reference checks still enforce those limits afterward. Both schema hashes are recorded in reports. [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs)

Generation validation sequence: completed provider response → JSON parse → canonical schema → source/settings/citation checks → semantic quality review policy → Phase 3 version/attempt/epoch checks → staged or published revision. A successful source link cannot establish that the cited passage supports the generated claim; the tests explicitly demonstrate this limitation.

## AI-06: Prompt boundaries and failure behavior

The [versioned note prompt](../../prompts/note-generation-v1.txt) is trusted application configuration. A separate user-role message contains an explicit allowlist of source records and supported note preferences. Evaluation rubrics, answer keys, review labels, and student approval fields are never passed to the model.

The [v2 development prompt](../../prompts/note-generation-v2.txt) adds explicit study-note transformation and correction-first rules after inspecting v1 output. It has only a targeted correction-case trial, not a complete three-case rerun or held-out evaluation. Keep both prompt versions and their separate evidence records.

Source text may quote instructions, including a lecture about prompt injection. Delimiters and role separation help organize the request but do not prove resistance; evaluate the output. The model receives no tools, cannot publish or delete data, and does not choose its own evidence origin or privacy mode. Output rendering still requires the Phase 3 sanitization boundary.

An incomplete/length-limited generation fails validation. Keep the prior notes; split the task or retry once with a smaller coherent source window and preserve failure evidence. Do not invent sources or edit the reference text to make invalid citations pass. Contract failures have a distinct error category from service/network failures; repeated retries cannot manufacture quality.

The evaluation runner performs one generation per fixture, with no automatic repair, so first-attempt defects remain observable. The application implementation may add one bounded repair attempt using validation error codes and the same source snapshot. Report both first-attempt and post-repair validity, and never relax citation requirements to improve the pass rate.

## AI-07: Deferred capabilities and qualification

The [evaluation plan](phase-4-evaluation.md) and [results](phase-4-results.md) specify the evidence boundary. Synthetic text tests isolate note behavior; they do not establish classroom STT accuracy, full-lecture retention, educational outcomes, or human acceptance.

No real audio fixture or human-reviewed dataset was supplied. The three included fixtures and rubrics are assistant-authored synthetic development material. Human review and a held-out real-lecture corpus remain required before calibrating or claiming the Phase 1 numerical quality targets.

Vision remains deferred for audio-recoverable algorithms/code. The missing-board cases require explicit limitations; if human evaluation shows those omissions prevent useful study notes in the selected course, advance slide/board ingestion through an explicit scope revision. Do not treat a synthetically correct missing-visual warning as recovery of the visual itself.
