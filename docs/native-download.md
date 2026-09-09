# Notetaker for Windows

Run `Notetaker-Native-0.2.0-Setup.exe` to install the app and its Start menu shortcut. Alternatively, extract the entire `Notetaker-Windows-x64.zip` into a folder and open `Notetaker.exe`; keep `_internal` and `NotetakerService.exe` next to it. The target is Windows 10 22H2 or Windows 11 x64; current verification was performed on Windows 11. This native Qt Widgets application contains no Chromium, Electron or WebView engine. Docker, Python, PowerShell, Ollama and a browser are not required on the receiving computer.

The application bundles its Python, Qt, speech and CPU note inference runtimes. Model weights are separate. Open **Local models** to select an existing faster-whisper model folder, use existing Ollama model files, or import a compatible local Qwen GGUF. Model downloads and external providers are never started automatically. CPU generation speed depends on the model and computer. A model is necessary for transcription or note generation; recording and your saved library work independently.

The private standalone library is stored in `%LOCALAPPDATA%\NotetakerNative`, using SQLite with full synchronous writes and private audio files. This is a separate library from the earlier Docker development workspace; existing Docker data is not changed or automatically migrated. Keep the whole library folder when moving to a new computer. Close Notetaker before copying it; retain your model files separately.

Choose Slate or Midnight in the top bar. Delete course asks you to review the current lecture count and then removes course content through durable cleanup. The × beside Worth reviewing dismisses notices for that saved revision; Show review notices brings them back. New revisions can show new notices.

Use **Record**, then **Stop and save audio**. After an interruption, **Recover saved audio** reconciles the local journal with the library. Do not erase the library folder to resolve a recording error. Notes are checked and saved separately from audio. Upload syllabus/curriculum under Course materials and lecture slides with Add slides / materials. Text-based PPTX, PDF, DOCX, TXT and Markdown are supported; images and scanned text are not interpreted.

This is an unsigned development build. Synthetic verification does not qualify real microphone devices, full-hour endurance, accessibility, educational quality or release readiness. Installing a newer application folder does not remove the per-user library. No public GitHub release has been published by this implementation task.
