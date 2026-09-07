# Phase 6.4 / M04: Automatic study notes

Date: 2026-09-07. Status: implementation and verification in progress. This first increment implements notes from a bounded saved transcript; it does not close the full M04 qualification gates.

## Product direction

The selected LLM writes the student's notes from lecture context. Students do not have to draft notes themselves. Transcript corrections improve the evidence; manual note editing is an optional later review workflow in M06. Detailed notes remain the primary product, especially for algorithms, code, reasoning and content-heavy courses.

Choose **Local model → Start automatic notes** in a lecture. Once chosen, a background worker generates notes when saved transcription finishes and refreshes them after transcript corrections. Closing the page does not cancel generation. Pause automatic notes to stop future publication; existing notes remain readable. Speech transcription must currently be requested in its transcript panel; live processing comes in M05.

The notes panel precedes the transcript. It renders topic blocks, evidence labels, code/equation text, unresolved information, and source links opening the exact transcript version with original audio. Markdown export uses a saved revision and includes a portable source appendix. The model has no application tools. Generated text is escaped in both UI and export.

## Runtime and persistence

- Start Ollama with an installed supported model. The initial adapter supports local Qwen2/Qwen3 GGUF completion models with at least a 32,768-token context. This host has `qwen3:4b` and `qwen2.5:14b`; exposing a model in the selector does not establish its educational quality. Cloud aliases and other tokenizer families are excluded. There is no automatic download or provider fallback.
- `scripts/Start-App.ps1 -WithSpeech` now starts the notes worker with the app profile. Existing private database/audio volumes are preserved. An unavailable Ollama service does not block capture, transcript inspection or saved notes.
- Additive migration 0004 stores immutable model preferences, pinned generation requests and note revisions. The generation identity includes source snapshot, settings version, model digest, base note revision and lifecycle/audio epochs. Successful revisions retain prompt/schema/input hashes, provider settings, preflight token count, inference metrics and resolved Unicode citation offsets.
- One note job is claimed globally per local workspace. A 60-second lease renews every 10 seconds. Expired attempts can be reclaimed after process exit; old attempts cannot publish. New transcript/model inputs invalidate older jobs. Provider unavailability retries up to three attempts at 60-second intervals; invalid/truncated output requires an explicit retry. No invalid output replaces the last valid revision.
- The notes worker uses PostgreSQL due-job reconciliation every three seconds; Kafka is not required for this increment. `notes.requested` outbox records are persisted for later notification integration. It does not claim the M05 replay stream or a complete shared speech/note resource scheduler.
- The local provider endpoint is restricted to loopback or Docker Desktop's host gateway. HTTP redirects and environment proxies are disabled. Model identities are checked before and after inference. Secret provider credentials are not part of the current UI or database schema.

## Input limits and remaining work

The first increment sends the complete selected transcript snapshot in one request. It includes the entire prompt/schema, reserves 6,000 output tokens, applies a conservative UTF-8 byte bound for the supported Qwen byte-level tokenizers including template and special-token headroom, then obtains the model's actual prompt count with a one-output-token preflight. Oversized input is rejected intact; it is never silently truncated or summarized to fit. Output must finish normally and pass the canonical Phase 4 schema, coverage, citation and settings checks on the server.

**Long lectures are not supported by this first note-generation increment.** Topic segmentation with shared definitions and correction context remains the next M04 implementation task. Inputs above the byte/context bound or 200 source passages display a capacity message and retain the full transcript and previous notes. Code and equations are readable plain text; mathematical typesetting, interactive note editing, cross-topic reconciliation and full-lecture quality remain outstanding. Do not call M04 complete until these limits and its human review gates are addressed.

Prompt v3 adds explicit coverage treatment for uncertainty passages and tighter source-only wording after a v2 fixture failure. Canonical validation is unchanged. Structural source validity cannot prove semantic support or educational usefulness; every generated result says human review is pending.

## Reproduce verification

From the repository root with `PYTHONPATH=apps/api` and the local Python environment installed:

```text
python -m notetaker.verify_notes --model qwen3:4b --report .local/note-evaluation.json
```

This uses only the three committed synthetic CS text fixtures, never microphones or user lecture files. It records every result, including rejected ones. Backend service checks use `scripts/Test-Services.ps1`; frontend/contract checks use `npm test`, `npm run typecheck`, production builds and browser inspection. A database development checkpoint was saved at `.local/notetaker-before-m04.dump` before applying migration 0004; it is not a qualified coordinated audio/database restore.

Final results are recorded here after execution. Representative real lectures, independent human note review, sustained local performance and Windows installer qualification remain open.

## Later OpenAI and Claude connections

User requirement added on 2026-09-07: support the user's chosen OpenAI/ChatGPT and Claude models later. Keep local automatic notes first; implement optional provider connections in Phase 7 without making them a core release dependency.

Use supported provider APIs and user-supplied provider credentials. The current documentation describes API authentication for [OpenAI](https://developers.openai.com/api/reference/overview#authentication) and [Claude](https://platform.claude.com/docs/en/manage-claude/authentication). A consumer subscription or browser login must not be assumed to authorize arbitrary third-party API use. Recheck available official account-connection mechanisms when implementing this feature; do not collect account passwords, scrape sessions or repurpose another app's credentials.

Before that feature ships: Windows-protected credential storage outside browser storage/database exports; explicit choice of what lecture content is sent to which provider; model availability and provider billing explanations; revocation/disconnection; bounded retries and cost controls; the same source validation and stale-result protection as local notes. Cloud outages must preserve the last notes and never silently change the selected provider.

Related: [phase plan](../project-phases.md), [implementation roadmap](phase-5-roadmap.md), [transcription evidence](phase-6-m03.md), [AI contracts](../ai/phase-4-pipeline.md).
