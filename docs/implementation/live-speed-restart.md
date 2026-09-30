# Live speed and stop/restart repair

Active phase: **6.8 / M08**, priority override on 2026-09-30. macOS 6.9.3 is paused.

## Speed increment

Live speech uses greedy beam 1 instead of beam 5, configurable with `NOTETAKER_SPEECH_LIVE_BEAM_SIZE` (1â€“5). Non-live saved windows retain beam 5. Live source identities remain immutable when capture seals; sealing does not re-decode them. Word timestamps, VAD, source coordinates and uncertainty checks remain. Real lecture accuracy needs qualification; set the override to 5 to retain the earlier search width.

Speech and note workers check idle queues every 0.5 seconds (previously 2 and 3 seconds). Local notes allocate context in 2,048-token steps against the existing conservative byte bound, plus output and reserve, rather than always reserving 32,768 tokens. The actual tokenizer probe still validates capacity before generation, using the same allocation. Detailed output remains 6,000 tokens; no input or source is silently truncated. Note preview decoding is coalesced to at most ten updates per second plus the terminal update, preserving the complete final response.

## Executed evidence

Windows, existing local faster-whisper small.en CPU/int8, four threads, fresh Windows SAPI synthetic fixture, first 10 seconds: alternating beam 5/1/5/1 took 3.517/2.787/3.096/2.729 seconds. Identical text on these four runs. The warm pair is about 12% faster. Cold-load time is excluded; this is not an end-to-end or human-quality claim. Local benchmark output: `.local/restart-speed-benchmark.json`.

Initial focused backend run: 71 passed; Python lint passed. Final context-allocation regression run: 44 passed; documentation and whitespace checks passed. Existing pytest deprecation/cache warnings remain.

## Next work and limits

Stop/restart repairs and shared checks now pass. Package and verify the Windows update. Installed application and installer are not yet updated. No student library, physical microphone, model download or external inference was used. Earlier release and macOS qualification gates remain open.

## Stop/restart increment

A deterministic recorder regression reproduced an in-flight upload returning its pre-stop journal snapshot after Stop had closed the journal. It overwrote the recorder’s current state, skipped sealing and left restart disabled. Stop now drains the prior upload before closing the run and performs a fresh synchronization to seal it. Periodic ticks do not enter setup/stop transitions. A new setup clears the old completed-run reference before requesting a stream, so failed setup cannot modify the previous run.

A backend regression reproduced immediate pause/resume leaving the earlier running job in the queue until its lease/heartbeat advanced. Applying preferences now cancels obsolete due/running jobs and clears previews transactionally before scheduling fresh work. Attempt/publication fences and the inference-slot lock remain; cancellation never permits simultaneous calls to the same model role. An already executing provider call unwinds at its next preview/fenced check or network timeout, rather than being force-killed. Resume is clearly labeled. Notes requests have a 20-second client timeout, retain idempotency identities for retries and release busy controls on errors.

Both regression tests failed before their fixes and pass afterward. Windows checks: 79 focused backend tests; full backend **260 passed, 2 existing environment-dependent skips**; **63 JavaScript contracts**, **39 desktop tests**; frontend typecheck/lint/production build, Python lint. Chromium generated-tone AudioWorklet/worker/IndexedDB test passed offline interruption/recovery, three successive stop/start cycles on the same recorder, and journal reopen. Production-renderer checks passed three note pause/resume cycles plus existing streamed text, automatic revisions, protected drafts and deletion. Standalone web manifest/hydration/capture assets passed. Existing pytest deprecation/cache warnings remain. Frozen service/installer and packaged startup checks passed; delivery follows.

## Windows installer delivered — 2026-09-30

Unsigned x64 installer: `.local/restart-speed/installer/Notetaker-0.1.0-Windows-Standalone-Setup.exe`, **407,285,900 bytes**, SHA-256 `F717209E63E766A8905AFBAAD245E3205E7FC4116BA8C3FB2D7BDFF5ECA437F6`. Source commits: `3743011` (speed), `7214afb` (restart). The installer is ready and has not been installed automatically. Close Notetaker normally before installing; retain the existing selected library.

Fresh frozen service built successfully; its executable hash matches the packaged service (`BB11A7E43558C1CCBE4478392644B5D9B8E5BF891353600F378254B2FCD7EDEE`). Web component `.local/desktop-web/2b25a857-774f-4838-98b5-48ad02eec862`, build ID `1WVSKboBFZyNvPBuOAzZv`. Runtime `.local/restart-speed/runtime` contains 6,480 inventoried files; all 1,806 reused vendor/notice files were verified before and after staging. The new service and web were copied separately. Electron-builder acquired/extracted the selected Electron 44.3.0 distribution; no model weights were downloaded or bundled.

Actual packaged Electron passed startup/PostgreSQL migrations, synthetic verified audio, **three recorder stop/restart cycles on the same recorder against the real API/storage**, Quit/automatic reopen with identical audio readback, renderer isolation, theme persistence, native window controls and snapshot exports. Isolated profile: `.local/standalone-smoke-f6eef723-9659-4367-a67b-ba6f29219e14`. Logs: `.local/restart-speed-packaged-smoke.log`, `.local/restart-speed-installer-build.log`.

Installed-upgrade and real-lecture quality/performance qualification remain open. The synthetic warm speech pair is a 12% decode improvement, not a guarantee for all lectures; no end-to-end local-note throughput benchmark was performed. No microphone, existing student library, cloud inference, automatic installation or push. macOS remains paused; next user delivery step is installing this update and retaining the existing library selection. Earlier signing, hardware, endurance, backup/restore and human-quality gates remain open.
