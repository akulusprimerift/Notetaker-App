# Ollama Cloud note models — 2026-11-07

Phase **6.9.5** remains active. At the user's request, Ollama Cloud is an optional, explicitly chosen cloud provider for notes and generated study questions, alongside the OpenAI and Claude API connections. Speech transcription stays local.

## Behavior

- **Connect:** Settings → Accounts & API keys → API provider **Ollama Cloud**, then paste a key created at `ollama.com/settings/keys`. On macOS the key is stored by the Electron provider bridge in the login Keychain (`safeStorage`); on Windows it uses Windows protected storage. It never enters lecture history, exports or the renderer.
- **Discovery and validation:** the bridge lists models from `https://ollama.com/api/tags` (embedding models are excluded). The public list may not check the key, so connecting sends one `Reply with OK.` request with `num_predict: 1` and no lecture content. `401` rejects the key and keeps any existing connection; `429` reports the usage limit; `403` means the key authenticated but that plan cannot use the probe model, so the key is accepted. Refresh repeats discovery.
- **Generation:** `POST https://ollama.com/api/chat` with `Authorization: Bearer <key>`, `stream: true`, `format: "json"`, `temperature: 0` and `num_predict: 16384`. The larger allowance leaves room for reasoning models' private thinking before the note JSON. Streaming is native Ollama NDJSON: only `message.content` becomes preview/output; `message.thinking` is never shown or saved. Completion requires `done_reason: "stop"`; tool calls, stream errors, truncation and oversized output fail without saving. Output passes the same citation/source validation (`canonical`) as every other cloud draft, and metadata records `processing_location: cloud`.
- **Consent and no fallback:** `ollama-cloud/<model>` is a cloud model, so selecting it requires the existing per-lecture cloud confirmation. Notetaker never falls back between local and cloud models.
- **Local Ollama stays local:** a signed-in local Ollama can list `-cloud` models with `remote_host`/`remote_model`. The local adapter already hides and refuses those models (covered in `test_notes.py`), so cloud inference cannot happen through the local path without consent.

The documented API is from `docs.ollama.com/cloud`, `/api/authentication`, `/api/chat` and `/api/tags` (read 2026-11-07). Those pages do not document cloud error codes or confirm that every cloud model honors `format`; the adapter therefore uses JSON mode rather than a strict schema and relies on server-side validation.

## Executed evidence

Apple Silicon Mac (macOS 26.6). No real Ollama account or key was used; requests were synthetic test doubles.

- Desktop: NDJSON parsing across byte boundaries with thinking excluded, `length` truncation, incomplete stream, tool call and error rejection; bridge discovery/probe, `401` preserving the previous key, `403` acceptance, exact request host/headers/body and no key in inventory. **42 desktop contracts, 63 JavaScript contracts passed.**
- Backend: direct (non-bridge) streaming with validated citations, no thinking or secret in previews/metadata, truncation and authentication failures; per-lecture consent required for `ollama-cloud/...`. **Full backend 284 passed, 1 skipped.**
- Packaged Mac app: the Accounts dialog lists **Ollama Cloud** with its key guidance and the platform-neutral storage notice (screenshot inspected); the bundled bridge contains the cloud adapter.

Not yet verified: a real Ollama Cloud key, live model list, actual cloud note quality/latency, usage-limit behavior and which cloud models honor JSON mode. The user connects their own key in the app; Notetaker does not enter or request it.
