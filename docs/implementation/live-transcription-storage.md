# Live transcription and audio storage repair

Active phase: **6.8 / M08**, priority repair requested on 2026-09-30 before macOS work resumes. macOS 6.9.3 stays paused.

## Problem and root cause

Recording saved audio but never transcribed it. The installed library's SeaweedFS log showed every chunk upload refused with "No writable volumes and no free volumes left". The bundled `weed server` used its default `-volume.max=8`: seven system volumes plus one full 256 MB `notetaker-audio` volume left no writable slot. Uploads failed, audio stayed in the browser journal, and no speech jobs were created. The speech worker itself was ready.

Storage also grew quickly: capture used the device rate (typically 48 kHz, 96 KB/s of PCM), and every chunk was kept indefinitely.

## Changes

- **Storage cap:** standalone and Docker SeaweedFS start with `-volume.max=0`, which sizes the volume count from free disk space. The existing 1% free-space reserve is unchanged.
- **Capture rate:** the recorder captures at 16 kHz (`AudioContext({sampleRate:16000})`), the rate speech models decode at. Chromium resamples the device stream. This stores one third of the bytes at 48 kHz devices.
- **Faster live passages:** live speech cores are 4 seconds (previously 6) with the same 2-second context, so the first passage can appear after 6 seconds of saved audio instead of 8.
- **Audio retention:** each lecture has **Keep lecture audio after transcription** in Capture. New lectures default to off; lectures that existed before migration 0018 keep their audio. When off, after each live passage publishes, the speech worker advances a per-run `released_through` frontier to the end of the contiguous completed live cores. Chunks ending at least 2 seconds (one context length) before it are deleted; the frontier commits before deletion so reads never meet a missing object. Live passages ending at the frontier stay valid, and a gap declared inside released audio is refused (`gap_released`), so released audio is never needed again. A sealed run's short tail, transcribed with saved-audio windows, stays until finalization or removal.
- **Finalize choice:** finalizing offers **Keep all remaining audio** or **Delete all audio once the final snapshot is saved**. It defaults to the lecture's retention setting. Deletion reuses the existing audio-removal inventory and reconciliation after the snapshot is written; transcript, notes and revisions stay.
- Playback of released audio returns `410 audio_released`; Capture shows how much transcribed audio was deleted and only offers retained chunks.

Migration **0018** adds `lectures.keep_audio` (existing rows true), `capture_runs.released_through` and `finalizations.discard_audio`. It is additive; existing student data is not changed.

## Executed evidence (Windows, 2026-09-30)

- Actual bundled SeaweedFS 4.47 in a temporary directory with 1 MB volumes and synthetic 192 KB objects: default flags **failed after 48 objects**; `-volume.max=0` **stored all 80**.
- Backend: full suite **266 passed, 2 existing skips** (one live-latency expectation updated for 4-second cores and rerun). New `test_audio_retention.py`: live release behind context, keep-audio retention, CSRF and released-gap refusal, finalize-and-delete with reconciliation, default keep, and upgrade preservation from 0017.
- **63 JavaScript contracts**, **39 desktop tests**, Python lint, frontend typecheck/lint/production build, whitespace check.
- Real Chrome (installed browser, `NOTETAKER_CHROMIUM`): generated-tone AudioWorklet/worker/IndexedDB capture uploads 16 kHz chunks, plus offline/wake recovery and three stop/restart cycles. Production renderer with synthetic API: retention toggle, released-chunk filtering and finalize delete choice.

## Limits and next work

No physical microphone, real lecture, installed-app upgrade or packaged-runtime run was performed. The installed library's existing full volume becomes usable only after the updated host starts SeaweedFS with the new flag; audio still waiting in that browser's journal then uploads and is transcribed. SeaweedFS reclaims space from deleted objects through its own garbage vacuum, so disk usage falls after compaction rather than immediately. A failed object delete during release leaves an orphan until audio or lecture removal reconciles the prefix. Speech accuracy with 4-second cores on real lectures is unqualified.

## Cloud-processing confirmation — 2026-09-30

The Study notes confirmation for sending lecture content to a connected provider was component state, so it reset to unchecked and reappeared whenever the panel remounted (changing lecture sections, reopening the lecture, or resuming paused notes). Confirming now closes the prompt into "Cloud processing confirmed for *provider*" with a **Withdraw** action. The confirmation is remembered per provider on this device (`localStorage`, read defensively), and every note-preference request still sends `cloud_consent` explicitly; the server requirement is unchanged. Generated-question consent is a separate per-request prompt and is unchanged.

Executed: production renderer in real Chrome with synthetic API — confirm, start notes with `cloud_consent: true`, leave and return to Study notes, reload, then withdraw restores the prompt. Frontend typecheck/lint/production build, 63 JavaScript contracts and the retention UI check were rerun. No live provider call.
