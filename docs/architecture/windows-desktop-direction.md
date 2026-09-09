# Windows desktop direction

Date: 2026-09-09. The user explicitly selected a native Windows application with no browser engine. Qt Widgets replaces Electron for the deliverable. Python, Qt, faster-whisper and the CPU Ollama executable are bundled; models remain user-selected local files. An explicit standalone SQLite/private-file profile removes Docker dependencies while retaining backend source, revision and deletion contracts. Existing Docker libraries are preserved separately. See [native download](../native-download.md) and [M08](../implementation/phase-6-m08.md). The Electron proposals below are historical and do not control the native implementation.

The product is a course-neutral Windows note-taking application. The current browser interface is the development surface for the same product. Reuse the existing React interface, Python services, source validation and saved data when adding a desktop host.

## Proposed first desktop increment

Use an Electron desktop host for the first Windows proof of concept. This is an engineering recommendation based on the existing JavaScript UI and Chromium audio-capture implementation, not a completed compatibility result. Electron's bundled renderer gives a specific browser runtime to test. Tauri remains an alternative if installation size becomes a demonstrated priority; it introduces a Rust host and a Windows WebView2 distribution decision. Both have documented Windows installer paths: [Electron Forge Squirrel.Windows](https://www.electronforge.io/config/makers/squirrel.windows) and [Tauri Windows installers](https://v2.tauri.app/distribute/windows-installer/).

Bring a small desktop-host experiment forward after the current note-generation repair and writing-preference checks. Keep complete installer/upgrade qualification in M08 and continue long-lecture note processing in M04. The experiment must not claim that merely opening a localhost page is a finished installable product.

1. Launch a single app window with a normal Windows title and icon. Reuse the existing interface and authenticated API.
2. Detect the local services, show their startup progress, and offer clear recovery when Docker or Ollama is unavailable. For the first experiment, disclose these prerequisites; do not silently install them or bundle model weights.
3. Manage only processes/services started by this app. Closing a window must not discard recording buffers or kill unrelated Docker workloads. Define background note processing and explicit Quit behavior.
4. Test saved notes, model/style preferences, source playback, close/reopen, offline recovery and synthetic audio in the actual desktop renderer. Physical microphone testing still requires the user's approval.
5. Before shipping an installer, decide how Python, PostgreSQL, audio storage, Kafka and Ollama are distributed and upgraded. Keep writable data and model caches in a documented per-user Windows location outside the install directory. Qualify migration and coordinated restore with existing data.

## Desktop boundary

Follow [Electron's security guidance](https://www.electronjs.org/docs/latest/tutorial/security): isolate and sandbox the renderer, keep Node integration disabled, restrict navigation/new windows, and validate narrow IPC calls. Lecture/model text never receives filesystem or shell execution authority. Microphone permission should follow the user's recording action; it must not be automatically granted to arbitrary pages. Future OpenAI/Claude credentials belong in Windows-protected storage, outside renderer storage and exported notes.

M08 remains responsible for clean-machine install, Start menu launch, upgrade preservation, signing/distribution decisions, uninstall data-retention behavior, accessibility and full-lecture qualification. See the [build phases](../project-phases.md) and [M04 status](../implementation/phase-6-m04.md).
