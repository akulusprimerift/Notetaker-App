# Notetaker for Windows — first public build

The local **0.4.0 development build** additionally has **Visual notes**, HTML export and **AI connections**. OpenAI/Claude APIs are separately billed; subscription options require installed official clients and account sign-in through your system browser. Cloud processing is explicit per lecture; audio transcription remains local. See [setup behavior and verification limits](implementation/visual-notes-providers.md). The public 0.3.1 instructions below describe the earlier release, whose downloads are unchanged.

Download the installer or portable ZIP from the [GitHub releases page](https://github.com/akulusprimerift/Notetaker-App/releases). The current public build is **0.3.1**.

Run `Notetaker-Native-0.3.1-Setup.exe` to install the app and its Start menu shortcut. Alternatively, extract the entire `Notetaker-Windows-x64.zip` into a folder and open `Notetaker.exe`; keep `_internal` and `NotetakerService.exe` next to it. The target is Windows 10 22H2 or Windows 11 x64; current verification was performed on Windows 11. This native Qt Widgets application contains no Chromium, Electron or WebView engine. Docker, Python, PowerShell, Ollama and a browser are not required on the receiving computer.

The application bundles its Python, Qt, speech and CPU note inference runtimes, plus the English faster-whisper small.en speech model. No separate Whisper install or speech download is needed. Your explicitly selected speech model is preserved on upgrades; fresh libraries use the bundled model. Note model weights remain separate: open **Local models** to use local Ollama files or import a compatible local Qwen GGUF. Select the model under **Note preferences**; recording automatically enables it for a new lecture. Inference never downloads weights or contacts external providers. CPU generation speed depends on the model and computer; recording works independently of inference.

The private standalone library is stored in `%LOCALAPPDATA%\NotetakerNative`, using SQLite with full synchronous writes and private audio files. This is a separate library from the earlier Docker development workspace; existing Docker data is not changed or automatically migrated. Keep the whole library folder when moving to a new computer. Close Notetaker before copying it; retain your model files separately.

Choose Slate or Midnight in the top bar. **Delete lecture** removes only the selected lecture after confirmation. **Delete course** removes the course and its lectures after reviewing the current count. Both use durable cleanup. The × beside Worth reviewing dismisses notices for that saved revision; Show review notices brings them back. New revisions can show new notices.

Choose a lecture and recording input, use **Record**, then **Stop and save**. The red **● Recording…** button is the active indicator; capture remains active until you press **Stop and save**. The level meter shows incoming sound; captured time and verified saved time are separate. Silence, a delayed device callback, sleep, or a transient Windows input warning no longer stops the recording automatically; the status message explains the condition while preserving the run. Supported stereo and float inputs are converted to mono PCM at their native sample rate. Live transcript and note previews appear beside the saved notes. Recognition uses short audio windows, so the first words follow the first eight seconds of saved audio plus inference time; previews are actual recognized segments, not a simulated typing effect. Notes begin after roughly 24 seconds of recognized audio or 100 words, plus local model processing time. Each small section streams into the preview, passes source checks, and is saved into Study notes while recording continues. The next section then follows automatically; the status shows sections saved and current progress. Larger backlogs are processed in sections too. Stopping flushes short remaining transcript tails. Previously saved sections survive a later generation failure, and student edits remain protected for comparison.

After an interruption, **Recover saved audio** reconciles the local journal with the library. Do not erase the library folder to resolve a recording error. Notes are checked and saved separately from audio. Upload syllabus/curriculum under Course materials and lecture slides with Add slides / materials. Text-based PPTX, PDF, DOCX, TXT and Markdown are supported; images and scanned text are not interpreted.

## Recommended first-use path

1. Install with `Notetaker-Native-0.3.1-Setup.exe`, or extract `Notetaker-Windows-x64.zip` as a complete folder.
2. Launch Notetaker and create or open a course. The native library is private to the current Windows user and opens without an access key.
3. In **Local models**, select a note model already available on the computer or import a compatible local Qwen GGUF. The app does not download models. The bundled English speech model is ready immediately.
4. Add course materials before recording when useful. Text from PPTX, PDF, DOCX, TXT and Markdown can support note regeneration; scanned images and slide visuals are not interpreted.
5. Select the lecture and input, then press **Record**. Watch both the level meter and the captured/verified-saved counters. Press **Stop and save** explicitly; recording is not stopped by a temporary input warning.
6. Let transcript and note sections catch up, then review, edit, regenerate proposals if needed, and export the saved revision you want.

## Files and backups

The library is stored at `%LOCALAPPDATA%\NotetakerNative`. Close Notetaker before copying that entire folder for a manual backup, and keep local model files separately. This library is intentionally separate from the older Docker/PostgreSQL development workspace and is not automatically migrated.

## Release notes and limitations

This is the first public, unsigned Windows build. Synthetic verification and an isolated Windows 11 installation passed, including installation, reinstall retention, audio journal recovery, local materials, themes and protected note editing. These checks do not qualify every physical microphone, accessibility, full-hour endurance, sleep/power-failure recovery, coordinated backup/restore, educational note quality or signed production distribution. macOS is planned for a later release.
