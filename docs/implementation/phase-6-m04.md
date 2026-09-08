# Phase 6.4 / M04: Automatic study notes

Updated: 2026-09-08. Status: bounded automatic notes repaired and verified with real local-model output; course-neutral writing preferences implemented. This first increment implements notes from a bounded saved transcript; it does not close the full M04 qualification gates.

## Product direction

The selected LLM writes the student's notes from lecture context. Students do not have to draft notes themselves. Transcript corrections improve the evidence; manual note editing is an optional later review workflow in M06. Contextual study notes remain the primary product, for any subject and content-heavy course. Computer science is one evaluation subject, not an application restriction; biology and history fixtures now exercise the same path.

Choose a local model, detail level (Detailed/Standard/Brief), layout (Topic outline/Cornell/Study questions and answers), and optional writing preferences, then start automatic notes. Changing these preferences requests a new revision; the previous revision stays available until replacement succeeds. Once chosen, a background worker generates notes when saved transcription finishes and refreshes them after transcript corrections. Closing the page does not cancel generation. Pause automatic notes to stop future publication; existing notes remain readable. Speech transcription must currently be requested in its transcript panel; live processing comes in M05.

The notes panel precedes the transcript. It renders topic blocks, evidence labels, code/equation text, unresolved information, and source links opening the exact transcript version with original audio. Markdown export uses a saved revision and includes a portable source appendix. The model has no application tools. Generated text is escaped in both UI and export.

## Runtime and persistence

- Start Ollama with an installed supported model. The initial adapter supports local Qwen2/Qwen3 GGUF completion models with at least a 32,768-token context. This host has `qwen3:4b` and `qwen2.5:14b`; exposing a model in the selector does not establish its educational quality. Cloud aliases and other tokenizer families are excluded. There is no automatic download or provider fallback.
- `scripts/Start-App.ps1 -WithSpeech` now starts the notes worker with the app profile. Existing private database/audio volumes are preserved. An unavailable Ollama service does not block capture, transcript inspection or saved notes.
- Additive migration 0005 adds immutable writing-preference instructions to settings snapshots; 0004 stores immutable model preferences, pinned generation requests and note revisions. The generation identity includes source snapshot, settings version, model digest, base note revision and lifecycle/audio epochs. Successful revisions retain prompt/schema/input hashes, provider settings, preflight token count, inference metrics and resolved Unicode citation offsets.
- One note job is claimed globally per local workspace. A 60-second lease renews every 10 seconds. Expired attempts can be reclaimed after process exit; old attempts cannot publish. New transcript/model inputs invalidate older jobs. Provider unavailability retries up to three attempts at 60-second intervals; invalid/truncated output requires an explicit retry. No invalid output replaces the last valid revision.
- The notes worker uses PostgreSQL due-job reconciliation every three seconds; Kafka is not required for this increment. `notes.requested` outbox records are persisted for later notification integration. It does not claim the M05 replay stream or a complete shared speech/note resource scheduler.
- The local provider endpoint is restricted to loopback or Docker Desktop's host gateway. HTTP redirects and environment proxies are disabled. Model identities are checked before and after inference. Secret provider credentials are not part of the current UI or database schema.

## Input limits and remaining work

The first increment sends the complete selected transcript snapshot in one request. It includes the entire prompt/schema, reserves 6,000 output tokens, applies a conservative UTF-8 byte bound for the supported Qwen byte-level tokenizers including template and special-token headroom, then obtains the model's actual prompt count with a one-output-token preflight. Oversized input is rejected intact; it is never silently truncated or summarized to fit. Output must finish normally and pass the provider draft schema. The app resolves request-local source labels to original immutable transcript excerpts, creates block/passage IDs, and computes coverage from actual citations. It then enforces the unchanged canonical Phase 4 schema, coverage, citation and settings checks. Unknown source labels still fail; omitted material is honestly listed for review. Long individual source passages are split into exact bounded excerpts with server-computed occurrence positions.

**Long lectures are not supported by this first note-generation increment.** Topic segmentation with shared definitions and correction context remains the next M04 implementation task. Inputs above the byte/context bound or 200 source passages display a capacity message and retain the full transcript and previous notes. Code and equations are readable plain text. Basic writing preferences are implemented early at the user’s request; mathematical typesetting, interactive note editing, cross-topic reconciliation and full-lecture quality remain outstanding. Do not call M04 complete until these limits and its human review gates are addressed.

The earlier v2/v3 provider prompts asked a small model to reproduce citation quotes, identity and coverage bookkeeping; both exposed coverage mismatches, and the app repeatedly rejected the saved synthetic lecture. The repaired draft adapter asks the LLM for contextual prose and supporting source labels, while the app handles bookkeeping deterministically. Explicit writing instructions are applied after the transcript in the request. Canonical validation is unchanged. Structural source validity cannot prove semantic support or educational usefulness; every generated result says human review is pending.

## Reproduce verification

From the repository root with `PYTHONPATH=apps/api` and the local Python environment installed:

```text
python -m notetaker.verify_notes --model qwen3:4b --report .local/note-evaluation.json
```

Add `--dataset universal` to evaluate biology and history with Cornell/brief-question preferences. The verifier uses only committed synthetic text fixtures, never microphones or user lecture files. It records every result, including rejected ones. Backend service checks use `scripts/Test-Services.ps1`; frontend/contract checks use `npm test`, `npm run typecheck`, production builds and browser inspection. A database development checkpoint was saved at `.local/notetaker-before-m04.dump` before applying migration 0004; it is not a qualified coordinated audio/database restore.

Executed verification:

- 102 backend tests passed against PostgreSQL, plus real audio-storage and Kafka probes. The final 32 note-focused tests also passed after the display/profile refinements. Two existing upstream test-client deprecation warnings remain.
- 60 JavaScript tests, frontend type checks and production Docker builds passed. The deployed database reported no missing migration operations.
- The repaired draft adapter passed all three CS fixtures. Biology and history both generated notes. Initial style trials ignored the requested presentation; after explicit per-request style instructions, biology produced Cornell question cues and history produced three brief questions with answers. These are synthetic model trials, not independent human qualification.
- The failing saved synthetic lecture now has actual Qwen3-generated revisions 1 and 2. Revision 2 combines adjacent transcript evidence into coherent explanations after applying saved writing preferences. Authenticated HTTP checks verified its Markdown export and all 14 cited audio excerpts against their original frame counts. Browser checks verified saved notes, source selection, playable audio (1.52-second first excerpt, no media error), and the export link.
- No microphone was accessed. The old failed fixture outputs are retained alongside the successful reports, not hidden.

See [verification reports](../../evaluations/reports/phase-6-m04/README.md). Student-quality limits remain: the model can omit important detail or only partially follow free-form instructions. In the live revision, constant auxiliary space was omitted and the requested numbered presentation was not followed; the notes are useful pipeline evidence, not a passing full study-quality assessment. The next work is long-lecture topic processing, stronger detail preservation and human review. Representative real lectures, independent human note review, sustained local performance and Windows installer qualification remain open.

## Windows application

The [desktop direction](../architecture/windows-desktop-direction.md) proposes an early Electron host experiment using the current UI/services; M08 retains full installation and upgrade qualification. No Windows installer has been built yet.

## Later OpenAI and Claude connections

User requirement added on 2026-09-07: support the user's chosen OpenAI/ChatGPT and Claude models later. Keep local automatic notes first; implement optional provider connections in Phase 7 without making them a core release dependency.

Use supported provider APIs and user-supplied provider credentials. The current documentation describes API authentication for [OpenAI](https://developers.openai.com/api/reference/overview#authentication) and [Claude](https://platform.claude.com/docs/en/manage-claude/authentication). A consumer subscription or browser login must not be assumed to authorize arbitrary third-party API use. Recheck available official account-connection mechanisms when implementing this feature; do not collect account passwords, scrape sessions or repurpose another app's credentials.

Before that feature ships: Windows-protected credential storage outside browser storage/database exports; explicit choice of what lecture content is sent to which provider; model availability and provider billing explanations; revocation/disconnection; bounded retries and cost controls; the same source validation and stale-result protection as local notes. Cloud outages must preserve the last notes and never silently change the selected provider.

Related: [phase plan](../project-phases.md), [implementation roadmap](phase-5-roadmap.md), [transcription evidence](phase-6-m03.md), [AI contracts](../ai/phase-4-pipeline.md).
