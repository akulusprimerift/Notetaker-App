# Phase 6 / M02: Recording and audio recovery

Date: 2026-09-07. Status: implemented with synthetic browser/service verification. Real microphone and full device-failure qualification remain open. The user requested synthetic audio only; no microphone permission was granted and no personal audio was recorded.

## Student workflow

Open a lecture, select **Start recording**, and allow the microphone when you choose to use it. The app checks its storage connection, browser recovery storage and one-hour buffer headroom before starting the capture graph. It shows recording separately from confirmed saves. **Stop recording** stops the microphone first, preserves the final partial audio chunk, then uploads remaining audio and closes its manifest.

A connection failure leaves unconfirmed audio in the browser. Reopen the same browser profile and lecture, then choose **Recover segment**. An unsealed interruption retains an explicit unknown gap. A normal offline stop can recover without inventing a crash. A separate recording segment has its own sample clock and boundary; the app does not claim a continuous timeline across interruptions.

Another tab cannot acquire the same lecture's recording lock. Explicit takeover on another browser/device advances server ownership; the old owner stops when it learns of the change. Its buffered audio needs recovery. The app cannot remotely stop an offline microphone on a different device.

Saved audio excerpts can be played in the lecture workspace. This first playback control exposes short saved intervals; continuous lecture playback and transcript navigation belong to M03. Transcription and generated notes are **not implemented**. Verified audio creates pending speech jobs, with no placeholder transcription or model output.

## Implementation

- [Recording interface](../../apps/web/app/recording.tsx), [controller](../../apps/web/public/capture/recorder.mjs), [AudioWorklet](../../apps/web/public/capture/worklet.js), [worker](../../apps/web/public/capture/worker.mjs), and [PCM encoder](../../apps/web/public/capture/pcm.mjs): mono PCM16 WAV at the actual AudioContext sample rate, nominal two-second chunks, flushed tail and no microphone monitoring through speakers.
- [IndexedDB journal](../../apps/web/public/capture/journal.mjs): owner-scoped run identity, blobs and sample manifest written in a strict transaction. Success means transaction completion. A matching verified acknowledgement releases only the corresponding blob and retains its metadata/receipt. Pending reads load one chunk at a time. Browser persistence is requested and its actual outcome is displayed.
- Limits: 1 GiB pending journal across locally known runs, 8 MiB worklet backlog, 8 MiB maximum upload, one-hour admission estimate with 25% overhead. At 48 kHz, that admission estimate is 432,000,000 bytes. Storage-write failure stops capture; bounded chunks already delivered to the controller remain available as emergency WAV downloads if the journal cannot retain them. That fallback requires saving the downloads before leaving the page.
- [Capture API](../../apps/api/notetaker/capture.py) and [private audio store](../../apps/api/notetaker/audio_store.py): authorization/origin/CSRF, client-persisted admission identity, hashed 45-second grants with same-owner renewal, explicit takeover, immutable reservations, canonical WAV/hash/length validation, object readback and post-transfer ownership/deletion checks. Objects are never exposed through public URLs.
- The acknowledgement transaction inserts a verified chunk, logical speech job, outbox and lecture update together. Failed transfer/readback leaves its reservation for retry and later deletion inventory. A lost response retries the same immutable identity. Conflicting bytes, overlaps and noncontiguous adjacent chunks are rejected. Saved-through stops at the first missing range.
- [Migration 0002](../../apps/api/migrations/versions/0002_reliable_capture.py) adds capture runs, reservations, verified chunks and immutable manifest revisions. Sealing and subsequent late recovery preserve revision membership. Ordinary live chunk saves advance a manifest counter; they do not copy an entire manifest into JSON every two seconds. Playback uses `/lectures/{id}/audio-chunks/{chunk_id}` with current authorization and object validation.
- Recording status considers every segment: a completed new segment cannot conceal an older pending segment. An audio-complete manifest can still contain an explicitly reported unknown interruption. M07 must check those issues separately before finalization.

The SQLite preview does not enable recording. PostgreSQL and private SeaweedFS storage are the application path. Kafka/model outages do not control durable audio acknowledgement; actual speech dispatch and job execution are M03 work. Deletion write fences are present, but full deletion/cleanup workflows remain M07 work.

## Run and verify

Use the existing [local launcher](../../scripts/Start-App.ps1):

```powershell
pwsh -File scripts/Start-App.ps1
# Add -NewUnlockCode only when a new browser session is needed.
```

Open `http://127.0.0.1:3000`. The launcher rebuilds changed code; omit `-NoBuild` after an update. A pre-M02 database snapshot exists locally at `.local/notetaker-before-m02.dump`; it predates the new audio and is not a backup of recordings. Existing courses and the separate SQLite preview were preserved.

Developer checks:

```powershell
npm test
npm run typecheck
pwsh -File scripts/Test-Services.ps1
pwsh -File scripts/Test-Services.ps1 -Restart
```

The restart option deliberately restarts PostgreSQL, SeaweedFS and Kafka. Use it when no wanted recording is active. It creates its own synthetic course/schema, WAV/object bucket and broker topic, verifies acknowledged audio and the sealed manifest after restart, then removes only its generated resources.

The [development verification page](../../apps/web/app/capture-check/check.tsx) at `/capture-check` provides generated-tone recording, isolated real IndexedDB checks and explicit failure switches. Run the frontend in development against the configured API on port 8010; stop the web container first so port 3000 remains available. The page returns not-found in the production build. Its connection switches affect only its recorder, never system networking. No microphone is requested. The sample course is named **Capture checks (synthetic)** and its lecture **Generated tone — no microphone**.

## Executed evidence

| Check | Observed result |
| --- | --- |
| PostgreSQL application tests | 44 passed, including 20 capture checks in addition to the 24 foundation checks. Tests cover readback failure, immutable retry/conflict, out-of-order/missing audio, invalid WAV/hash/size, adjacency, explicit ownership, expired grants, stale seals, recovery, concurrent duplicate uploads, deletion/takeover during transfer, authorization, schema agreement and multi-segment status. Two upstream test-client deprecation warnings remain visible. |
| JavaScript tests | 60 passed: the existing 52 architecture/AI checks plus eight capture checks. PCM rate/header/count/clipping, full identity acknowledgement matching, admission arithmetic, arbitrary block sizes/tail flushing, bounded worklet backpressure and the default browser transport binding are covered. |
| Browser journal | Six real IndexedDB checks passed: close/reopen persistence, mismatched ACK retention, matching ACK release, atomic capacity rejection, transaction-abort retention and owner-scoped listing. |
| Lost upload response | Injected one lost response after the server completed its upload. The browser retried and reached zero pending bytes without duplicating the saved chunk/job. |
| Offline stop and recovery | A generated-tone recording continued during simulated connection loss. Stopping left 3,249,388 bytes in the browser; a second tab recovered all 3,352,320 captured samples and reached a complete sealed manifest with zero pending bytes. An early test exposed overly conservative crash labeling for normal offline stops; the backend now distinguishes normal stop from abrupt interruption and has a regression test. |
| Two tabs | The second tab's start was refused while the first held the lecture lock. Recovery succeeded after the first stopped. |
| Simulated permission denial | The synthetic stream factory rejected with the browser's permission-denial error type. A readable error appeared, no new recording was admitted, and retry started the generated tone. This does not test an actual browser permission prompt. |
| Abrupt exit and reload | Fault injection terminated a generated-tone recorder without sealing, then the page was actually reloaded. The journal retained 2,880,660 pending bytes and 3,648,000 sample positions. Explicit recovery saved all declared samples, sealed the manifest, emptied the pending buffer and preserved the unknown crash gap. This is a simulated recorder exit, not a Windows power-loss test. |
| Simulated suspension stop | The stop handler flushed a partial tail, saved all 1,668,480 samples, sealed the third segment and retained its sleep/suspension issue. No actual Windows sleep or microphone interruption was induced. |
| Browser-generated jobs | After the three synthetic segments, PostgreSQL contained 91 verified chunks, 91 speech jobs and 91 matching audio outbox records for the test lecture. All browser buffers were empty. Jobs remain pending for the unimplemented speech worker. |
| Real storage restart | A synthetic canonical WAV passed through the capture API, received a verified ACK and sealed manifest, then remained byte-identical and readable after the three real service containers restarted. Ordinary object and Kafka record checks also passed. |
| Builds and UI | TypeScript checking and both production Docker builds passed. The normal student page showed recovered audio and enabled recording; a fetch-binding startup bug found there was fixed. The UI continues to state that notes/transcription are unavailable. |

## Remaining qualification

M02's full exit remains open. The implementation is ready for further testing; these checks do not establish production reliability for real lectures:

- Actual microphone permission denial/retry, device removal/mute behavior, hardware sample rate and playable recorded speech. The user explicitly deferred microphone access.
- Real Windows sleep/resume, browser/process crash, disk pressure and browser storage eviction. The current suite uses controlled failures and checks transaction/backlog bounds; emergency-download behavior still needs a full browser failure drill.
- A 45–60 minute recording, sustained IndexedDB/upload load, full accessibility/assistive-technology review and simultaneous model workloads. No endurance or live transcription performance claim is made.
- Full transcript playback, deletion reconciliation, finalization and backup/restore qualification in their assigned milestones. The current single-machine volumes are not host-loss redundancy.

Implementation references: [AudioWorkletProcessor](https://developer.mozilla.org/en-US/docs/Web/API/AudioWorkletProcessor), [IndexedDB transaction durability](https://developer.mozilla.org/en-US/docs/Web/API/IDBDatabase/transaction), and [Web Locks](https://developer.mozilla.org/en-US/docs/Web/API/Web_Locks_API). The release gates remain in the [roadmap](phase-5-roadmap.md).
