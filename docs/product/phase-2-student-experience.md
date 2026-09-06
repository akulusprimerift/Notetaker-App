# Phase 2: Student experience

Version: 0.1

Date: 2026-09-05

Status: Workflow and screen requirements; no application or interactive prototype is implemented in this phase.

## 1. Purpose and design baseline

Turn the [Phase 1 product brief](phase-1-product-brief.md) into a concrete student experience for **Capture → Transcribe → Organize → Verify → Study from the notes**. Detailed notes are the main work surface. The transcript and recording provide evidence and recovery paths.

The user selected **computer science, focusing on algorithms and code**, as the initial course example. A single student's private workspace and English-language lectures remain working assumptions. Another subject should change examples and evaluation fixtures without changing the core workflow.

The first browser experience targets a desktop or laptop. A narrow layout must still allow reading and editing, but phone recording and pairing are not introduced here. Exact supported browsers and hardware belong to Phase 3.

## 2. Decisions made in this phase

| Decision | Baseline behavior | Reason |
| --- | --- | --- |
| Main work surface | Detailed notes, with an adjacent source panel available on demand. | Students should not need to assemble study notes from a transcript. |
| Note depth | Detailed by default; optional Expanded adds more of the available explanation and intermediate reasoning. | Neither setting is allowed to remove critical material or invent missing reasoning. |
| Note format | Topic outline by default; sectioned prose as the second format. Both preserve equations, code blocks, and examples. | Keep preferences small and useful before adding complex templates. |
| Brief overview | An optional collapsed companion generated from the detailed version. | Switching to an overview must not replace or delete detailed notes. |
| AI explanations | Off by default for the first release; if supported and enabled, show them in distinct blocks. | Evidence origin must remain obvious. This does not introduce a separate tutoring feature. |
| Live changes | Update unedited blocks without stealing scroll position or keyboard focus; protect edited blocks and show suggested updates. | A changing lecture must not disrupt reading or destroy student work. |
| Export | One Markdown file containing the chosen note revision and a source appendix with cited transcript excerpts. Audio is excluded. | The document stays useful without a running app or access to private links. |
| Final notes | Versioned output with visible completeness and outstanding issues. | Finishing generation does not certify factual accuracy or complete capture. |
| Secondary actions | Catch Me Up and Mark Important remain optional extensions after the core path works. | They are not dependencies for the first complete lecture-to-notes milestone. |

Settings apply to new generation. Changing a preference after notes exist preserves the current revision and offers a preview of regenerated notes. Course defaults prefill the next lecture; each lecture retains the settings used for its own revisions.

The [illustrative computer science notes](phase-2-cs-note-example.md) show the intended treatment of algorithm steps, a worked example, complexity, exceptions, and unavailable board content. They are a manually authored design example, not generated or benchmarked output.

## 3. Screen map

| Screen | Purpose | Required content and actions |
| --- | --- | --- |
| S1 Course library | Find and organize lectures. | Create/select course; list lectures with date, title, capture/finalization status, and outstanding issues; open notes; recovery entry for unfinished sessions. Empty state offers Create course. |
| S2 Lecture preparation | Start with a working input and understandable settings. | Lecture title; course; microphone selection and input meter; Detailed/Expanded; Topic outline/Sectioned prose; actual processing location; Start recording. Optional terms input appears only when supported. |
| S3 Live lecture | Capture reliably while displaying useful notes. | Recording indicator and elapsed time; separate save and processing status; topic outline; detailed notes; Transcript/Source toggle; Stop recording. Secondary actions appear only when implemented. |
| S4 Source panel | Verify a specific note without losing reading position. | Selected claim/block; evidence label; transcript excerpt, interval, and revision; previous/next context; audio playback when retained; source correction action. |
| S5 Lecture completion | Account for outstanding audio and show finalization. | Recording stopped; pending audio; gaps; transcript and note progress; retry/finalize actions; access to saved live notes. |
| S6 Notes workspace | Study, verify, edit, compare, and export. | Topic navigation; detailed notes; optional overview; issues list; source panel; edit/save state; revision comparison; regenerate; export; lecture settings. |
| S7 Lecture data controls | Explain retention and carry out deletion. | Retained data summary; audio removal and lecture deletion actions; consequences; confirmation; deletion progress/failure; access restrictions. |

S3 and S6 share the note workspace, so the transition out of recording does not force the student to learn a different editor. S4 is a panel on wide screens and an in-page view with Back to note on narrow screens. S7 is accessed from lecture settings, away from the recording controls.

### Live lecture layout requirements

```text
Course / lecture                 Recording 23:10       Stop recording
Audio saved through 23:08       Transcript through 23:03
Notes through 22:40             Processing on this device

Topic outline    Detailed notes                         Source (on demand)
Definitions      Heading and explanation                Transcript excerpt
Worked example   Example, intermediate steps, result    18:42–19:20 / version
Limitations      Caveats and source controls             Play audio / Correct

New notes available — Jump to latest
```

The numbers above are illustrative UI copy, not timing targets. Show contiguous saved coverage, not merely the timestamp of the newest received chunk; a missing earlier chunk must remain visible.

### Final notes layout requirements

```text
Lecture title       Notes ready • 2 items need review     Export
Detailed / Overview              Format                  Version history

Topic outline    Detailed notes                         Source / proposed edit
                 Definitions
                 Explanation and reasoning
                 Worked example
                 Conditions and limitations

Saved revision / pending edits                 Review issues / Regenerate
```

These are layout requirements, not a rendered or usability-tested prototype.

## 4. End-to-end workflows

### F1 Prepare and start

1. From S1, select or create a course and open S2. Default the lecture name from course and date; allow editing it.
2. Select a microphone and show whether input is available. Distinguish unavailable input from a working input with no detected sound; silence alone does not block recording.
3. Show only supported processing configurations. Use plain language such as "Transcription and notes stay on this device" or name the external provider and the content it receives.
4. Start recording once. While starting, suppress duplicate requests. Display Recording only after capture has actually started.
5. If an AI service is unavailable but capture storage is usable, offer Record now, process later. If neither reliable local capture nor the required persistence path is available, explain the blocker and keep the session unstarted.
6. Enter S3 immediately after capture starts, retaining the selected settings. Recovery and storage feasibility are requirements to implement in Phase 3, not assumed browser guarantees.

### F2 Follow a dense lecture

1. Show provisional transcript as it arrives and topic-organized notes as material becomes usable. Before first output, distinguish Listening from Processing delayed and Recording interrupted.
2. Preserve definitions, examples, reasoning, caveats, and explicit emphasis. Do not insert empty boilerplate sections when the lecture provides no such content.
3. Label provisional output and show how far transcription and notes have progressed. A stalled model must not make an old topic appear current without a delay indicator.
4. Keep scroll and selection stable when the student reads an earlier topic. Show New notes available rather than forcing them to the bottom.
5. Allow opening the transcript or source evidence. Audio playback during capture requires an explicit action and a headphone reminder; do not autoplay into the recording microphone.
6. Accept a student note edit without pausing recording. Save it as student-authored content, protect it from subsequent automatic replacement, and retain its source relationships for review.

### F3 Stop and finalize

1. Stop recording immediately when requested; do not ask a confirmation that prolongs capture. Make a repeat Stop harmless.
2. Enter S5 and show outstanding uploads separately from processing. Stopping the microphone does not imply all audio is saved or transcribed.
3. Automatically finalize once expected audio is accounted for. Out-of-order or pending chunks keep the session pending, even when later chunks arrived.
4. If audio remains unrecoverable, offer "Finalize available audio" with the missing intervals or an explicit unknown-extent gap. The resulting revision is labeled Incomplete recording.
5. A student may reopen saved live notes while finalization runs. Leaving the page must not be described as safe if capture fragments or edits exist only in the current page's memory.
6. Apply final output to untouched content with version history. Where student edits would be affected, stage proposed replacements for comparison instead of applying them silently.
7. If late audio is recovered after incomplete finalization, preserve that revision and offer a new finalization. Update affected notes and citations as a new revision.

### F4 Inspect a source and resolve uncertainty

1. Activate a source control from a note block to open S4 and highlight the supported claim or passage. For mixed evidence, expose which source supports which text.
2. Show the cited transcript revision and interval. A newer transcript version appears as a separate notice, never as a silent replacement of the cited evidence.
3. Play retained source audio on request. If it was removed, keep the excerpt and show "Audio removed; transcript reference retained" without a broken playback control.
4. Distinguish Lecture paraphrase, Exact quote, Student edit, and AI explanation. Authorship and evidence origin are separate: generated lecture paraphrases still require lecture sources.
5. Label ambiguous words, conflicting statements, and missing visuals as issues. A reference to an unseen board equation must not produce invented mathematical content.
6. Return to the original note and reading position. An unavailable source or access failure must be shown explicitly; do not substitute unrelated material.

### F5 Correct, regenerate, and resolve conflicts

1. Editing a note shows Saving, Saved, or Not saved. Do not discard the unsaved text when a request fails; offer retry and copy as a recovery action.
2. A transcript correction records a new version while preserving the earlier transcript and its link to source audio. Student-corrected text remains labeled as such.
3. Mark dependent notes and any overview as Source changed. Their previous citations remain inspectable; they do not become verified by association with the new source.
4. Regenerate the selected topic or entire lecture using the selected source revision and preferences. Preserve current notes until the new result is available.
5. Where the student edited content, show Current and Suggested with Keep mine, Use suggestion, and Edit combined. The student's existing version remains in history after any choice.
6. If another change arrives during comparison, invalidate the stale proposal and require a fresh comparison. Do not apply it over newer edits.
7. Regeneration failure keeps the previous saved notes. Undo an accepted replacement by restoring a prior version as a new revision.

### F6 Save, export, and reopen

1. Reopening from S1 restores the latest saved revision and surfaces pending edits, source changes, incomplete capture, or finalization failure.
2. Default export to Detailed notes. Offer the overview only when it exists and identify it as a shorter companion.
3. Before export, resolve pending saves or explicitly choose the last saved revision. Do not imply an export includes edits that were never saved.
4. Export one `.md` file with title, course, lecture date, note revision, source revisions, completeness status, issue labels, and the selected note content. Preserve headings, code fences, equations, and readable source references.
5. Add a source appendix using stable reference labels such as `[S1]`, timestamp ranges, and the cited transcript excerpts. Multiple notes may reuse one source entry. App links may be additional conveniences, but must not be the sole evidence representation.
6. Exclude raw audio, unrelated transcript passages, credentials, and expiring private download URLs. Explain that the export contains lecture excerpts; local exports are not removed by deleting data in the app.
7. Label student additions and AI explanations in the file. Keep stale-source and missing-visual warnings visible. If a cited excerpt is unavailable, preserve its reference and clearly mark it unavailable.

### F7 Manage retained data

1. S7 shows what is retained and whether processing is still running. Initial design default: retain audio until the student removes it; storage limits and any automatic retention policy require explicit Phase 3 decisions.
2. Remove audio explains that replay and audio-based retranscription will be unavailable while notes and transcript remain. Delete lecture explains that lecture audio, transcript, notes, revisions, and other derived lecture data will be removed.
3. Require a scoped confirmation for deletion. This is a proposed app interaction, not a request for permission to edit this repository.
4. During recording, require Stop recording before deletion. During background processing, deletion must stop new derived writes and show progress until the deletion contract is satisfied.
5. On failure, show what remains and provide retry; do not report success before the application has actually completed its defined deletion work. Phase 3 must define backup retention and deletion completion semantics.
6. Restoring a connection or replaying old work must not recreate a deleted lecture. Returning to its URL shows unavailable without leaking its contents.

## 5. Independent operational states

Avoid a single green "Live" badge that conflates capture, persistence, and inference.

| Dimension | States to represent | Student-facing information |
| --- | --- | --- |
| Capture | Not started; Starting; Recording; Interrupted; Stopped | Whether the microphone is actively capturing, elapsed timeline, interruption location, and Resume when possible. |
| Persistence | Pending; Saved on this device awaiting transfer; Saved to application storage; At risk; Failed | Contiguous saved coverage, pending interval/count, confirmed local recovery availability, and storage action needed. |
| Transcript | Waiting; Updating; Delayed; Failed; Finalizing; Finalized | Latest processed interval, provisional/final status, and retry where appropriate. |
| Notes | Waiting; Updating; Delayed; Failed; Finalizing; Ready | Latest included transcript interval, current revision, outstanding proposals and issues. |
| Completeness | Complete for available capture; Pending audio; Known gaps; Unknown-extent interruption | Whether any lecture evidence is missing. Notes ready is independent of completeness. |
| Edits | Clean; Saving; Saved; Not saved; Conflict | Whether student changes are durable and what can be safely reopened or exported. |

"Saved to application storage" may refer to storage on the same computer in local mode; it must not imply an off-device backup. The exact durable acknowledgement and local recovery mechanism belong to Phase 3.

## 6. Recovery and degraded operation

| Trigger | Required behavior | Recovery action |
| --- | --- | --- |
| Microphone permission denied | Remain unstarted and explain how to retry input selection/permission. | Retry after permission changes; no false recording indicator. |
| Microphone disconnect or device sleep | Show interrupted capture and a known or unknown-extent gap; do not manufacture audio. | Resume the same lecture after capture is available, preserving the timeline gap. |
| Network or app service unavailable | Continue only while the supported local capture path is functioning; show which data is saved locally and pending. | Retry transfer and reconcile existing chunk identities without duplication. |
| Storage pressure or write failure | Surface risk before implying data is safe; do not discard pending capture silently. | Explain available actions and stop capture visibly if it cannot be preserved. |
| Page refresh or crash | Discover saved session state and any actually recoverable local fragments. | Offer resume for an interrupted lecture or finalize available audio; show unrecoverable gaps. |
| Transcription or note service fails | Keep capture and already saved evidence available where their paths still work. | Retry processing; never switch externally without an explicit processing-mode choice. |
| Transcript/notes connection drops | Retain displayed saved content with a stale indicator. | Reconnect from known revisions; apply only missing/new revisions without duplicates. |
| Duplicate tab or repeated action | Expose one active recording owner for a lecture; a second tab opens read-only monitoring. | Phase 3 defines ownership transfer after failure; do not permit concurrent capture by accident. |
| Edit save fails or revision conflicts | Keep the local edit visible, flag Not saved or Conflict, and preserve the server revision. | Retry, copy, or compare. |
| Finalization fails | Retain live notes and any prior final revision with an explanatory status. | Retry without replacing or duplicating student content. |

A refresh cannot be prevented reliably by a written requirement. The implementation must prove recovery behavior on supported browsers, and the UI may claim recoverability only when persisted data supports that claim.

## 7. Accessibility and interaction requirements

- All core actions work by keyboard with visible focus, descriptive labels, and logical tab order. Source and comparison panels return focus to their invoking control when closed.
- Do not rely on color alone for recording, uncertainty, errors, or save states. Pair icons with text.
- Announce important recording interruptions and save failures to assistive technology. Do not announce every transcript token or continuously move focus as notes arrive.
- Support text zoom and reflow. Keep code/equations readable with labeled local scrolling when necessary; the rest of the page should remain navigable.
- Provide explicit playback controls and textual timestamps. Never autoplay source audio or rely on sound as the only interruption signal.
- Make motion optional and preserve reading position. A Jump to latest control restores live following deliberately.
- Optional shortcuts must be discoverable, must not fire inside text editing, and must not replace visible controls.

These are requirements for later testing, not a claim of accessibility conformance.

## 8. Acceptance and Phase 3 handoff

The [acceptance scenarios](phase-2-acceptance-scenarios.md) map every core Phase 1 requirement to observable outcomes and relevant screens. [Verification notes](phase-2-verification.md) record which documentation checks ran.

Phase 3 must resolve:

- Supported hardware, browsers, processing configurations, and admission to capture-only mode.
- Durable capture acknowledgement, local recovery limits, timeline gaps, and contiguous coverage calculation.
- Single recording ownership, action idempotency, reconnect synchronization, and finalization with late/missing audio.
- Versioned transcript/note/provenance models, human edit protection, stale proposal detection, and dependency invalidation.
- Authorization, scoped deletion, background cancellation, backup retention, and protection against resurrection by replay.
- How preferences, overview dependencies, source excerpts, and portable Markdown exports are represented.

Phase 4 must select representative lecture material and validate note quality, terminology accuracy, latency, and visual-evidence limitations. The numerical Phase 1 quality gates remain proposed.
