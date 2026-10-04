# Phase 6.9.4 — Complete Mac lecture workflow

Active phase: **6.9.4**, started at the user's request on 2026-10-01. Earlier 6.9.1 containment, 6.9.2 native runtime and 6.9.3 native integration qualification remain open: no Mac app has been built yet. This increment delivers the workflow/performance qualification harness and a Windows reference baseline. It does **not** complete 6.9.4, which requires an installed Mac build.

## Workflow harness

`scripts/test-windows-host.py` (historical name; it runs both platforms) now selects `NotetakerService` or `NotetakerService.exe` and starts the frozen service host in a new `.local/host-smoke-*` profile. It never opens a student library, accesses a microphone, downloads models or calls providers. With `--synthetic-audio` it runs one lecture through:

1. Course/lecture creation, **Keep lecture audio** on, a Markdown syllabus material saved and listed.
2. Speech-worker readiness; a nonexistent note model is refused with `model_unavailable`; the selected local note model is saved.
3. Real-time paced 2-second verified chunk uploads with capture heartbeats (or `--fast` for no latency claim), then seal.
4. Timestamped passages and streamed note previews measured during capture, saved note revisions, settled transcript/notes.
5. Citations resolve to saved transcript passages or the material; source text and source audio load.
6. Protected student edit → changed detail prompt → valid regeneration proposal → edit retained → merge one section → undo to the edit.
7. Explicitly request flash cards with student instructions from the current selected saved note revision, inspect their pinned source quotes and save a self-assessment.
8. Student-revision Markdown/DOCX and generated-revision exports; finalization; final-snapshot Markdown retains the student edit; every saved chunk matches its SHA-256.

Omitting `--speech-model` runs the missing-speech-model path instead: status `missing`, audio verified and intact, `model_unavailable` visible, no invented passages. The report is written to `workflow-report.json` in the profile with platform, CPU, model names and timings.

## Windows reference baseline — 2026-10-01

Executed against the installed-equivalent standalone runtime `.local/audio-retention/runtime` (Windows 11, Intel 20 logical CPUs, CPU speech), `faster-whisper-small.en` and Ollama `qwen3:4b`. [Raw report](macos-workflow-windows-baseline.json).

| Measure (272 s synthetic CS lecture, paced) | Result |
| --- | --- |
| Service startup / speech ready | 23.5 s / 4.1 s |
| Chunk save p50 / max | 0.093 s / 0.421 s (137 verified) |
| First passage / first streamed note text / first saved notes | 9.5 s / 69.1 s / 94.3 s after capture start |
| Max speech backlog while notes generated | 52.2 s; 152 polls saw previews with speech still pending |
| Transcript complete after capture end | 89.9 s (103 passages) |
| Notes settled after capture end | 588.7 s (13 saved sections, 97 citations, 1 material citation) |
| Regeneration proposal after prompt change | 56.8 s |

All workflow checks passed, as did the missing-speech-model run (47 s audio, `--fast`). A 68 s paced run also passed all checks. The note model, not capture or speech, limits this machine: notes trail a 4.5-minute lecture by about 10 minutes, and concurrent note generation raises the speech backlog. These are synthetic Windows numbers for comparison only; they do not qualify Mac performance, real-lecture accuracy or note quality.

This baseline predates the Flash Cards change. Its `catch_up: true` workflow-report field records the earlier 2026-10-01 harness behavior and is historical, not a current capability.

Harness defects found and fixed during these runs: missing capture heartbeats (lease expired at chunk 22); a marker containing Markdown-escaped brackets (exports correctly escape them); transcript metrics read from the note stream, which omits transcript state on the PostgreSQL host, so they now come from `/transcript` as in the workspace. No product code changed.

## Run on the Apple Silicon Mac

After 6.9.2 produces a prepared runtime, generate equivalent synthetic speech with the built-in voice (no microphone):

```sh
say -f evaluations/fixtures/speech-cs-synthetic.txt -o .local/synthetic-cs.wav --file-format=WAVE --data-format=LEI16@22050
PYTHONPATH=apps/api uv run --no-project python scripts/test-windows-host.py /absolute/prepared-macos-runtime \
  --speech-model /absolute/faster-whisper-small.en --note-model qwen3:4b --synthetic-audio .local/synthetic-cs.wav
PYTHONPATH=apps/api uv run --no-project python scripts/test-windows-host.py /absolute/prepared-macos-runtime \
  --synthetic-audio .local/synthetic-cs.wav --fast
```

Use only existing local models; close any other Notetaker first (occupied ports are refused). Record macOS version, chip/memory and the report. Then repeat the packaged-app checks with `tests/desktop/native-smoke.cjs` (save/Quit/reopen, exports, themes) from the installed app location.

## Remaining 6.9.4 evidence

- Native Mac runs of both harness modes and the packaged smoke; measured Mac limits (longest lecture whose notes keep pace, backlog growth, memory via Activity Monitor or `/usr/bin/time -l`).
- Service failure during processing (note runtime stopped mid-generation) and low storage near SeaweedFS's free-space reserve. Not automated: stopping Ollama by name could affect a user's own Ollama, and filling a disk is unsafe on a shared machine. Use a disposable Mac volume/user.
- Packaged UI walk-through of the same workflow, quit/reopen recovery during capture, and prompted Flash Cards with the selected model.

No microphone, student library, model download, cloud provider, installer build/replacement or push was used.
