# Live speed and stop/restart repair

Active phase: **6.8 / M08**, priority override on 2026-09-30. macOS 6.9.3 is paused.

## Speed increment

Live speech uses greedy beam 1 instead of beam 5, configurable with `NOTETAKER_SPEECH_LIVE_BEAM_SIZE` (1–5). Non-live saved windows retain beam 5. Live source identities remain immutable when capture seals; sealing does not re-decode them. Word timestamps, VAD, source coordinates and uncertainty checks remain. Real lecture accuracy needs qualification; set the override to 5 to retain the earlier search width.

Speech and note workers check idle queues every 0.5 seconds (previously 2 and 3 seconds). Local notes allocate context in 2,048-token steps against the existing conservative byte bound, plus output and reserve, rather than always reserving 32,768 tokens. The actual tokenizer probe still validates capacity before generation, using the same allocation. Detailed output remains 6,000 tokens; no input or source is silently truncated. Note preview decoding is coalesced to at most ten updates per second plus the terminal update, preserving the complete final response.

## Executed evidence

Windows, existing local faster-whisper small.en CPU/int8, four threads, fresh Windows SAPI synthetic fixture, first 10 seconds: alternating beam 5/1/5/1 took 3.517/2.787/3.096/2.729 seconds. Identical text on these four runs. The warm pair is about 12% faster. Cold-load time is excluded; this is not an end-to-end or human-quality claim. Local benchmark output: `.local/restart-speed-benchmark.json`.

Initial focused backend run: 71 passed; Python lint passed. Final context-allocation regression run: 44 passed; documentation and whitespace checks passed. Existing pytest deprecation/cache warnings remain.

## Next work and limits

Repair recording journal/upload stop races and pause/resume note scheduling; run repeated synthetic restart and offline/recovery checks. Complete shared checks and package the Windows update. Installed application and installer are not yet updated. No student library, physical microphone, model download or external inference was used. Earlier release and macOS qualification gates remain open.
