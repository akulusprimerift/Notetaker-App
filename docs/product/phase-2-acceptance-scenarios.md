# Phase 2 acceptance scenarios

These are future application acceptance cases derived from the [student experience](phase-2-student-experience.md) and [Phase 1 scope](phase-1-product-brief.md). They have been reviewed for documented coverage, but have not been executed against an application. There is no runnable application in this phase.

The table uses Phase 1 requirement IDs and Phase 2 screen IDs. Every scenario states a trigger and an observable outcome; it does not prescribe an implementation technology.

| Scenario | Requirements | Screens | Given / when | Expected observable outcome |
| --- | --- | --- | --- | --- |
| UX-01 | CAP-01 | S1, S2, S6 | An empty workspace; create a course and lecture, save notes, then reopen it. | Course and lecture are discoverable; the saved note revision and outstanding issues return. |
| UX-02 | CAP-02, PRIV-01 | S2, S3 | A valid microphone; inspect the processing mode and start recording twice quickly. | Actual data destination is visible; exactly one capture starts and Recording appears only after successful start. |
| UX-03 | CAP-02 | S2 | Microphone permission is denied, then granted. | No false recording state; actionable error and successful retry without duplicate sessions. |
| UX-04 | CAP-02, TRN-01, NOTE-02 | S2, S3 | Models are unavailable but the supported capture storage path works; choose Record now, process later. | Audio capture and save states remain visible; transcription/notes show pending work, not invented output. |
| UX-05 | TRN-01, NOTE-01, NOTE-02 | S3, S6 | A dense lecture contains definitions, reasoning, examples, caveats, and a later correction. | Ordered provisional transcript and detailed topic notes appear; final notes preserve recoverable content and the correction with evidence. Quality is judged using the Phase 1 rubric. |
| UX-06 | NOTE-02 | S3 | The student reads an earlier topic while new notes arrive. | Scroll, selection, and focus remain stable; New notes available and Jump to latest are offered. |
| UX-07 | NOTE-03, EDIT-01 | S2, S6 | Detailed outline notes already exist; switch to Expanded sectioned prose and regenerate. | Existing detailed notes remain until a new revision is available; edited material receives proposals and preferences do not invent evidence. |
| UX-08 | NOTE-01, NOTE-03 | S6 | A brief overview exists; switch between Detailed and Overview. | Detailed content remains intact; the overview is identified as a shorter view and has its own source-change status. |
| UX-09 | SRC-01 | S3, S4, S6 | A note cites a transcript span and retained audio; activate its source. | The supported claim, exact cited revision, interval, and contextual excerpt appear; playback requires an explicit action and returning preserves position. |
| UX-10 | SRC-01, PRIV-01 | S4, S7 | The student has removed audio but retained notes and transcript. | Transcript evidence remains available; audio removal is explained and no broken playback control appears. |
| UX-11 | NOTE-01, SRC-01 | S3, S4, S6 | Speech includes an unclear term and a reference to an unseen equation. | Uncertainty and missing visual evidence are visible; the system does not invent the term or equation to make notes look complete. |
| UX-12 | SRC-01, NOTE-01 | S4, S6 | A block contains a lecture paraphrase, a student addition, and an optional AI explanation. | Each passage has distinguishable authorship/evidence labels; lecture citations do not falsely support the additions. |
| UX-13 | CAP-02 | S3, S5 | Connectivity fails during capture while supported local persistence remains available. | Local saved coverage and pending transfer are shown; reconnect transfers once without dropping or duplicating recorded content. |
| UX-14 | CAP-02 | S3, S5 | Microphone disconnects or the device sleeps and later resumes. | Capture interruption and known/unknown-extent gap are visible; resuming does not claim uninterrupted recording. |
| UX-15 | CAP-02, CAP-01 | S1, S3, S5 | The page refreshes or crashes with saved audio and possibly unsaved fragments. | Recoverable fragments are reconciled; the session offers resume/finalize and discloses unrecoverable gaps without claiming all fragments survived. |
| UX-16 | CAP-02 | S3, S5 | The local or application storage path cannot persist more audio. | At-risk status is visible; no false Saved state; capture stops visibly if preservation cannot continue. |
| UX-17 | TRN-01, NOTE-02 | S3, S6 | Processing falls behind, fails, or its update connection disconnects while capture still works. | Saved evidence remains; transcript/note progress shows delay or failure; reconnect/retry restores revisions without duplicate blocks or an undisclosed provider switch. |
| UX-18 | CAP-02, NOTE-02 | S3, S5 | Stop is clicked while an earlier chunk is missing and a later chunk has arrived. | Microphone stops immediately; pending audio prevents automatic complete finalization; displayed saved-through coverage does not jump over the hole. |
| UX-19 | CAP-02, NOTE-02, SRC-01 | S5, S6 | Audio cannot be recovered; choose Finalize available audio, then later recover the missing audio. | First revision retains an incomplete-recording label; late evidence offers a new version without rewriting prior citations or edits. |
| UX-20 | NOTE-02, EDIT-01 | S5, S6 | Final note generation fails after usable live notes exist. | Live notes and any prior final revision remain available; retry does not erase student edits. |
| UX-21 | EDIT-01, SRC-01 | S4, S6 | Correct a meaning-changing transcript error used by notes and an overview. | New transcript version is labeled student-corrected; affected notes/overview show Source changed; old citations still resolve to their original revision. |
| UX-22 | EDIT-01, NOTE-02 | S3, S6 | Edit a live note; automatic or final generation later proposes different text. | Student content is not silently replaced; comparison offers Keep mine, Use suggestion, and Edit combined. |
| UX-23 | EDIT-01 | S6 | A newer edit arrives after a regeneration comparison was opened. | The stale proposal cannot overwrite the newer edit; a fresh comparison is required. |
| UX-24 | EDIT-01 | S3, S6 | Saving an edit fails; later retry succeeds or a replacement is undone. | Unsaved text remains with retry/copy actions; a successful save is distinguishable; undo restores content as a new revision with history retained. |
| UX-25 | OUT-01, SRC-01, NOTE-01 | S6 | Export saved detailed notes containing code, equations, uncertainty, student additions, and AI explanations; read outside the app. | Markdown preserves structure and labels, includes source excerpts/intervals/revisions and completeness status, and requires no running app to read cited evidence. No audio, credentials, or expiring private URLs are included. |
| UX-26 | OUT-01, EDIT-01 | S6 | Export while edits are unsaved or a cited excerpt is unavailable. | Save first or explicitly export the last saved revision; unavailable evidence remains labeled rather than silently omitted. |
| UX-27 | PRIV-01, CAP-02 | S3, S7 | Request lecture deletion during capture or background finalization. | Capture must stop first; deletion explains scope, blocks new derived writes, and does not report completion prematurely. Failures expose retry and remaining data. |
| UX-28 | PRIV-01, CAP-01 | S1, S7 | A deleted lecture receives late work or an old URL is reopened. | Deleted data does not reappear; the URL reveals no lecture content; exported files are identified as outside app deletion control. |
| UX-29 | PRIV-01, SRC-01 | S1, S4, S6 | A lecture or source request is unauthenticated, unauthorized, or no longer accessible. | Access is denied without revealing other course data or substituting another source; the student receives a useful unavailable state. |
| UX-30 | CAP-02 | S2, S3 | Open the same active lecture in a second tab and attempt to start capture. | One tab retains recording ownership; the second monitors without creating a second recorder. Recovery after owner failure follows the Phase 3 ownership contract. |
| UX-31 | CAP-02, NOTE-02, SRC-01, EDIT-01, OUT-01 | S1, S2, S3, S4, S5, S6, S7 | Use keyboard navigation, assistive technology, text zoom, and a narrow viewport across core flows. | Actions remain usable with visible focus and labels; panels restore focus; status is not color-only; interruptions are announced without every transcript update being announced. |
| UX-32 | CAP-02, TRN-01, NOTE-01, NOTE-02 | S3, S5, S6 | Run the full 45–60 minute fixture with a documented interruption and then finalize. | No unexplained ordering loss or duplication; gaps remain disclosed; final notes are reviewed against content/faithfulness gates and timing/resource measurements are recorded. |

## Execution plan

- Phase 3 turns recovery, versioning, authorization, and deletion scenarios into architecture contracts.
- Phase 4 creates human-reviewed fixtures and calibrates quality thresholds. A link checker cannot validate semantic note quality.
- Phase 6 executes these scenarios using integration tests and student-facing walkthroughs on supported browsers and hardware.
- Record actual expected/observed results, environment, and evidence when application tests run. Until then, all UX scenarios remain **not executed**.
- Catch Me Up, Mark Important, full document retrieval, and vision are excluded from this core acceptance matrix because they are secondary or deferred in Phase 1.
