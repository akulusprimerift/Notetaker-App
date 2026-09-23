# Windows live transcription repair — 2026-09-23

Active phase: **6.8 / M08 — Standalone Windows distribution**.

## Cause and changes

Read-only inspection of the installed desktop settings found an empty speech-model selection. The native host skipped launching its speech worker in that case, leaving verified audio without transcript passages and automatic notes without source evidence. The Transcript component also omitted the backend's fenced partial-recognition preview.

The host now always launches speech reconciliation. Missing models produce retryable, visible `model_unavailable` jobs. Authenticated lecture snapshots and transcript responses also disclose missing required model files before a job runs. The lecture-wide status and Transcript screen explain model selection and service restart; audio saving remains independent. Desktop model selection now requires `tokenizer.json` as well as `model.bin` and `config.json`, matching the speech adapter.

The Transcript screen displays partial recognition as a live draft, renders arbitrary text safely, and removes the preview once the worker publishes saved passages. Existing snapshot updates and polling refresh it without replacing student corrections. Existing note streaming and contextual batching remain unchanged; notes begin after sufficient transcript evidence and a selected note model are available. No migration or source/revision-history rewrite is required.

The user explicitly selected the existing `.local/models/faster-whisper-small.en` model for the installed app. Its desktop settings were updated while the app was closed, preserving the other settings and a local backup. No model download, microphone use, student-library write, provider fallback or push occurred.

## Executed verification

- Windows backend: **231 passed, 1 service-only skip**. Focused live/transcription checks: **45 passed**. The new regression covers missing-model disclosure, retained audio, retry, partial preview, and transcript-to-note publication while capture is still unsealed.
- **60 JavaScript contracts**, **15 desktop tests**, frontend typecheck/lint and Python lint passed.
- Production desktop web build and isolated bundle hash/hydration/capture-assets smoke passed. The bundle smoke used Node 26.3.0.
- Chromium with the actual React UI and synthetic responses passed missing-model guidance, safe partial-text rendering, transition to saved transcript passages, and note-stream display. No microphone was opened.
- Frozen service build succeeded. The frozen native host, real PostgreSQL/SeaweedFS, local faster-whisper `small.en` and Ollama `qwen3:4b` passed the unsealed-capture probe: **21 recognized passages and a validated saved note revision**, without stopping capture. Isolated profile: `.local/host-smoke-0b288acf88314ac6b73751619adc693c`.
- Packaged `win-unpacked/Notetaker.exe` passed fresh-library startup, the missing-model setup message, synthetic verified audio save, normal quit/reopen, course persistence, identical audio SHA-256 and renderer isolation. Profile: `.local/standalone-smoke-b44c5eff-62e6-4208-a8fe-54cbcc2abe23`. Documentation and whitespace checks passed.

The first focused test invocation lacked its temporary parent directory; creating that isolated directory and rerunning passed. The first frozen live probe could not save its first audio chunk: SeaweedFS reported disk free space below its 1% reserve while concurrent builds were running. It timed out before inference. The successful rerun used a fresh isolated library after space recovered. These runs do not establish hardware latency, microphone quality or release readiness.

## Reproduce the isolated live probe

`scripts/test-windows-host.py` accepts `--speech-model`, `--synthetic-audio` and `--note-model`. Supply existing local models and synthetic mono PCM16 WAV only. It starts an isolated native PostgreSQL/audio/worker library, uploads audio, and requires both recognized transcript passages and a saved note revision **before sealing capture**. Its normal cleanup stops the owned services and preserves the test profile for inspection. It does not open the student's library.

## Delivery

Unsigned installer: `.local/live-fix/installer/Notetaker-0.1.0-Windows-Standalone-Setup.exe`, **397,916,242 bytes**, SHA-256 `906C7C693F65A6D01D3DC8389359176F10A28085B3317FC4FE53607AE93AD1D9`. Build exited successfully. Packaged service SHA-256 matches the tested frozen executable; runtime inventory preserves verified vendor components and includes the new web bundle. The installer includes the earlier material-upload repair. Existing installed binaries were not replaced automatically.

Next user step: install this build and reopen Notetaker using the existing library. The approved speech-model selection is already saved. Choose a note model in each lecture's preferences if one is not already selected. Retained audio is reconciled automatically; previously failed jobs have a Retry transcription action.

Remaining qualification: installed upgrade, clean-machine setup, hardware/endurance, educational quality and the existing M08 release gates. Saved lectures remain available for transcription after the selected model is activated on next service startup; note writing also requires a per-lecture note-model selection.
