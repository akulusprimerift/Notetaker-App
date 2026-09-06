# Phase 1: Product definition and scope

Version: 0.1

Date: 2026-09-05

Status: Initial scope baseline; working assumptions and proposed targets are identified below.

## 1. Product priority

The application must transcribe lectures and turn them into high-quality notes. This is the most important project capability, particularly for dense, fast-moving, content-heavy courses.

The first major application milestone is:

> Process a complete, content-heavy lecture into detailed, trustworthy, editable notes that a student can realistically study from.

The current product loop is **Capture → Transcribe → Organize → Verify → Study from the notes**. The broader practice, measurement, and personalization loop remains a future direction.

This brief records the user's current priority. It narrows the first release described by the original source documents without replacing their broader long-term vision. It is a product scope document, not an instruction to implement every referenced technology.

## 2. Initial audience and assumptions

The initial user is a student who needs to preserve and understand substantial lecture content while minimizing interaction during class.

Working assumptions for design and evaluation, subject to revision:

- Begin with a single student's private workspace, with courses and saved lecture sessions.
- Use English-language lectures and an initial technical course, with computer science as a candidate benchmark domain.
- Use a desktop or laptop browser for live capture. Define the supported operating system, browser, and hardware in Phase 3.
- Use 45–60 minute lectures as the first endurance benchmark. This is a test baseline, not a promised maximum duration.
- Develop locally and preserve the preference for a self-hosted path. Feasibility of simultaneous local transcription and note generation must be measured.

The audience is not limited permanently to technical subjects. Broad subject and language support should follow validation on the initial domain.

## 3. What good notes mean

Good notes provide organized compression without losing the substance needed to understand the lecture. Their length follows the material; an arbitrary word limit must not force removal of important content.

| Lecture content | Expected treatment in detailed notes |
| --- | --- |
| Topics and transitions | Use coherent headings and explain how related topics connect. Do not equate elapsed time with a new topic. |
| Definitions and terminology | Preserve meaning and technical terms. Clearly distinguish exact quotations from paraphrases. |
| Explanations and reasoning | Retain the steps connecting premises to conclusions, including why a method works when explained. |
| Worked examples | Keep the problem, relevant intermediate steps, and result together with the concept they illustrate. |
| Procedures and algorithms | Preserve ordered steps, assumptions, inputs/outputs, complexity, and limitations when discussed. |
| Equations and code | Preserve recoverable symbols, identifiers, and structure. Identify missing visual evidence instead of inventing it. |
| Qualifications and exceptions | Retain conditions under which a statement holds, counterexamples, caveats, and limitations. |
| Professor emphasis and corrections | Preserve explicit emphasis and later corrections with source links. An exam prediction must not be presented as a professor statement. |
| Repetition and digressions | Consolidate redundant wording while retaining new examples, qualifications, and useful context. |
| Unclear or conflicting evidence | Mark uncertainty and expose the relevant source. Do not silently reconcile conflicting statements. |

For example, notes on an algorithm should preserve its purpose, steps, assumptions, worked example, complexity, and limitations when those appear in the lecture. Missing information may be added only as a separately labeled AI explanation, never as reconstructed lecture evidence.

A brief overview may accompany the detailed notes. Students must be able to return to the full detailed version.

## 4. First-release scope

### Required core capabilities

| ID | Capability | Required behavior |
| --- | --- | --- |
| CAP-01 | Course and lecture organization | Create a course, start a named lecture, and reopen saved transcripts and notes. |
| CAP-02 | Reliable audio capture | Start/stop recording, show recording and persistence states, detect interruption, retry pending uploads, and disclose unrecoverable gaps. |
| TRN-01 | Timestamped transcription | Produce ordered transcript segments, handle domain terminology, distinguish provisional and finalized text, and identify uncertain content. |
| NOTE-01 | Detailed note generation | Meet the content-preservation requirements in Section 3 using coherent topic organization. |
| NOTE-02 | Live and final notes | Show incremental notes during the lecture and produce a refined version after all available audio is accounted for. Preserve usable live output if finalization fails. |
| NOTE-03 | Note preferences | Provide a detailed default and a small set of depth/format preferences. Preferences must not permit fabricated attribution or silently destroy the detailed version. |
| SRC-01 | Source inspection | Link lecture-derived notes to the relevant versioned transcript span and retained audio interval. Keep AI explanations visibly separate. |
| EDIT-01 | Correction and regeneration | Allow transcript and note edits. Preserve student edits and earlier versions when applying regenerated material, and flag dependent content affected by source corrections. |
| OUT-01 | Save and export | Persist notes and provide a readable export. Markdown is the proposed initial format; define portable source-reference behavior in Phase 2. |
| PRIV-01 | Basic privacy and deletion | Make processing location explicit, protect access to course content, and support deletion of lectures and their derived data. Define retention and recovery behavior before implementation. |

### Secondary features, after the core path works

- **Catch Me Up:** A concise, source-linked explanation of the recent topic transition and current discussion. It should reuse the reliable transcript/note pipeline.
- **Mark Important:** A low-interaction timestamp marker that influences final note review and organization.
- **Course terminology input:** A simple glossary or supplied terms may improve transcription without requiring a complete document retrieval system.

These remain desired features but must not delay proving that the core system produces useful notes.

### Deferred features

- Practice questions, flashcards, mastery estimates, spaced review, and adaptive learning.
- Full syllabus intelligence, semester-wide retrieval, and extensive concept graphs.
- Phone pairing, automatic slide alignment, and board-image interpretation.
- Numerous provider integrations, broad multilingual support, native mobile applications, and collaborative workspaces.
- Kubernetes, autoscaling, GitOps, CDC, and the full observability suite as release requirements.

Course documents and visual capture can move earlier if the initial evaluation domain requires them for accurate notes. Until then, visual-only content is an explicit limitation: a transcript cannot recover a diagram or an unspoken equation. Notes must say when the available evidence is insufficient.

## 5. Student journey

1. Select a course and create a lecture; choose a note depth/format and the supported processing mode.
2. Check microphone input and start recording with clear capture and save indicators.
3. Receive timestamped transcript and incremental notes while interacting as little as possible.
4. If processing or connectivity is interrupted, see whether recording continues, what is saved, and what remains pending.
5. Stop recording; see upload completion and finalization progress rather than an immediate, potentially incomplete final result.
6. Review the detailed final notes, follow uncertain statements to their sources, and correct mistakes.
7. Save or export the notes and reopen them later for study.

Phase 2 will specify the screens, accessibility needs, edit interactions, and recovery flows behind this journey.

## 6. Trust and recovery requirements

- Recording status, local persistence, server persistence, and AI processing are separate states. The product must not imply that one guarantees the others.
- Define a durable acknowledgement in Phase 3. It must cover retrievable audio and associated metadata, not just receipt of an HTTP request.
- Retain pending captured audio until durable acknowledgement or an explicit user deletion, subject to disclosed device storage limits. Detect interruption and mark gaps; do not promise capture while the device is asleep or the microphone is unavailable.
- Preserve available audio when transcription fails, the transcript when note generation fails, and usable notes when final refinement fails.
- Track source and note revisions so final transcription corrections do not silently invalidate citations or overwrite student work.
- Audio replay is available only while the source audio is retained. Deletion must clearly explain which verification and regeneration capabilities will become unavailable.
- Never move course data to a cloud provider as an undisclosed fallback. Treat uploaded and transcribed content as evidence, not privileged instructions.

## 7. Proposed quality gates

These are initial evaluation targets, not measured performance claims or guarantees. Phase 4 must calibrate them against human-reviewed fixtures and record any changes with reasons.

Before model output is reviewed, annotate each fixture with key content items, critical items, terminology, source intervals, and known ambiguity. Include definitions, examples, reasoning, qualifications, and professor corrections. Include a full lecture and difficult excerpts involving noise, rapid delivery, and visual references.

| Area | Proposed acceptance gate | Evaluation method |
| --- | --- | --- |
| Detail coverage | Preserve at least 90% of annotated key items and every recoverable critical item in final detailed notes. | A human reviewer maps reference items to note blocks; missing evidence is evaluated separately from omitted available evidence. |
| Faithfulness | No unflagged critical factual errors or fabricated professor attributions in the release fixtures. | Review for errors that change meaning, such as reversed negation, incorrect conditions, or altered algorithm steps. |
| Citation resolution | Every lecture-derived note block has a resolvable transcript source; replay resolves when audio is retained. | Check identifiers, versions, and intervals, then inspect the displayed source. |
| Citation support | At least 95% of reviewed lecture-derived claims are supported by the cited spans, with no unsupported critical claims. | Human claim-level review; a valid link alone does not count as support. |
| Transcription | Report overall word error rate, domain-term accuracy, and meaning-changing errors separately. | Compare against manually corrected reference audio/transcript; set numeric transcription thresholds after baseline measurement. |
| Organization | A reviewer can find each annotated major topic and its associated examples without searching the full transcript. | Perform topic-finding tasks and record failed or confusing organization. |
| Capture integrity | No silently missing acknowledged audio in the tested failure scenarios; every detected capture gap is visible. | Compare recording manifests, stored audio, and UI state after network interruption, retry, refresh, and worker restart. |
| Editing safety | Regeneration preserves student changes or presents an explicit conflict; it never silently overwrites them. | Correct a transcript and note, regenerate, and compare versions and citations. |
| Endurance | Process the complete 45–60 minute fixture without unexplained ordering loss, duplication, or incomplete finalization. | Run on declared hardware and report recovery behavior and resource use. |

Record user-visible transcript delay, note delay, finalization time, and correction effort in addition to correctness. Define timing endpoints and hardware before selecting latency thresholds; the original three-second targets remain unvalidated proposals.

The main usability measure is how much correction and reorganization a student needs before studying from the notes. Start by recording correction time and edit categories. Evaluate delayed learning outcomes later; this phase makes no claim that note generation alone improves retention.

## 8. Engineering scope

The production engineering portfolio remains a project goal. During the first release, prioritize only the infrastructure needed for capture durability, asynchronous processing, recovery, source integrity, and useful diagnostics.

The original Next.js, FastAPI, PostgreSQL, Kafka, object storage, and local model choices are architecture candidates to reconcile in Phase 3. This phase does not mandate removing Kafka or replacing the existing proposed stack. Advanced orchestration and scaling experiments follow a working note-taking workflow.

## 9. Open decisions and next owners

| Decision | Current position | Resolve in |
| --- | --- | --- |
| Initial course and language | Technical course and English are working assumptions. | Phase 2, before choosing evaluation fixtures. |
| Note formats and depth controls | Detailed is the default; exact controls remain open. | Phase 2. |
| Export and retained source behavior | Markdown proposed; source links need a defined portable representation. | Phase 2. |
| Supported hardware and browsers | Not yet established; no minimum hardware claim. | Phase 3. |
| Local-only versus optional cloud execution | Local development and a self-hosted path are preferred; supported model configurations need measurement. | Phases 3–4. |
| Storage limits, retention, and interruption recovery | Must be explicit before capture implementation. | Phase 3. |
| Need for slides or visual input in the first release | Deferred unless the selected course cannot meet note-quality gates without them. | Phase 4, before the final backlog. |
| Performance and quality thresholds | Section 7 contains proposed gates; latency and transcription thresholds need baseline data. | Phase 4. |

## 10. Phase 1 completion boundary

Phase 1 delivers a written product priority, initial audience, first-release scope, note-quality definition, proposed acceptance gates, deferred scope, and assigned open decisions.

It does not deliver application code, a final architecture, validated model quality, or proven performance. Phase 2 translates this baseline into a concrete student experience; Phase 5 consolidates the original documents after the design and evaluation decisions are made.
