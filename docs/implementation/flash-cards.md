# Flash Cards

Product change accepted 2026-10-03. The former Study Tools tab is labeled **Flash Cards** and contains one focused card flow. It keeps recording, Study notes, Transcript and Finish in the lecture workspace.

## Student flow

- Opening or revisiting the tab reads saved sets only. It never queues generation because of tab changes, note updates or dialog opening.
- **Create flash cards** opens a keyboard-accessible prompt dialog. The student submits nonempty instructions to start a new generation. The form is disabled until the current notes and selected note model are available.
- The request uses the current selected saved note revision (student revision when present, otherwise the latest generated revision), every complete eligible note block, exact original source text and source warnings. Passages with current transcript/material citations keep those citations; uncited student-authored or edited passages are pinned to the selected revision and cited as student notes. Unedited unsupported explanations, stale-source and diagram blocks are omitted whole; their qualifications are not silently cut out.
- Each request can return up to eight flash cards. A 16 KiB evidence limit and the selected model's context limit fail visibly instead of truncating saved notes. Cloud selections keep the existing per-request confirmation for sending notes, sources and instructions.
- Saved cards can be revealed, moved through, inspected with exact source quotes, self-assessed, edited with expected-version checks and compared with append-only history. An uncertain enqueue retry repeats the same idempotency key and request body. A failed job leaves existing sets intact and offers an explicit retry.
- Loading, no-supported-notes, missing-model, queueing, worker failure, stale-source and saved-empty states are announced or labeled accessibly. Streaming previews are marked unvalidated and never presented as saved cards.

## Backend and persistence

The existing `/lectures/{lecture_id}/study/questions` endpoint and `question_sets` table now accept `revision_id`, the selected `preference_id`, a `prompt` and optional explicit cloud consent. New requests pin `contract_version: flashcards-v1`, the student's exact instructions, the current note revision and all eligible note block IDs in the existing immutable evidence JSON. Uncited student notes get a deterministic evidence ID bound to the note revision and passage; original transcript/material citations remain in the same request when present. The worker sends both the prompt and the saved notes/source context to the selected model; it validates every quote against the exact source record, checks the selected model again, and preserves existing lease/attempt, lifecycle, settings, note-revision, ownership, CSRF, idempotency and expected-version protections.

No table change or data migration is needed. Existing saved study sets, student edits, assessments, source records and note history remain intact; old non-flashcard question sets are not converted or deleted. The `/study/learning` and `/study/catch-up` read surfaces and UI have been retired. This removes no recordings, transcripts, notes, source evidence or bookmark rows.

## Verification

Executed on the assigned macOS worktree with synthetic data only; no microphone or model download:

- `PYTHONPATH=apps/api:apps/api/tests uv run --no-project --python .venv/bin/python python -m pytest -q apps/api/tests/test_questions.py apps/api/tests/test_learning.py apps/api/tests/test_study.py`: 36 passed after adding uncited student-note provenance coverage.
- `bun tests/desktop/questions-ui.cjs`: passed prompt dialog, whitespace refusal, no generation on open/tab switch/reload, CSRF, same-key retry, current-source reveal, student edits/history/conflicts, stale-source gate, empty state and 400 px layout. Screenshots were inspected under `.local/questions-review/`.
- `bun run test`: 63 passed. `bun run typecheck`, `bun run lint`, `bun run build:web`, `uv run --no-project --python .venv/bin/python ruff check apps/api` and `git diff --check`: passed.
- `bun run verify:docs` with the task-local PowerShell 7.6.6 directory on `PATH`: 51 planning Markdown files and 279 local links pass; 32 student scenarios map to 10 requirements/contracts and 8 milestones, with 6 open gates assigned.
- Full API suite: 256 passed, 3 skipped, 8 failed. Every failure is in existing cloud/provider-connection tests that call Windows protected storage; this macOS host raises the intended `Provider connections require Windows protected storage` error. The 36 affected feature tests pass separately.

These independent-branch checks validate synthetic flow and evidence structure, not real local-model card quality, human learning benefit, Windows packaging or release readiness.

## Revision 2 combined integration and qualification — 2026-10-03

Combined validation uses integration commit `c03904bf6ec0f003de3ffef7377a9778c49b6cf7`, whose parents are Flash Cards `532141ad1db0503ec5a9f5722242aff76b68d939` and Settings + SQLite integration `f582e35fc1043ae6a975fb7abd1dffeb688b6f8a`; that predecessor combines Settings `952a803d2c089ba9afaabf0ab16905b64307a746` with SQLite `109cff9409965cf3087762b623c8af26ac7a1bdd`. The feature and both predecessors were exercised together before publication prep.

- Full backend on the combined tree: **259 passed, 4 skipped, 8 failed**. All eight failures are the existing Windows protected-storage provider tests on macOS (`Provider connections require Windows protected storage`). No new integration failures were observed.
- Focused saved-note/persistence check: the manually added, transcript-uncited note remained in selected-revision context, was queued with the entered prompt, and was persisted through worker completion as a student-note citation. SQLite app-database and staged SQLite conversion checks also passed: **3 passed**, 2 dependency deprecation warnings.
- Flash Cards browser flow passed on the combined tree, including no generation on open/tab switch/reload, prompt-only generation, blank-prompt refusal, CSRF, idempotent retry, source reveal, edits/history/conflicts, stale-source refusal and the narrow layout.
- Settings browser flow passed keyboard/focus handling, nested dialog return, four persisted themes, text contrast (minimum **6.09:1**), selector/focus contrast, reduced motion and 360px layout.
- A no-capture persistent-navigation run passed: the recording controller DOM remained mounted across Notes, Flash Cards, Transcript and Finish. The now-retired “Study tools” navigation expectation in the legacy layout script was updated to “Flash Cards”. The standard synthetic audio-start path was not rerun; the parent’s same-runtime Mac AudioWorklet qualification remains the applicable capture limitation.
- `bun run test` (**63 passed**), `bun run typecheck`, `bun run lint`, `bun run build:web` and Python Ruff passed on the integrated source. After this documentation and test follow-up, `PATH=/Users/kash/Documents/.multplx-worktrees-e1986cb8d2eb1708/f6e5c6993a37996437b5aedc303dae53cae55a969c25f903d56e624e73a10052/.local/tooling/powershell/7.6.6:$PATH bun run verify:docs` passed: **53 planning Markdown files and 307 local links**, including structural coverage.
- `tests/desktop/appearance-ui.cjs` reaches its platform-font assertion and fails on this Mac because Chromium reports **Helvetica Bold** for the heading while the check requires the locally installed TikTok Sans face. The `Workspace Sans` declarations are unchanged from Settings and no font files are tracked in the web app. This remains a Windows font-installation qualification limit; the assertion and font styling were left intact.

Synthetic browser screenshots captured from the combined tree are stored beside the task delivery report as `notes-finish-workspace.png` (Notes/Finish navigation, course sidebar and short transcript preview) and `flash-cards-prompt.png` (prompt dialog). No real lecture data, model inference or microphone was used.

Revision 2 keeps final publication and fast-forward of the original feature branch gated on the parent’s current typed SQLite completion for `f582e35fc1043ae6a975fb7abd1dffeb688b6f8a`. After that gate, the focused Flash Cards PR targets `mx/notetaker-sqlite`. Ordinary push/PR publication is authorized; remote merge, force push and shared target-branch changes are not.
