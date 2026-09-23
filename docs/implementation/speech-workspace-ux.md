# Speech workspace usability — 2026-09-23

Active phase: **6.8 / M08 — Standalone Windows distribution**.

## User-facing changes

The recording toolbar no longer offers Mark Important. Previously saved bookmarks, sources and undo remain available in Study tools. The reported spinner/recording interruption path is removed; its historical root cause was not reproduced. No existing student data or revisions are rewritten.

Study notes contains a 144px transcript viewport directly above the note content. It follows new saved passages and fenced partial recognition, scrolls internally, shows at most 30 recent saved passages, and never scrolls the document. The full Transcript tab retains playback, corrections and history. Draft text remains labeled provisional and is rendered as text. The recorder stays mounted across tab changes, speech-status updates and help dialogs.

The selected note LLM now receives explicit instructions to identify important concepts using context, repetition and instructor cues while respecting negation and corrections. Existing canonical `emphasis` blocks render bold with the current theme's background and accent border, labeled “Important · AI identified.” Citation validation and student revision protection remain intact. This applies to new generated notes; it does not silently regenerate saved revisions. Human importance/educational quality remains unqualified.

A lecture-wide speech status distinguishes missing files, selected/unverified, loading, failed load, offline worker and loaded readiness. Native readiness is a three-second worker heartbeat with a per-launch nonce and 15-second expiration; it requires completed model loading, not just file existence. Docker retains honest selected/unverified status when no shared readiness path is configured. The status has no lecture text or credentials. Readiness does not promise recognition quality or real-time latency.

Select speech model opens a narrowly authorized Electron action, checks the saved folder, known model/cache folders and Downloads with bounded scanning, and offers a discovered folder before a normal folder chooser. All three required files are checked. Selection saves settings without restarting services or interrupting capture. If services are running, users finish recording and confirmed saves before quitting/reopening. There is no automatic download, import, cloud fallback or microphone access.

The small modal explains Windows downloads and local folder selection, plus macOS file preparation only (macOS support remains future work). A fixed allowlisted link opens the publisher's model-file page in the user's browser. Guidance was checked against the [publisher file listing](https://huggingface.co/Systran/faster-whisper-small.en/tree/main) and [Hugging Face download documentation](https://huggingface.co/docs/huggingface_hub/guides/download).

## Executed evidence

- Windows backend: 233 passed, 1 service-only skip; readiness tests reject stale/previous-launch/wrong-model status, corrupt files and failed loads.
- 60 JavaScript contracts and 15 desktop tests passed, including local speech discovery with incomplete-folder rejection.
- Browser flows with synthetic responses passed safe partial text, transition to saved passages, fixed height and bottom-following, missing/ready status, modal Escape/focus return, bold emphasis, retained recorder DOM, legacy bookmark review/removal/undo, Midnight and 400px layout.
- Frontend typecheck/lint, Python lint and production web build passed. Packaging verification is recorded below when complete.

Synthetic checks do not establish microphone quality, hardware latency, educational usefulness, installed upgrade or release readiness. Existing M08 gates remain open.

## Next work

Install the updated build and qualify the existing-library upgrade and actual hardware recording separately. Review automatic importance choices against held-out human-reviewed lectures; refine prompts from measured false positives/negatives. Preserve Windows-before-macOS sequencing and the deferred Phase 7.4 experiment.

## Packaged verification and environment limit

The frozen service built successfully. Two isolated native-host runs confirmed **speech_model_ready_before_capture** with the existing local faster-whisper model. End-to-end audio saves could not complete on this environment: the first attempt exceeded the test's 10-second HTTP timeout; the 60-second rerun returned 503. SeaweedFS logged 0.76% free disk, below its required 1% reserve (about 10 GB on this drive). This is a storage prerequisite, not evidence of successful live inference. No user files were deleted and the storage safeguard was not lowered. Isolated profiles: `.local/host-smoke-8f9cfeb0b2864e79a2cd5110467fad4d` and `.local/host-smoke-2b1f9de3886b4c5fbca15b0f0bbb556d`.

The final web bundle `.local/desktop-web/3c189b3f-782e-426e-aff4-6a0b10efab15` passed inventory/hash verification, isolated React hydration and capture-asset checks. The final browser run again passed the live-preview and legacy-study flows. The 400px Midnight screenshot was inspected with the preview immediately above note content. Source checks distinguish this from microphone or live inference qualification.

The actual packaged `win-unpacked/Notetaker.exe` passed first-library setup, missing-model status, the workspace selection action, persisted model path, normal quit/reopen, loaded-worker readiness, absence of Mark Important, transcript preview and the help dialog. Renderer Node access remained disabled. The native folder chooser was stubbed to the existing local speech folder; all application IPC, persistence, service startup and model loading were real. Isolated profile: `.local/speech-setup-smoke-6d3597be-8df8-4c17-a559-d044eee96707`. No microphone was opened. An initial test assertion was invalid because Bun constant-folded `typeof require` in its serialized callback; evaluating that expression as a browser string corrected the harness and the rerun passed.

Packaged service SHA-256 matches the independently tested frozen executable. Installation/upgrade on the student's existing library has not been performed.

## Delivery

Unsigned Windows x64 installer: `.local/speech-ux/installer/Notetaker-0.1.0-Windows-Standalone-Setup.exe`, **397,870,083 bytes**, SHA-256 `3AEBB1A0A8CBF3EB71DCE6B942FF0660C07763B6878F44CA147274C515CB6303`. It uses the tested packaged application and frozen service. The installer build exited successfully.

Close Notetaker normally before installing this build. Keep the existing library selection. Ensure more than 10 GB free on C: before recording so the existing audio storage reserve is met; the packaging run ended with approximately 5 GB free. Models remain user-selected local files. No installed binaries, student library or installed settings were replaced by this task. No push was performed.
