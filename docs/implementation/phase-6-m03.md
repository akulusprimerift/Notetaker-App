# Phase 6.3 / M03: Local transcription and source inspection

Date: 2026-09-07. Status: implemented and verified with synthetic speech, real services and browser walkthroughs. Representative recorded lectures, human accuracy review and full device qualification remain open. No microphone was used.

## Student result

Stop a recording and wait for all declared audio in that segment to be saved. The local speech worker processes it, and timestamped passages appear in **Lecture transcript**. Each passage can play its original audio, including audio spanning multiple upload chunks. **Correct passage** saves a new student revision; **View history** retains the original recognition and subsequent corrections. Earlier transcript snapshots keep their original membership and text.

Progress distinguishes queued, processing, processed and needs-attention states. A missing local model leaves work pending. Noise with no recognized speech remains uncertain; only digital silence is asserted as silence. Scores are uncalibrated model outputs, never an accuracy percentage. Recording gaps remain explicit. **Processed** does not mean human-verified or complete lecture coverage.

This milestone processes complete, sealed recording segments. Missing declared audio waits for recovery; it is not replaced with silence. Continuous live transcription belongs to M05. Detailed study-note generation belongs to M04 and is not implemented yet. The current browser UI is the development preview; an installable Windows app is required in M08.

## Implementation and boundaries

- [Migration 0003](../../apps/api/migrations/versions/0003_versioned_transcription.py) adds speech windows, generation metadata, logical transcript segments, immutable text versions, snapshots and ordered snapshot membership, plus job attempt counts. Composite foreign keys constrain evidence to its lecture. Existing migrations remain unchanged; destructive downgrade is refused.
- [Worker](../../apps/api/notetaker/speech_worker.py): one local CPU speech process, one active inference per lecture, 60-second claims and ten-second renewals. Every publication rechecks the attempt, lease, lecture/audio epochs and manifest revision. Kafka hints and database reconciliation use the same claim function. The outbox sends references only; the inbox validates against the stored event and tolerates duplicate delivery. Temporary failures back off; unavailable models wait for provisioning; invalid output fails visibly. Original audio jobs complete only when the run's current speech windows complete.
- Window planning reads verified audio outside database locks. It looks for at least 200 ms of near-silence within two seconds of a nominal 24-second boundary and chooses the pause center. Cores stay at most 26 seconds; two-second context on each side stays at most 30 seconds. Context never crosses a declared gap. Word midpoints assign overlapping context to one core, without deleting repeated text by string matching. Forced seams through speech remain reviewable uncertainty. This reduces boundary errors; it does not guarantee perfect alignment for arbitrary speech.
- [Speech adapter](../../apps/api/notetaker/speech_provider.py): faster-whisper 1.2.1, CTranslate2 4.8.2, local `small.en`, English, CPU/int8, four threads, beam size five, word timestamps and VAD. Provisioning is separate. Inference loads only local files and never downloads or falls back to an external provider. Model digest and inference settings accompany each published generation.
- [Transcript API](../../apps/api/notetaker/transcription.py): authenticated transcript/snapshot/source/history reads, bounded reconstructed WAV playback, post-read authentication/audio-epoch checks, idempotent corrections and expected-version conflicts. Human corrections stay protected when subsequent speech windows finish; retries do not overwrite published text. New transcript snapshots provide the version boundary for M04's future note dependencies.
- [Transcript UI](../../apps/web/app/transcript.tsx): separate processing status, source playback, corrections and history. Correction drafts use owner/lecture-scoped **tab session storage**, so another tab cannot clear a draft and reload can recover it. A closed tab is not a durable cross-device draft store; full draft management belongs to M06. Polling does not replace the draft. Conflicts show the newer saved passage and require an explicit comparison-base update. Unsafe navigation is blocked while editing; expired sessions return to unlock.

The speech worker's optional Compose profile reuses the existing API, PostgreSQL, private SeaweedFS and Kafka. No extra database, vector service, cloud provider or separate API implementation was added. More than one speech process across lectures has not been memory-qualified; use the supplied single-worker configuration.

## Start locally

After the M01 environment setup, provision the pinned model once, then start the speech-enabled app:

```powershell
pwsh -File scripts/Provision-Speech.ps1
pwsh -File scripts/Start-App.ps1 -WithSpeech
```

Provisioning downloads the pinned model revision `d1d751a5f8271d482d14ca55d9e2deeebbae577f` into ignored project storage. Model weights are not committed. The model binary SHA-256 is `62b2a45b05ee59acb4a5341b33ee35e041395d378d418a18acfe4c9e768ee37a`. The separate [speech dependency lock](../../apps/api/requirements-speech.lock) pins dependencies and hashes; the API image keeps its existing lighter dependency set.

Open `http://127.0.0.1:3000`. Add `-NewUnlockCode` if the session expired. Omitting `-WithSpeech` permits recording without starting a new speech worker; it does not stop one already running. The worker is an optional development service, not a Windows installer.

Reproduce a synthetic test with Windows' installed speech voice:

```powershell
pwsh -File scripts/New-SyntheticSpeech.ps1
docker compose --env-file .local/services.env --profile app exec -T api python -m notetaker.verify_speech --audio .local/synthetic-cs.wav --reference .local/synthetic-cs.wav.txt --report .local/speech-check.json
```

The [probe](../../apps/api/notetaker/verify_speech.py) creates clearly named synthetic course/lecture records, uploads and seals actual WAV chunks, waits for the independently running model worker, and verifies every returned passage's source WAV length/rate. It revokes its temporary session afterwards. Test lectures are retained for inspection; no user lecture is deleted. [The reference](../../evaluations/fixtures/speech-cs-synthetic.txt) is assistant-authored CS material, not an independently annotated lecture.

Before migration, a local database dump and 96 audio objects (18,121,344 bytes) were copied to `.local/before-m03`, with an object/hash manifest. This is a development checkpoint, not a qualified automated backup/restore product.

## Executed evidence

| Check | Result |
| --- | --- |
| Backend suite | 70 tests passed against PostgreSQL: 44 prior workspace/capture checks and 26 transcription checks. Includes concurrent claims, stale attempts, epoch/source changes during inference, invalid output, missing models, corruption, duplicate events, ownership, immutable snapshots, correction conflicts and revoked-session playback. Two upstream test-client deprecation warnings remain. |
| Process termination | A separate process acquired an isolated synthetic job and was terminated. After accelerating its lease expiry in the test database, another attempt reclaimed and published it. This tests process loss and fencing, not a measured 60-second recovery deadline. |
| Normal synthetic CS speech | [Report](../../evaluations/reports/phase-6-m03/normal.json): 68.04 seconds, 158 reference words, zero normalized word edits, 17 playable passages; 24.70 seconds from sealing through completion and source checks. |
| Rapid synthetic CS speech | [Report](../../evaluations/reports/phase-6-m03/rapid.json): 47.05 seconds, the same 158 words, zero normalized word edits, 15 playable passages; 10.48 seconds after sealing. |
| Silence and noise | [Six seconds of digital silence](../../evaluations/reports/phase-6-m03/silence.json) produced no words and no speech issue. [Six seconds of seeded noise](../../evaluations/reports/phase-6-m03/noise.json) produced no words and an explicit uncertain-speech interval. |
| Real Kafka outage | [Report](../../evaluations/reports/phase-6-m03/broker-outage.json): Kafka was stopped, then 47.05 seconds of newly uploaded synthetic speech completed through database reconciliation with zero normalized word edits and 15 verified source passages in 18.69 seconds. Kafka was restarted afterwards. |
| Browser | Saved-audio playback reached media ready state 4 with no error. A correction created revision 2 while revision 1 remained in history. Two tabs editing the same passage showed a conflict after one saved; the second draft survived polling and reload, and its stale save remained disabled. |
| Frontend and builds | TypeScript checks and 60 JavaScript architecture/AI/capture tests passed. API, speech-worker and frontend production Docker builds passed. |

The first actual-model attempt exposed a numeric-scalar conversion defect; the adapter now converts provider scalars before strict validation and a regression test covers it. A subsequent [pre-boundary-fix run](../../evaluations/reports/phase-6-m03/before-boundary-fix.json) repeated one word across a context seam (1/158 normalized word edits). Moving cuts to pause centers removed that duplicate in the final normal and rapid fixtures. Prior source revisions were retained; they were not rewritten to hide failed runs.

Word-error normalization lowercases words and ignores punctuation. These short, clean, generated recordings cannot establish real classroom accuracy, correct technical meaning in general, or calibrated timestamp error. The baseline includes negation, sorted-input requirements, loop invariants, complexity, empty arrays and repeated values. Text inspection found those reference statements preserved in the final fixtures; no human subject review is claimed.

CPU environment: Windows host Intel i7-13700H with 20 logical processors; speech ran in the local Linux Docker container with four CPU threads. Durations above are individual runs, not p95 latency, controlled cold/warm benchmarks, or simultaneous speech/note performance. Peak RAM/VRAM and full-lecture endurance remain unqualified.

## Remaining qualification and next phase

M03 is implemented with synthetic engineering evidence; its full exit remains open under the user's synthetic-only preference. Actual microphone recordings, accents/classroom noise, human term/meaning review and calibrated timestamps are still required by G01/G02. Gap handling, continuous speech without pauses, realistic rapid code identifiers and full lectures need broader fixtures. This is not a release-ready accuracy claim.

Next implementation: M04 detailed, source-linked notes from saved transcript snapshots. Keep M02/M03 qualification work visible as it proceeds. M08 now also requires an installable Windows desktop host, service lifecycle and clean-machine/upgrade checks; the desktop runtime is not yet selected or built. See the [phase plan](../project-phases.md) and [release gates](phase-5-roadmap.md).

Provider reference: [faster-whisper 1.2.1 source](https://github.com/SYSTRAN/faster-whisper/tree/v1.2.1). Actual installed adapter behavior and the reports above are the implementation evidence.
