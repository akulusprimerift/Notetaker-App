# Visual notes and AI connections

Updated 2026-09-11. **6.8 / M08 remains active.** The user brought visual notes and both API/subscription connections forward from Phase 7. Earlier hardware, quality, accessibility, backup and release qualification gaps remain open.

## Student workflow

The Electron **Visual notes** tab draws source-linked schematics alongside explanatory passages. Ask for process diagrams, cycles or concept maps in the existing custom layout prompt, then apply and write notes. Text-only preferences remain supported. This first visual vocabulary uses labeled nodes and directed relationships; it does not draw molecular bond geometry, anatomical illustrations or reconstruct unread slide images.

**Export** offers self-contained HTML with diagrams, prose, source versions, a source appendix and review record, or Markdown with readable diagram descriptions. Export uses the selected saved generated/student revision. Final snapshot HTML uses frozen content and the stored export record. Comparison includes diagrams for both revisions. Student edits retain the original schematic with a review notice; keep, merge, replace and undo retain existing immutable-history behavior.

**AI connections** offers OpenAI API, Claude API, ChatGPT subscription through an installed official Codex client, and Claude subscription through an installed official Claude Code client. Enter a model ID available to the account. API keys use current-user Windows DPAPI and atomic replacement in the private library's `connections` directory. Keys never enter API responses, lecture settings/history or exports. Saving a connection does not call a provider. **Test with sample text** sends a synthetic example and consumes API/subscription usage.

For subscriptions, select the official `.exe` and press **Sign in with subscription**. Its system-browser login uses a separate Notetaker client profile. No browser engine is embedded and no clients or models are downloaded. The official client manages token persistence; Codex requires its keyring rather than plaintext auth-file fallback. Notetaker does not extract another application's tokens. **Sign out** logs out this separate profile. **Disconnect** removes the connection while retaining client sign-in and saved notes.

Select the connection in **Note preferences**, then confirm cloud processing for that lecture. Requests send selected transcript/material text and prompts; recording and speech recognition remain local. The workspace identifies the processing location. Authentication, quota, truncation, timeout and connection failures retain saved notes without switching providers. Replacing a connection changes its identity: apply it again to affected lectures. Disconnect cannot retract requests already sent. API output is capped at 6,000 tokens; inputs and streamed responses are bounded. Set monetary budgets in the provider account; no app-wide dollar ledger is implemented.

## Architecture

Optional bounded diagram objects extend the draft/canonical material-note schemas. Old JSON revisions remain valid; no migration or historical rewrite is required. Draft prompt v2 distinguishes schematics from missing visual evidence. Validation rejects unknown properties, duplicate node IDs, absent edge endpoints and diagrams without cited passages. This checks structure/source identity, not scientific accuracy.

The app renders its own SVG shapes with React text nodes and escaped model labels; arbitrary model HTML and JavaScript are never executed. HTML exports contain escaped text and app-generated inline SVG, no external assets or scripts, and a restrictive content security policy. The Electron renderer and export path share the same source-linked content contract.

The provider dispatcher retains contextual batches, canonical validation, streamed previews, settings/attempt/epoch fencing and protected publication. OpenAI uses streamed Chat Completions; Anthropic uses Messages. Provider/model and a connection-generation identifier bind preferences and provenance; cloud model weights are not claimed immutable.

Subscription bridges use Codex app-server JSON-RPC and Claude Code print-mode events. Authentication must identify a subscription before submitting notes. Inherited API credentials and alternate endpoints are removed. Codex uses a private profile, ephemeral thread, read-only sandbox and disabled execution/browser/plugin features; unexpected approval requests fail. Claude disables tools, MCP, hooks, customizations, persistence and browser integration, with one generation turn. Generation subprocesses have bounded output/deadlines and owned Windows process jobs. Client versions and managed policies still require compatibility qualification.

## Provider documentation checked

- [OpenAI app-server](https://learn.chatgpt.com/docs/app-server) documents embedding, managed ChatGPT sign-in and streamed events. [Authentication](https://learn.chatgpt.com/docs/auth) distinguishes subscription and API access.
- [OpenAI Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create), [Claude Messages](https://platform.claude.com/docs/en/api/messages/create) and [Claude CLI reference](https://code.claude.com/docs/en/cli-reference) define the adapters.
- Claude's [Agent SDK subscription update](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan) says the June 15 billing change is paused and SDK/third-party usage continues against subscription limits. Its [developer login guidance](https://support.claude.com/en/articles/13189465-log-in-to-your-claude-account) directs developers building for others to API keys. These pages are inconsistent. The bridge uses the official client only; confirm distribution/plan support with Anthropic before advertising universal subscription support. No custom Claude OAuth impersonation or token extraction is implemented.

## Executed evidence

- Windows isolated SQLite/synthetic regression: **175 backend tests passed, one service-only skip**. Covers visual validation/export, edits/undo, cloud consent, DPAPI, streamed API responses, authentication/quota/redirect failures and connection replacement.
- **Three additional subscription-protocol tests passed** for authentication gates, incremental messages and unexpected approval rejection.
- Installed Codex app-server started in a fresh signed-out profile and returned authentication-required before any note text was submitted. This is startup/protocol evidence, not authenticated inference.
- **60 JavaScript contracts**, web typecheck, ESLint and production build passed. Ruff passed for the API. The previous desktop diagram reader was replaced by the Electron React/SVG reader in this increment.

Initial tests encountered the known Windows default pytest-directory permission issue and a duplicate module filename. A fresh project-local directory and distinct filename resolved them. A mutable-reference test exposed a missing diagram deep copy; fixed and rerun successfully.

## Remaining qualification

Live API credentials, paid model inference, successful browser sign-in, authenticated Codex generation and Claude Code installation/inference were not exercised. No microphone, student lecture data, cloud inference or model download was used. Mock streams do not qualify live providers. Representative biology/chemistry diagrams need human scientific review; dense graphs may need simpler prompts.

The session transfer records final 0.4.0 package/smoke evidence. No public release, push or installation over the student library is performed. Existing release gates remain open.
