# Windows desktop direction

Date: 2026-09-11. The user selected Electron as the only Windows host. The hardened Electron shell reuses the Next.js/React workspace, authenticated FastAPI contracts, Docker service lifecycle and Chromium audio-capture implementation. Models remain user-selected local files; no model weights are downloaded by the app. The previous Qt/native standalone profile has been removed from the repository. See [M08](../implementation/phase-6-m08.md).

The product is a course-neutral Windows note-taking application. The current browser interface is the development surface for the same product. Reuse the existing React interface, Python services, source validation and saved data when adding a desktop host.

## Electron desktop increment

Use the existing Electron desktop host for the Windows delivery. Electron's bundled renderer gives the capture and navigation flow a specific Chromium runtime to qualify, while the Docker/FastAPI services remain the development service profile. Tauri is not part of this delivery decision.

The current increment turns the host experiment into the primary Windows path. Keep complete installer/upgrade qualification in M08 and continue long-lecture note processing in M04. The installable app must keep the service boundary, capture recovery, source protection and explicit model selection visible to students.

1. Launch a single app window with a normal Windows title and icon. Reuse the existing interface and authenticated API.
2. Detect the local services, show their startup progress, and offer clear recovery when Docker or Ollama is unavailable. For the first experiment, disclose these prerequisites; do not silently install them or bundle model weights.
3. Manage only processes/services started by this app. Closing a window must not discard recording buffers or kill unrelated Docker workloads. Define background note processing and explicit Quit behavior.
4. Test saved notes, model/style preferences, source playback, close/reopen, offline recovery and synthetic audio in the actual desktop renderer. Physical microphone testing still requires the user's approval.
5. Before shipping an installer, decide how Python, PostgreSQL, audio storage, Kafka and Ollama are distributed and upgraded. Keep writable data and model caches in a documented per-user Windows location outside the install directory. Qualify migration and coordinated restore with existing data.

## Desktop boundary

Follow [Electron's security guidance](https://www.electronjs.org/docs/latest/tutorial/security): isolate and sandbox the renderer, keep Node integration disabled, restrict navigation/new windows, and validate narrow IPC calls. Lecture/model text never receives filesystem or shell execution authority. Microphone permission should follow the user's recording action; it must not be automatically granted to arbitrary pages. Future OpenAI/Claude credentials belong in Windows-protected storage, outside renderer storage and exported notes.

M08 remains responsible for clean-machine install, Start menu launch, upgrade preservation, signing/distribution decisions, uninstall data-retention behavior, accessibility and full-lecture qualification. See the [build phases](../project-phases.md) and [M04 status](../implementation/phase-6-m04.md).
