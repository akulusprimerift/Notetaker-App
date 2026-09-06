# Multimodal Academic Learning System
## Product + Technical Specification

**Version:** 0.2  
**Status:** Architecture / implementation blueprint  
**Primary product loop:** **Capture → Understand → Practice → Measure → Personalize**  
**Primary interface:** AI lecture note-taking and learning companion  
**Deployment philosophy:** Local-first development, production-inspired infrastructure, fully containerized

---

# 1. Executive Summary

This project is a **multimodal academic learning system** whose primary user-facing entry point is a live AI lecture note-taking application. The purpose is not to make it easier for students to ignore class. The purpose is to reduce the cost of re-engaging with classes that are boring, poorly delivered, overly dependent on PowerPoint, visually dense, too fast, or otherwise difficult to follow.

The system captures lecture audio, performs live speech-to-text, creates structured notes in a student-defined style, incorporates uploaded course materials, accepts board/screen photos from a paired phone, and preserves source provenance so students can distinguish professor-derived content from course-material-derived context and AI-generated explanation.

The note-taking layer feeds a larger learning loop:

1. **Capture** — collect lecture evidence and course context.
2. **Understand** — build structured notes and alternative explanations.
3. **Practice** — create active-recall and application questions.
4. **Measure** — collect evidence of understanding from student behavior.
5. **Personalize** — adapt future notes, explanations, and review priorities.

The implementation is intentionally **production-inspired**. A single local student does not require distributed event streaming, Kubernetes, autoscaling, distributed tracing, or schema registries; however, the project deliberately uses these systems where they can perform real architectural work so the project demonstrates production-relevant software engineering skills.

Core platform technologies:

- **Frontend:** Next.js + TypeScript
- **Backend:** FastAPI + Python
- **Realtime:** WebSockets
- **Event streaming:** Apache Kafka
- **Schema registry:** Apicurio Registry
- **Kafka inspection:** Kafbat UI
- **Relational data:** PostgreSQL
- **Vector search:** pgvector
- **Ephemeral state/cache:** Valkey
- **Object storage:** SeaweedFS
- **Local LLM/VLM runtime:** Ollama
- **Local STT:** faster-whisper
- **Telemetry:** OpenTelemetry
- **Metrics:** Prometheus
- **Dashboards:** Grafana
- **Logs:** Loki
- **Traces:** Tempo
- **Alerting:** Alertmanager
- **Error tracking:** GlitchTip
- **Load testing:** k6
- **Containers:** Docker
- **Local Kubernetes:** k3d / k3s
- **Kafka on Kubernetes:** Strimzi
- **Event-driven autoscaling:** KEDA
- **Kubernetes packaging:** Helm
- **Optional GitOps:** Argo CD
- **Optional CDC/outbox evolution:** Debezium

The final project should demonstrate both **applied AI engineering** and **distributed systems / platform engineering** without losing sight of the original product problem: helping a student preserve, understand, and retain lecture material.

---

# 2. Product Philosophy

## 2.1 The problem

Students often fail to extract meaningful value from lectures for reasons that are not solved by ordinary transcription software:

- a professor reads directly from slides;
- a lecture is monotone or disengaging;
- important material is mentioned once verbally;
- the professor assumes prerequisite knowledge;
- equations, diagrams, or code are written on a board but never appear in the slide deck;
- the professor says “this right here” while pointing at a visual;
- the student loses focus for several minutes and cannot identify the transition that occurred;
- technical vocabulary is mis-transcribed;
- generic summarizers remove examples or nuance;
- generated notes do not indicate what the professor actually said;
- the student leaves class with notes but does not retain the information.

## 2.2 Product promise

> If a lecture is difficult to follow, the student should still leave with an accurate, source-linked record of what happened and a short path toward understanding it.

## 2.3 Anti-goal

The application should **not** be marketed or designed around:

> “You do not need to pay attention because the AI will do the class for you.”

Instead:

> “If you miss something, lose focus, or receive a weak explanation, the system makes it easy to recover and learn the material.”

## 2.4 Core design principle

The AI should never remove the student's need to think. It should remove unnecessary friction around thinking.

## 2.5 Trust principle

The application must not blur:

- what the professor said;
- what a course document stated;
- what the AI inferred;
- what the AI added as an explanation.

This is a foundational product rule, not a cosmetic feature.

---

# 3. Product Loop: Capture → Understand → Practice → Measure → Personalize

## 3.1 Capture

Capture all evidence relevant to a lecture:

- live microphone audio;
- live transcript;
- uploaded lecture slides;
- syllabus;
- homework;
- readings;
- textbook excerpts;
- prior lecture notes;
- student-marked important moments;
- board/screen photos;
- slide alignment;
- lecture timestamps.

## 3.2 Understand

Convert raw evidence into:

- topic-structured notes;
- definitions;
- examples;
- equations;
- code snippets;
- professor emphasis;
- course-context links;
- prerequisites;
- alternative explanations;
- source provenance.

## 3.3 Practice

Generate:

- active-recall questions;
- application problems;
- “explain in your own words” prompts;
- analogies;
- worked examples;
- similar practice questions;
- short post-lecture review sessions.

## 3.4 Measure

Collect evidence such as:

- correctness;
- question difficulty;
- hints used;
- retries;
- repeated mistakes;
- response latency;
- review spacing;
- application performance;
- confidence ratings where useful.

## 3.5 Personalize

Use the evidence to adjust:

- note density;
- explanation depth;
- prerequisite reminders;
- practice frequency;
- review priority;
- teaching style;
- concept resurfacing.

---

# 4. User Experience

## 4.1 Before class

The student selects a course and creates/opens a lecture session.

Optional inputs:

- syllabus;
- today's slide deck;
- homework;
- readings;
- professor review sheet;
- prior notes;
- textbook excerpts.

The user chooses:

- a **Note Profile**;
- a **Model Profile**;
- privacy mode;
- optional lecture-specific instructions.

## 4.2 Note Profiles

A Note Profile defines how notes should be produced.

Example:

**Name:** CS Detailed

**Instructions:**

- use hierarchical headings;
- preserve algorithms and code examples;
- include Big-O complexity;
- preserve exact definitions;
- flag anything the professor indicates may appear on an exam;
- preserve equations;
- keep examples with the relevant concept;
- add AI explanations only in separately labeled sections;
- include timestamp/source provenance.

Built-in profiles may include:

- Cornell Notes;
- Detailed;
- Minimal;
- Exam Focused;
- Computer Science;
- Math / Equation Heavy;
- Law;
- Pre-Med;
- Custom.

## 4.3 Prompt hierarchy

The effective note prompt should be assembled in layers:

1. system constraints;
2. global user learning preference;
3. course-specific note prompt;
4. lecture-specific prompt;
5. current transcript/topic context;
6. retrieved course context;
7. visual context;
8. provenance requirements;
9. structured output schema.

## 4.4 Model Profiles

Normal users should see simple choices:

- Recommended;
- Fully Local;
- Hybrid;
- Cloud.

Advanced users may independently select:

- STT provider/model;
- note-generation provider/model;
- vision provider/model;
- embedding provider/model.

Example fully local configuration:

- STT: faster-whisper;
- Notes: Ollama + selected model;
- Vision: Ollama multimodal model;
- Embeddings: local embedding model.

## 4.5 Live lecture UI

The live UI should be deliberately low-interaction.

Primary controls:

- Start / Stop;
- Catch Me Up;
- Mark Important;
- Pair Phone;
- Board Capture;
- Transcript status.

The user should **not** need to manipulate infrastructure, prompts, or models during class.

## 4.6 Catch Me Up

When a student zones out, Catch Me Up should answer:

- what topic was previously being discussed;
- what important transition occurred;
- what concept is being discussed now;
- what minimum background is needed to rejoin;
- what slide/visual is currently relevant.

It should be intentionally concise.

Example:

> Earlier: Binary Search Trees can become unbalanced.  
> Then: the professor introduced AVL trees as a solution.  
> Now: the professor is showing how rotations restore balance.  
> You need to know: balance factor = left height - right height.

## 4.7 Mark Important

When pressed, store:

- lecture ID;
- timestamp;
- current topic;
- current slide candidate;
- transcript window around the timestamp;
- optional visual context.

The marked region gets higher priority in final notes and review generation.

## 4.8 Paired phone capture

The desktop lecture session displays a QR code or pairing token.

The phone opens a lightweight web page associated with the active lecture.

Phone UI:

- course / lecture name;
- active recording indicator;
- large Capture button;
- previous capture thumbnail.

No complex configuration should be required.

## 4.9 Post-lecture experience

After lecture, the student receives:

- refined transcript;
- final structured notes;
- source provenance;
- professor-emphasized concepts;
- AI-added explanations;
- identified concepts;
- weak/uncertain areas;
- short active-recall review;
- optional “Teach This Better” actions.

---

# 5. Trust, Provenance, and Evidence

## 5.1 Why provenance is mandatory

AI notes can create a serious failure mode if generated explanations are mistaken for something the professor stated.

Each note block must retain evidence.

## 5.2 Provenance source types

- transcript;
- lecture audio;
- slide;
- board image;
- homework;
- reading/textbook;
- previous lecture;
- AI explanation.

## 5.3 Example note rendering

**Lecture**  
AVL trees maintain a balance factor between -1 and +1.  
Source: 31:44–32:05

**Course material**  
Slide 14 defines the balance factor as h(left) - h(right).

**AI explanation**  
The balance factor tells us which side of the tree is taller and therefore which rotation may be required.

## 5.4 Raw vs derived data

Raw evidence should be immutable or append-only whenever practical:

- audio chunks;
- full recording;
- original transcript segments;
- uploaded documents;
- board images.

Derived artifacts can be regenerated:

- corrected transcript;
- topic segments;
- notes;
- concepts;
- embeddings;
- flashcards;
- summaries;
- mastery state.

---

# 6. High-Level Architecture

```text
                              ┌──────────────────────┐
                              │      NEXT.JS UI      │
                              │ web + phone capture  │
                              └──────────┬───────────┘
                                         │ REST / WebSocket
                              ┌──────────▼───────────┐
                              │ API + REALTIME GATE  │
                              │ FastAPI / WebSockets │
                              └──────────┬───────────┘
                                         │ domain events
                         ┌───────────────▼────────────────┐
                         │         APACHE KAFKA           │
                         │ topics + consumer groups       │
                         │ + Apicurio schema registry     │
                         └──────┬──────┬──────┬──────┬───┘
                                │      │      │      │
               ┌────────────────┘      │      │      └────────────────┐
               ▼                       ▼      ▼                       ▼
        ┌────────────┐          ┌──────────┐ ┌──────────┐      ┌────────────┐
        │ STT WORKER │          │ NOTE     │ │ VISION   │      │ STUDY      │
        │ Whisper    │          │ WORKER   │ │ WORKER   │      │ WORKER     │
        └─────┬──────┘          └────┬─────┘ └────┬─────┘      └─────┬──────┘
              │                      │            │                  │
              └──────────────┬───────┴────────────┴──────────┬───────┘
                             ▼                               ▼
                    ┌──────────────────┐             ┌──────────────────┐
                    │ PostgreSQL       │             │ SeaweedFS        │
                    │ + pgvector       │             │ audio/images/PDF │
                    └───────┬──────────┘             └──────────────────┘
                            │
                    ┌───────▼──────────┐
                    │ Valkey           │
                    │ buffers/cache/   │
                    │ locks/sessions   │
                    └──────────────────┘
```

AI provider plane:

- faster-whisper;
- Ollama;
- local embeddings;
- optional external providers behind the same interfaces.

Observability plane:

- OpenTelemetry;
- Prometheus;
- Grafana;
- Loki;
- Tempo;
- Alertmanager;
- GlitchTip.

Orchestration plane:

- Docker Compose;
- k3d/k3s;
- Kubernetes;
- Strimzi;
- KEDA;
- Helm;
- Argo CD later.

---

# 7. AI Provider Architecture

## 7.1 Independent model roles

The system has four primary model roles:

1. speech recognition;
2. note/reasoning generation;
3. vision-language analysis;
4. embeddings.

One provider does not need to provide all four.

## 7.2 Internal provider contracts

```python
class SpeechProvider:
    async def transcribe_chunk(self, audio_ref, context): ...
    async def finalize_lecture(self, lecture_ref): ...

class NoteModelProvider:
    async def generate_structured(self, messages, schema, settings): ...

class VisionProvider:
    async def analyze(self, image_ref, context): ...

class EmbeddingProvider:
    async def embed(self, texts): ...
```

Provider-specific details stay in provider modules.

The frontend talks only to application APIs.

## 7.3 Fully local path

```text
Microphone
 → SeaweedFS/local object store
 → faster-whisper
 → Ollama
 → local embeddings
 → PostgreSQL + pgvector
 → live/final notes
```

## 7.4 Hybrid path

Examples:

- local STT + cloud note model;
- cloud realtime STT + local Ollama note model;
- local note model + cloud vision model.

The system should clearly display which data is sent to an external provider.

---

# 8. Live Speech-to-Text

## 8.1 Classroom constraints

STT must account for:

- speaker distance;
- HVAC;
- coughing;
- neighboring students;
- professor facing away;
- technical vocabulary;
- acronyms;
- equations;
- names;
- code.

## 8.2 Initial local model

Use **faster-whisper** as the first implementation baseline.

The architecture must remain provider-agnostic.

## 8.3 Audio chunking

Initial live transport chunk target:

- roughly 1–5 seconds.

Each chunk stores:

- lecture_id;
- chunk_id;
- sequence;
- start_ms;
- end_ms;
- object_key;
- checksum;
- format;
- sample_rate.

## 8.4 Live vs final transcription

### Live
Optimizes for:

- latency;
- timestamps;
- continuity;
- responsive UI.

### Final
Optimizes for:

- accuracy;
- terminology correction;
- complete punctuation;
- topic coherence.

The final transcript can replace/correct live segments while preserving revision history if desired.

## 8.5 Course-aware terminology

Before lecture, extract likely terms from:

- today's slides;
- syllabus;
- previous lecture;
- homework;
- glossary;
- readings.

Use these terms for:

- STT hints when supported;
- correction passes;
- acronym normalization;
- technical spell checking.

---

# 9. Topic Segmentation and Note Buffers

## 9.1 Do not segment by arbitrary clock windows

A professor may spend seven minutes developing one concept.

Do not treat every 30-second window as an independent note section.

## 9.2 Topic state

A topic may be:

- tentative;
- active;
- transitioning;
- completed.

## 9.3 Rolling buffer

Maintain recent transcript in Valkey or application memory.

The note worker consumes meaningful transcript windows plus topic state.

## 9.4 Note delta operations

Potential delta operations:

- append key point;
- update definition;
- attach example;
- add equation;
- add professor emphasis;
- attach source;
- attach visual;
- close topic;
- add AI explanation.

The entire note document should not be regenerated every few seconds.

---

# 10. Final Note Generation

After lecture:

1. finalize transcript;
2. correct terminology;
3. finalize topic segmentation;
4. align slides;
5. align board captures;
6. retrieve relevant course context;
7. apply Note Profile;
8. regenerate clean final notes;
9. preserve source links;
10. extract concepts;
11. generate post-lecture review.

Final notes are a **derived artifact** and can be regenerated later using better models.

---

# 11. Course Context and RAG

## 11.1 Supported course inputs

- syllabus;
- slides;
- homework;
- instructor solutions when provided;
- readings;
- review sheets;
- textbook excerpts;
- prior notes;
- previous lecture transcripts.

## 11.2 Document ingestion

```text
Upload
 → object storage
 → document.uploaded event
 → parser
 → semantic chunking
 → metadata extraction
 → embedding generation
 → pgvector
 → document.indexed event
```

## 11.3 Chunking rules

Prefer meaningful boundaries:

- slide;
- heading;
- subsection;
- theorem;
- code block;
- homework question;
- page section;
- table.

Avoid blind fixed-character chunking as the only strategy.

## 11.4 Chunk metadata

- course_id;
- document_id;
- document_type;
- page;
- slide;
- section;
- date;
- lecture number;
- assignment number;
- topic labels.

## 11.5 Retrieval

Use a hybrid retrieval process:

1. hard-filter by course;
2. vector similarity;
3. document-type relevance;
4. date / lecture relevance;
5. keyword relevance if useful;
6. optional re-ranking.

Never retrieve unrelated course context.

## 11.6 Do not dump the semester into context

The model should receive only relevant chunks.

Large indiscriminate prompts are slower, more expensive, and can reduce answer quality.

---

# 12. Syllabus Intelligence

The syllabus should be parsed into structured course metadata.

Potential fields:

- course title;
- professor;
- meeting schedule;
- office hours;
- exam dates;
- exam weight;
- assignment weight;
- course schedule;
- topic sequence;
- grading rules;
- course resources;
- academic integrity policy.

This allows features such as:

- upcoming exam reminders;
- exam-relevant concept grouping;
- lecture topic expectations;
- course navigation.

---

# 13. Homework and Assignment Context

Homework is useful as **learning context**, not only as a source of answers.

Preferred interactions:

- “What concepts do I need before attempting Homework 3?”
- “Which lecture covered this?”
- “Why is my approach incorrect?”
- “Give me a similar problem.”
- “Explain the prerequisite concept without solving the assignment for me.”

The application can retrieve homework questions to understand what material the course expects the student to apply.

The system does not need to be designed around producing submission-ready homework answers.

---

# 14. Multimodal Vision

## 14.1 Why the camera matters

Audio alone cannot recover:

- equations on a board;
- diagrams;
- code;
- graphs;
- annotations;
- professor pointing at a specific element.

A board image is therefore a context source, not merely an OCR target.

## 14.2 Board capture pipeline

```text
Phone capture
 → upload image
 → visual.capture.uploaded
 → vision consumer group
 → classify visual
 → extract structured content
 → align to transcript
 → align to slide
 → visual.capture.analyzed
 → enrich notes
```

## 14.3 Visual output object

```json
{
  "kind": "whiteboard_diagram",
  "topic": "AVL rotations",
  "contains_equation": true,
  "contains_code": false,
  "importance": 0.91,
  "extracted_text": "...",
  "structured_summary": "...",
  "relationships": [],
  "timestamp_ms": 2244000
}
```

## 14.4 Visual modes

### Equation
Focus on:

- mathematical symbols;
- variable identity;
- structure;
- optional LaTeX conversion.

### Code
Focus on:

- indentation;
- exact identifiers;
- syntax;
- programming language.

### Diagram
Focus on:

- relationships;
- direction;
- arrows;
- labels;
- hierarchy.

### Chart
Focus on:

- axes;
- series;
- units;
- trends;
- labels;
- comparisons.

### Slide
Focus on:

- title;
- bullets;
- figures;
- current lecture explanation;
- matching uploaded slide.

---

# 15. Slide Alignment

## 15.1 Goal

When the professor says:

> “Notice what happens right here.”

The system should have a candidate visual context for “right here.”

## 15.2 Slide preprocessing

Each slide becomes a structured retrievable unit containing:

- slide ID;
- slide number;
- title;
- extracted text;
- rendered slide image;
- embedding;
- detected figures;
- speaker notes when available.

## 15.3 Runtime alignment

Score candidate slides using:

- transcript semantic similarity;
- active topic similarity;
- previous slide index;
- slide-order continuity;
- visual similarity if a phone image is available.

Store:

- slide_id;
- confidence;
- aligned start time;
- aligned end time.

---

# 16. Learning Engine

## 16.1 Concepts as first-class entities

The application should gradually operate on concepts rather than only documents.

Examples:

- Binary Search Tree;
- Balance Factor;
- AVL Rotation;
- Dijkstra's Algorithm;
- Edge Relaxation.

## 16.2 Concept edges

Potential relationship types:

- prerequisite_of;
- related_to;
- contrasts_with;
- example_of;
- used_in;
- derived_from.

## 16.3 Concept occurrence

A concept occurrence records where a concept appeared:

- lecture;
- timestamp;
- slide;
- homework;
- note block.

This supports later queries such as:

- “When was this first introduced?”
- “Where did the professor explain this?”
- “Show all diagrams related to this concept.”

---

# 17. Teach This Better

A student should be able to ask the application to improve a poor explanation.

Pipeline:

```text
Selected concept / note block
 → retrieve lecture evidence
 → retrieve course material
 → retrieve prerequisites
 → identify missing explanation
 → generate alternate teaching path
 → analogy
 → example
 → check-for-understanding question
```

The output must clearly label AI-added material.

The application should not rewrite history by making it appear that the professor gave the improved explanation.

---

# 18. Practice

## 18.1 Post-lecture review

A short review can include:

- 3 recall questions;
- 2 application questions;
- 1 explain-in-your-own-words prompt;
- 1 review of a weak concept.

The review should be short enough that a student can realistically complete it after class.

## 18.2 Practice item fields

A PracticeItem may store:

- concept_id;
- source lecture;
- question type;
- prompt;
- expected answer rubric;
- difficulty;
- generated_by_model;
- provenance;
- version.

## 18.3 Practice types

- free response;
- multiple choice;
- short calculation;
- code tracing;
- explanation;
- compare/contrast;
- diagram labeling;
- worked example continuation.

---

# 19. Measuring Learning

## 19.1 Do not pretend mastery is directly observable

The application should never say it knows exactly what a student retained.

It should estimate mastery from evidence.

## 19.2 Potential signals

- correct/incorrect;
- partial correctness;
- difficulty;
- hint usage;
- number of retries;
- response time;
- repeated misconception;
- time since last exposure;
- spaced review performance;
- application performance;
- student confidence.

## 19.3 MVP mastery model

Start with a transparent weighted heuristic.

Do not begin with a black-box ML model.

Example conceptual behavior:

- correct difficult response: strong positive signal;
- repeated correct responses over multiple days: stronger positive signal;
- hint-dependent success: smaller positive signal;
- repeated same misconception: negative signal;
- failure after long forgetting interval: expected negative signal, but not catastrophic.

## 19.4 Later research directions

Potential later experiments:

- Bayesian Knowledge Tracing;
- Item Response Theory;
- forgetting-curve models;
- Deep Knowledge Tracing;
- spaced-repetition scheduling.

These are later enhancements, not core architecture requirements.

---

# 20. Personalized Notes

Personalization should affect note generation over time.

If a concept is strongly mastered:

- condense repetitive review;
- retain professor emphasis;
- preserve source links;
- avoid removing new examples.

If a concept is weak:

- expand explanation;
- retrieve prerequisites;
- include additional examples;
- add a review prompt;
- surface related prior lecture material.

Personalization must never erase important lecture content silently.

---

# 21. Event-Driven Architecture

## 21.1 Why Kafka is used

Several workloads are naturally asynchronous:

- STT;
- note generation;
- document parsing;
- embedding generation;
- visual analysis;
- finalization;
- concept extraction;
- practice generation.

Kafka allows the realtime API to accept work without synchronously waiting for expensive inference.

## 21.2 Kafka is not the database

Kafka stores event streams.

PostgreSQL remains the application system of record.

Object storage retains binary evidence.

## 21.3 Do not place binary objects in Kafka

Correct:

```text
Browser → SeaweedFS → object key → Kafka event
```

Incorrect:

```text
Browser → 5 MB binary payload inside Kafka message
```

---

# 22. Kafka Topic Design

Suggested topics are domain-oriented.

## 22.1 Lecture

- lecture.started
- lecture.stopped
- lecture.finalization.requested
- lecture.finalized

## 22.2 Audio

- audio.chunk.uploaded
- audio.chunk.ready
- audio.chunk.failed

## 22.3 Transcript

- transcript.segment.created
- transcript.segment.corrected
- transcript.finalized

## 22.4 Topic

- topic.segment.started
- topic.segment.updated
- topic.segment.completed

## 22.5 Context

- context.retrieval.requested
- context.retrieved

## 22.6 Notes

- notes.delta.requested
- notes.delta.generated
- notes.block.updated
- notes.finalization.requested
- notes.finalized

## 22.7 Documents

- document.uploaded
- document.parse.requested
- document.parsed
- document.embedding.requested
- document.embedded
- document.indexed

## 22.8 Visual

- visual.capture.uploaded
- visual.capture.analyzed
- slide.aligned

## 22.9 Learning

- concept.detected
- practice.generated
- practice.attempted
- mastery.updated

## 22.10 Reliability

- retry topics where needed;
- dead-letter topics per major workflow.

---

# 23. Kafka Event Envelope

All events should share a common envelope.

```json
{
  "event_id": "uuid",
  "event_type": "audio.chunk.ready",
  "schema_version": 1,
  "occurred_at": "2026-09-05T19:00:00Z",
  "producer": "realtime-gateway",
  "trace_id": "...",
  "correlation_id": "...",
  "user_id": "...",
  "course_id": "...",
  "lecture_id": "...",
  "payload": {}
}
```

Benefits:

- consistent tracing;
- consistent debugging;
- easier schema tooling;
- easier DLQ replay;
- stronger event contracts.

---

# 24. Kafka Partitioning and Ordering

## 24.1 Lecture events

Use:

`partition key = lecture_id`

This preserves ordering for one lecture.

Example:

```text
Partition 2
Lecture A:
chunk 1 → chunk 2 → chunk 3 → transcript 1 → transcript 2
```

A different lecture may be processed on another partition.

## 24.2 Document events

Use:

`partition key = document_id`

when ordering within document ingestion matters.

## 24.3 Important limitation

Kafka ordering is guaranteed **within a partition**, not globally.

Do not claim total global ordering.

---

# 25. Kafka Consumer Groups

Suggested consumer groups:

- stt-workers;
- note-workers;
- vision-workers;
- document-workers;
- context-workers;
- study-workers;
- outbox-publisher.

Benefits:

- independent horizontal scaling;
- worker isolation;
- visible consumer lag;
- clear ownership of workflows.

---

# 26. Schema Registry

Use **Apicurio Registry**.

Recommended initial format: **Protobuf**.

Benefits:

- typed event contracts;
- schema versioning;
- compatibility checks;
- easier generated types;
- safer consumer evolution.

Example:

```proto
message TranscriptSegmentCreated {
  string event_id = 1;
  string lecture_id = 2;
  string segment_id = 3;
  int64 sequence = 4;
  int64 start_ms = 5;
  int64 end_ms = 6;
  string text = 7;
  float confidence = 8;
}
```

CI should include schema compatibility tests.

---

# 27. Delivery Semantics and Idempotency

## 27.1 Delivery model

Design for **at-least-once delivery**.

Do not make unsupported “exactly once everywhere” claims.

## 27.2 Idempotent consumers

Every event has an event_id.

Consumers should avoid duplicate side effects using one or more of:

- unique event_id table;
- deterministic entity keys;
- database upsert;
- unique constraints;
- processed_events table.

## 27.3 Example

If `audio.chunk.ready` is delivered twice, the same transcript segment must not be inserted twice.

---

# 28. Retry and Dead-Letter Topics

## 28.1 Error categories

### Transient
Examples:

- Ollama temporarily unavailable;
- storage timeout;
- database contention;
- network interruption.

### Permanent
Examples:

- invalid schema;
- corrupted file;
- missing required object;
- unsupported file type.

## 28.2 Retry

Use bounded exponential backoff.

Do not retry forever.

## 28.3 DLQ

Example:

`stt.dlq`

DLQ record should preserve:

- original event;
- failure classification;
- exception reference;
- retry count;
- failed_at.

DLQ count should appear on dashboards and trigger alerts.

---

# 29. PostgreSQL Data Model

PostgreSQL is the system of record.

Suggested tables:

## Identity / settings

- users
- note_profiles
- model_profiles

## Course

- courses
- course_memberships
- course_documents
- document_chunks

## Lecture

- lectures
- audio_assets
- transcript_segments
- topic_segments
- visual_captures
- slide_alignments

## Notes

- note_documents
- note_blocks
- provenance_links

## Learning

- concepts
- concept_edges
- concept_occurrences
- practice_items
- practice_attempts
- mastery_events

## Reliability

- outbox_events
- processed_events

---

# 30. Suggested Database Relationships

```text
USER
 ├── NoteProfile
 ├── ModelProfile
 └── Course
      ├── CourseDocument
      │    └── DocumentChunk ─── embedding
      ├── Lecture
      │    ├── AudioAsset
      │    ├── TranscriptSegment
      │    ├── VisualCapture
      │    ├── TopicSegment
      │    ├── NoteDocument
      │    │    └── NoteBlock
      │    │         └── ProvenanceLink
      │    └── ConceptOccurrence
      └── Concept
           ├── ConceptEdge
           ├── PracticeItem
           └── MasteryEvent
```

---

# 31. Database Indexing

Initial relational indexes:

- transcript_segments(lecture_id, sequence)
- topic_segments(lecture_id, start_ms)
- note_blocks(note_document_id, position)
- document_chunks(course_id, document_id)
- practice_attempts(user_id, concept_id, attempted_at)
- mastery_events(user_id, concept_id, created_at)
- outbox_events(published_at)
- processed_events(event_id UNIQUE)

Add vector indexes only after the dataset is large enough to justify approximate nearest-neighbor search.

---

# 32. pgvector

Use pgvector instead of introducing a separate vector database initially.

Vectorized records may include:

- document chunks;
- topic segments;
- note blocks;
- concept descriptions.

Benefits:

- one data platform;
- transactional metadata near vectors;
- simpler local development;
- fewer infrastructure dependencies.

A separate vector database can be reconsidered only if measurements justify it.

---

# 33. Valkey

Valkey stores **ephemeral** state.

Candidate keys:

```text
lecture:{id}:active_topic
lecture:{id}:recent_transcript
lecture:{id}:connected_devices
lecture:{id}:slide_candidate
ws:{user_id}:connections
rate:{user_id}:{route}
lock:lecture:{id}:finalize
```

Valkey must not become the source of truth.

If it disappears, critical state should be recoverable from Kafka/Postgres where practical.

---

# 34. SeaweedFS Object Storage

Store:

- live audio chunks;
- full lecture recording;
- board images;
- slide images;
- PDFs;
- presentation files;
- generated export assets.

Example object path:

```text
courses/{course_id}/lectures/{lecture_id}/audio/{sequence}.webm
```

Kafka events reference object keys.

---

# 35. Transactional Outbox

## 35.1 The problem

Sequence:

1. insert transcript into PostgreSQL;
2. publish `transcript.segment.created` to Kafka.

If step 1 succeeds and step 2 fails, the database and event stream disagree.

## 35.2 The solution

Within one Postgres transaction:

- insert transcript;
- insert outbox event;
- commit.

A publisher asynchronously publishes pending outbox rows.

## 35.3 Later Debezium path

Later:

```text
PostgreSQL WAL
 → Debezium
 → Kafka
```

This is an advanced phase, not a launch requirement.

---

# 36. Backend Structure

## 36.1 Modular monolith first

Do not split every concept into a microservice.

Recommended first architecture:

- FastAPI API application;
- optional separate realtime gateway;
- multiple worker processes;
- strongly separated internal modules.

This provides production-like asynchronous boundaries without unnecessary network complexity.

## 36.2 API responsibilities

- auth;
- courses;
- lectures;
- documents;
- note profiles;
- model profiles;
- notes;
- study sessions;
- phone pairing;
- deletion/retention controls.

## 36.3 Realtime responsibilities

- active lecture session;
- WebSocket connections;
- live transcript delivery;
- live note delta delivery;
- topic updates;
- capture notifications;
- Catch Me Up responses.

---

# 37. Representative REST API

## Courses

```text
POST   /courses
GET    /courses/:id
PATCH  /courses/:id
DELETE /courses/:id

POST   /courses/:id/documents
GET    /courses/:id/documents
GET    /courses/:id/concepts
```

## Lectures

```text
POST   /lectures
POST   /lectures/:id/start
POST   /lectures/:id/stop
GET    /lectures/:id
GET    /lectures/:id/transcript
GET    /lectures/:id/notes
```

## Live actions

```text
POST /lectures/:id/audio/chunks
POST /lectures/:id/mark-important
POST /lectures/:id/catch-me-up
```

## Visual

```text
POST /lectures/:id/pair-device
POST /lectures/:id/captures
```

## Profiles

```text
POST /note-profiles
GET  /note-profiles
POST /model-profiles
GET  /model-profiles
```

## Study

```text
POST /study-sessions
GET  /study-sessions/:id
POST /practice/:id/attempt
GET  /courses/:id/mastery
```

---

# 38. WebSocket Contract

Server → client messages:

- transcript.segment;
- topic.updated;
- notes.delta;
- lecture.status;
- capture.processed;
- catchup.ready;
- system.warning.

Client → server:

- lecture.join;
- lecture.leave;
- transcript.edit;
- mark-important;
- catchup.request.

Message envelope:

```json
{
  "type": "notes.delta",
  "lecture_id": "...",
  "timestamp": "...",
  "trace_id": "...",
  "payload": {}
}
```

---

# 39. OpenTelemetry

Instrument every service from early development.

Services:

- API;
- realtime gateway;
- STT worker;
- note worker;
- vision worker;
- document worker;
- context retrieval worker;
- study worker.

Propagate trace context through Kafka headers.

---

# 40. Distributed Trace Example

One audio chunk should be traceable across:

```text
POST audio chunk
 → object storage upload
 → Kafka produce
 → Kafka queue wait
 → STT consume
 → STT inference
 → transcript DB insert
 → transcript Kafka event
 → note consumer
 → RAG retrieval
 → LLM inference
 → note DB update
 → WebSocket delivery
```

This enables investigation of questions such as:

> “Why did this live note take four seconds to appear?”

without guessing.

---

# 41. Metrics

## 41.1 API

- requests_total
- request_duration_seconds
- http_4xx_total
- http_5xx_total
- websocket_connections

## 41.2 Kafka

- messages_produced_total
- messages_consumed_total
- consumer_lag
- consumer_processing_duration
- retry_events_total
- dlq_events_total

## 41.3 STT

- stt_processing_duration_seconds
- audio_chunk_to_transcript_seconds
- stt_errors_total
- stt_confidence
- real_time_factor

## 41.4 LLM

- llm_request_duration_seconds
- llm_requests_total
- llm_failures_total
- llm_tokens_input
- llm_tokens_output
- llm_structured_parse_failures

## 41.5 RAG

- retrieval_duration_seconds
- retrieval_candidates
- retrieval_selected_chunks
- retrieval_score_distribution

## 41.6 Notes

- transcript_to_note_latency
- note_delta_generation_duration
- finalization_duration
- notes_generated_total

## 41.7 Storage

- object_write_latency
- object_write_failures
- database_query_latency
- database_connections
- disk_utilization

## 41.8 End-to-end

- audio_chunk_to_live_transcript
- audio_chunk_to_live_note
- lecture_stop_to_final_notes

---

# 42. Logging

Use structured JSON logs.

Useful fields:

- timestamp;
- service;
- level;
- message;
- trace_id;
- span_id;
- event_id;
- lecture_id;
- course_id;
- worker_id;
- exception type.

Do not routinely emit full transcript/course contents into centralized telemetry.

Use Loki for aggregation.

---

# 43. Traces

Use Tempo as the distributed tracing backend.

Grafana should link from:

metric anomaly → trace → relevant logs.

Ideal debugging workflow:

1. see p95 spike;
2. select time range;
3. inspect slow trace;
4. identify Kafka wait vs model inference vs DB latency;
5. inspect matching logs.

---

# 44. Error Tracking

Use GlitchTip for:

- frontend exceptions;
- API exceptions;
- worker crashes;
- stack traces;
- build/release IDs;
- trace context.

GlitchTip is **not** the primary throughput/latency monitoring system.

Performance belongs in Prometheus/Grafana/Tempo.

---

# 45. Alerting

Use Alertmanager for system alerts.

Example alert rules:

## STT latency

p95 audio-chunk-to-transcript > 3 seconds for 5 minutes.

## Kafka lag

STT consumer lag > 1000.

## DLQ

DLQ event count > 0.

## API error rate

5xx > 5% over a defined interval.

## Model availability

Ollama health check fails.

## Storage

SeaweedFS capacity > 85%.

## Database

Connection pool > 80% utilized for sustained duration.

## KEDA saturation

Worker deployment remains at max replicas while lag continues increasing.

Initial alert destination can be a local webhook or email.

---

# 46. Grafana Dashboards

Create dashboards for:

## System overview

- active lectures;
- API RPS;
- p95 end-to-end latency;
- error rate;
- overall worker health.

## Kafka

- messages/sec;
- lag by consumer group;
- partition health;
- retry count;
- DLQ count.

## AI pipeline

- STT latency;
- note model latency;
- local inference queue;
- model failures.

## Storage

- DB query latency;
- connection pool;
- SeaweedFS storage;
- object error rate.

## Kubernetes

- pod count;
- CPU;
- memory;
- replica changes;
- restarts.

## Load test

- virtual users;
- request rate;
- p50/p95/p99;
- Kafka lag;
- replicas;
- errors.

---

# 47. Docker

## 47.1 Requirement

Every application/infrastructure component should be reproducible through containers where practical.

## 47.2 Compose profiles

### core

- frontend;
- API;
- realtime;
- Postgres;
- Valkey;
- SeaweedFS;
- Kafka;
- Apicurio;
- Kafbat UI.

### ai

- Ollama;
- STT worker;
- note worker;
- vision worker;
- document worker;
- study worker.

### observability

- OTel Collector;
- Prometheus;
- Grafana;
- Loki;
- Tempo;
- Alertmanager;
- GlitchTip.

### full

All profiles.

## 47.3 GPU

Local AI containers should support GPU acceleration where available.

Development should not require every large model to be loaded simultaneously.

---

# 48. Kubernetes

## 48.1 Local cluster

Use **k3d** to run k3s nodes inside Docker.

Suggested cluster:

- 1 server/control plane;
- 2 agents.

## 48.2 Namespace design

### application

- frontend;
- API;
- realtime;
- workers.

### data

- Postgres;
- Valkey;
- SeaweedFS.

### kafka

- Strimzi operator;
- Kafka cluster;
- Apicurio;
- Kafbat UI.

### observability

- OTel Collector;
- Prometheus;
- Grafana;
- Loki;
- Tempo;
- Alertmanager;
- GlitchTip.

## 48.3 Kubernetes workload requirements

Application deployments should define:

- liveness probes;
- readiness probes;
- CPU/memory requests;
- CPU/memory limits;
- ConfigMaps;
- Secrets;
- replica counts;
- graceful shutdown handling.

Stateful components require persistent volumes.

---

# 49. Strimzi

Use Strimzi to operate Kafka on Kubernetes.

This demonstrates:

- Kubernetes Operators;
- CRDs;
- StatefulSets indirectly;
- persistent storage;
- topic configuration;
- rolling broker changes;
- Kubernetes-native Kafka administration.

Do not hand-write a complex Kafka StatefulSet unless the goal is specifically to learn the internals Strimzi abstracts.

---

# 50. KEDA

## 50.1 Why KEDA is valuable

KEDA gives Kubernetes autoscaling a concrete reason to exist.

Scale worker replicas from Kafka consumer lag.

Example:

```text
lag = 10
STT workers = 1

lag = 4000
STT workers = 1 → 2 → 4 → 8

lag drains
STT workers = 8 → 4 → 2 → 1
```

## 50.2 Candidate deployments

- STT;
- document ingestion;
- note generation;
- vision.

## 50.3 Measure during scaling

- consumer lag;
- replicas;
- processing throughput;
- p95 latency;
- CPU;
- memory;
- scale-up delay;
- queue-drain time.

---

# 51. Helm

Use Helm after basic Kubernetes deployment is understood.

Suggested charts:

- academic-app;
- data;
- observability.

Potential values files:

- values-local.yaml;
- values-test.yaml;
- values-benchmark.yaml.

---

# 52. Argo CD

Optional late-phase GitOps.

```text
Git
 → Argo CD
 → Helm
 → Kubernetes
```

Demonstrates:

- declarative deployment;
- reconciliation;
- GitOps;
- reproducible environment state.

Do not add Argo CD before Helm/k3d deployment works manually.

---

# 53. k6 Load Testing

## 53.1 Purpose

Do not claim scalability without measurement.

k6 should create reproducible workloads.

## 53.2 Scenarios

### REST API

- create course;
- create lecture;
- upload chunk metadata;
- retrieve notes.

### WebSocket

- maintain multiple active lecture connections.

### Lecture simulation

Each virtual lecture generates an audio event on a schedule.

### Document ingestion

Upload multiple course files concurrently.

## 53.3 Suggested tiers

- 1 lecture;
- 10 lectures;
- 50 lectures;
- 100 lectures.

The actual maximum depends on the user's hardware and local model capacity.

## 53.4 Metrics

- events/sec;
- API throughput;
- p50;
- p95;
- p99;
- Kafka lag;
- error rate;
- CPU;
- memory;
- worker replicas;
- DB utilization.

## 53.5 Benchmark evidence

Store benchmark outputs in:

`docs/benchmarks/`

Resume performance numbers must come from these actual results.

---

# 54. Testing Strategy

## 54.1 Unit tests

Test:

- prompt assembly;
- note delta merge;
- parser utilities;
- event validation;
- retry classification;
- mastery heuristic;
- provider adapters.

## 54.2 Integration tests

Run against containerized:

- Kafka;
- Postgres;
- Valkey;
- SeaweedFS.

Test:

- event publish/consume;
- DB write;
- duplicate event;
- retry;
- DLQ;
- object lookup.

## 54.3 Contract tests

Validate:

- Protobuf compatibility;
- REST schemas;
- WebSocket schemas;
- structured LLM outputs.

## 54.4 End-to-end fixture

Create a deterministic fixture containing:

- sample lecture audio;
- slide deck;
- board image;
- expected topic boundaries;
- known concept list.

Run:

course → lecture → audio → transcript → notes → finalization → practice.

## 54.5 Failure tests

Explicitly test:

- STT worker killed mid-processing;
- Ollama unavailable;
- Kafka temporarily unavailable;
- Postgres unavailable;
- corrupt event;
- missing object;
- duplicate event;
- DLQ path;
- worker restart;
- Kubernetes pod restart.

---

# 55. Reliability Principles

## 55.1 Graceful degradation

If RAG fails:

- produce lecture-only notes;
- label course context unavailable.

If note generation fails:

- preserve transcript.

If vision fails:

- preserve image;
- allow retry.

If finalization fails:

- retain live transcript and notes;
- retry finalization asynchronously.

## 55.2 Backpressure

Kafka consumer lag is the primary backlog signal.

Do not keep expensive inference inside synchronous API request paths.

## 55.3 Exactly-once language

Prefer:

- at-least-once delivery;
- idempotent consumers;
- transactional outbox.

Do not claim universal exactly-once behavior.

---

# 56. Privacy and Security

## 56.1 Recording visibility

The UI must clearly indicate recording status.

Users should be reminded to comply with:

- applicable recording laws;
- university policy;
- instructor policy.

## 56.2 Processing modes

### Fully Local

No model input leaves the machine.

### Hybrid

Some roles are local and some external.

### Cloud

Course data may be transmitted to configured external providers.

The active processing path should be obvious in settings.

## 56.3 Secrets

Local development:

- `.env`;
- never commit secrets.

Kubernetes:

- Secrets.

Do not store provider API keys in browser localStorage.

## 56.4 Retention controls

Options may include:

- delete raw audio after final transcript;
- retain raw audio;
- remove board images after extraction;
- delete lecture;
- delete course;
- regenerate notes after deleting raw audio where possible.

## 56.5 Telemetry privacy

Avoid placing full transcript text or full student documents in:

- metrics;
- logs;
- error tracking.

Prefer IDs and trace references.

---

# 57. Repository Structure

```text
academic-learning-system/
├── apps/
│   ├── web/                    # Next.js
│   ├── api/                    # FastAPI REST
│   └── realtime/               # WebSocket gateway
├── workers/
│   ├── stt/
│   ├── notes/
│   ├── vision/
│   ├── documents/
│   ├── context/
│   ├── study/
│   └── outbox/
├── packages/
│   ├── event-contracts/
│   ├── model-providers/
│   ├── observability/
│   ├── schemas/
│   └── shared-types/
├── infra/
│   ├── compose/
│   ├── kafka/
│   │   ├── topics/
│   │   └── schemas/
│   ├── k3d/
│   ├── kubernetes/
│   ├── helm/
│   └── observability/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── contract/
│   ├── e2e/
│   └── load/
├── docs/
│   ├── architecture/
│   ├── adr/
│   ├── benchmarks/
│   ├── runbooks/
│   └── diagrams/
├── scripts/
├── Makefile
└── README.md
```

---

# 58. Architecture Decision Records

Add ADRs for important choices.

Suggested ADRs:

- ADR-001 — Kafka instead of direct worker calls
- ADR-002 — SeaweedFS for binary objects
- ADR-003 — pgvector before dedicated vector DB
- ADR-004 — modular monolith + workers instead of microservices
- ADR-005 — at-least-once delivery + idempotency
- ADR-006 — Protobuf event schemas
- ADR-007 — local-first model abstraction
- ADR-008 — k3d for local Kubernetes
- ADR-009 — Strimzi for Kafka
- ADR-010 — KEDA for lag-based autoscaling
- ADR-011 — OpenTelemetry as vendor-neutral instrumentation
- ADR-012 — raw evidence vs derived artifact separation

ADRs should include:

- context;
- decision;
- alternatives;
- consequences;
- date/status.

---

# 59. Initial SLO Targets

These are engineering targets, not final claims.

## Live transcript

Target p95 audio-chunk-to-transcript latency:

**< 3 seconds**

## Live notes

Target p95 transcript-to-note-delta latency:

**< 3 seconds**, subject to local model performance.

## REST API

Normal metadata API p95:

**< 300 ms**, excluding large uploads and model inference.

## Error rate

Steady-state benchmark core API:

**< 1% errors** target.

## Data integrity

Acknowledged audio metadata should not be silently lost.

## DLQ

Nominal test suite should produce **0 DLQ events**.

These targets should be revised after measurement.

---

# 60. Development Commands

Potential Makefile commands:

```text
make dev-core
make dev-ai
make dev-observability
make dev-full

make test
make test-unit
make test-integration
make test-contract
make test-e2e
make benchmark

make k3d-up
make k3d-down
make helm-install
make helm-uninstall
make dashboards
```

The goal is one-command reproducibility.

---

# 61. Detailed Implementation Phases

## Phase 0 — Foundation

### Build

- monorepo;
- Next.js shell;
- FastAPI shell;
- Postgres;
- Valkey;
- SeaweedFS;
- single-node Kafka;
- Apicurio optional initially;
- Docker Compose;
- course schema;
- lecture schema;
- event envelope;
- provider interfaces;
- OpenTelemetry initialization;
- health endpoints.

### Tests

- create course;
- create lecture;
- write/read Postgres;
- publish/consume a sample event;
- object put/get;
- trace ID appears in logs.

### Exit criteria

`docker compose --profile core up` starts the core environment and one test event travels from API → Kafka → consumer.

---

## Phase 1 — Live Capture + STT

### Build

- browser microphone capture;
- chunk transport;
- audio object storage;
- `audio.chunk.ready` events;
- STT consumer group;
- faster-whisper provider;
- transcript segment persistence;
- `transcript.segment.created` events;
- WebSocket live transcript;
- sequence ordering;
- retries;
- DLQ.

### Metrics

- upload latency;
- Kafka queue wait;
- STT inference time;
- chunk-to-transcript latency;
- error rate;
- consumer lag.

### Exit criteria

- 45–60 minute test lecture processes continuously;
- transcript remains ordered;
- reconnect does not duplicate segments;
- duplicate events are idempotent;
- p95 metrics are visible.

---

## Phase 2 — Custom Note Engine

### Build

- Note Profile CRUD;
- Model Profile CRUD;
- Ollama note provider;
- structured note schema;
- rolling topic buffer;
- topic segmentation baseline;
- note delta events;
- live note UI;
- transcript provenance;
- Mark Important;
- Catch Me Up.

### Exit criteria

- same transcript produces materially different note styles under different profiles;
- every important note can link back to transcript evidence;
- note-worker failure does not interrupt transcription.

---

## Phase 3 — Course RAG

### Build

- document upload;
- parser worker;
- semantic chunking;
- metadata extraction;
- embedding provider;
- pgvector;
- retrieval service;
- syllabus intelligence;
- slide indexing;
- homework context;
- Apicurio Registry;
- Protobuf event schemas;
- schema compatibility tests.

### Exit criteria

- note generation retrieves relevant course context;
- citations/provenance point to the correct document chunk;
- unrelated course content is excluded;
- incompatible event schema changes fail CI.

---

## Phase 4 — Multimodal Capture

### Build

- phone pairing token;
- QR code;
- lightweight phone UI;
- image upload;
- visual event;
- vision worker;
- image classification;
- equation/code/diagram handling;
- slide alignment;
- visual provenance.

### Exit criteria

- a board image is associated with the correct lecture/topic;
- visual analysis enriches the correct note section;
- source remains clearly identified.

---

## Phase 5 — Post-Lecture Learning

### Build

- final STT pass;
- transcript correction;
- final topic segmentation;
- final note regeneration;
- concept extraction;
- concept graph baseline;
- Teach This Better;
- active recall;
- practice generation;
- mastery events;
- post-lecture short review.

### Exit criteria

Every completed lecture can produce:

- final notes;
- source links;
- concepts;
- a short review;
- mastery evidence after practice.

---

## Phase 6 — Observability + Reliability

### Build

- OTel Collector;
- Prometheus;
- Grafana;
- Loki;
- Tempo;
- Alertmanager;
- GlitchTip;
- dashboards;
- retry metrics;
- DLQ metrics;
- runbooks;
- transactional outbox.

### Failure drills

- kill STT worker;
- disable Ollama;
- force DLQ;
- restart Kafka;
- cause storage failure.

### Exit criteria

- one trace spans API → Kafka → worker → DB → WebSocket;
- dashboards show p95 and lag;
- an intentional fault triggers the expected alert;
- DLQ can be inspected and replayed.

---

## Phase 7 — Kubernetes

### Build

- k3d cluster;
- namespace separation;
- basic manifests;
- probes;
- persistent volumes;
- resource requests/limits;
- Helm;
- Strimzi;
- Kafka cluster in Kubernetes;
- application worker deployments.

### Exit criteria

- supported stack boots in k3d;
- worker pods restart cleanly;
- persistent data survives pod restart;
- Kafka operates through Strimzi.

---

## Phase 8 — KEDA + Load Testing

### Build

- KEDA Kafka scaler;
- k6 scripts;
- lecture simulator;
- benchmark dashboard;
- CPU/memory profiling;
- fault/load scenarios.

### Exit criteria

- worker replicas respond to Kafka lag;
- queue drains after burst load;
- benchmark report contains measured p50/p95/p99;
- results are committed to `docs/benchmarks/`;
- no fabricated performance numbers.

---

## Phase 9 — Optional GitOps / CDC

### Build

- Argo CD;
- GitOps deployment;
- Debezium;
- WAL-based outbox publication;
- environment overlays;
- backup/restore documentation;
- refined runbooks;
- polished demo environment.

### Exit criteria

- Git changes reconcile into the local cluster;
- outbox events can be driven through CDC;
- deployment state is reproducible.

---

# 62. Free / Self-Hosted Tooling Constraint

The intended stack should remain usable locally without managed-service subscription fees.

Core choices are selected for self-hosting/container use:

| Component | Role |
|---|---|
| Apache Kafka | Event streaming |
| Apicurio Registry | Schema registry |
| Kafbat UI | Kafka UI |
| PostgreSQL | Relational database |
| pgvector | Vector search |
| Valkey | Cache / ephemeral state |
| SeaweedFS | Object storage |
| Ollama | Local LLM/VLM runtime |
| faster-whisper | Local STT |
| OpenTelemetry | Telemetry instrumentation |
| Prometheus | Metrics |
| Grafana | Dashboards |
| Loki | Logs |
| Tempo | Traces |
| Alertmanager | Alerts |
| GlitchTip | Error tracking |
| k6 | Load testing |
| Docker | Containers |
| k3d / k3s | Local Kubernetes |
| Strimzi | Kafka operator |
| KEDA | Event-driven autoscaling |
| Helm | Kubernetes packaging |
| Argo CD | Optional GitOps |
| Debezium | Optional CDC |

Before any commercial deployment, licenses and distribution terms should be re-checked. For the local portfolio implementation, the goal is a fully self-hosted toolchain without managed service costs.

---

# 63. Resume / Interview Positioning

Do not describe the project as:

> “Made an AI notes app using Kafka and Kubernetes.”

Stronger framing:

> Built a multimodal academic learning platform that streams lecture audio through an event-driven Kafka pipeline, performs local speech recognition and configurable LLM note generation, enriches notes with RAG over course materials and board images, and preserves timestamp-level provenance.

Potential systems bullet after implementation:

> Designed Kafka consumer groups and lecture-scoped partitioning for ordered asynchronous processing; implemented idempotent workers, schema-registry-backed event contracts, bounded retries, dead-letter topics, and distributed tracing across the ingestion pipeline.

Potential infrastructure bullet after implementation:

> Containerized the platform with Docker and deployed it to local Kubernetes using k3d, Strimzi, Helm, and KEDA; autoscaled inference workers from Kafka consumer lag and benchmarked throughput and p95 latency with k6.

Potential observability bullet:

> Instrumented services with OpenTelemetry and built Prometheus/Grafana/Loki/Tempo dashboards and alerting for consumer lag, STT latency, model failures, DLQ growth, and end-to-end lecture processing.

Only add measured performance numbers after running benchmarks.

---

# 64. What This Project Demonstrates

## Applied AI

- speech-to-text;
- model abstraction;
- local inference;
- multimodal vision;
- RAG;
- embeddings;
- structured model output;
- provenance;
- prompt/context engineering.

## Distributed systems

- Kafka;
- partitioning;
- consumer groups;
- retries;
- DLQs;
- idempotency;
- schema evolution;
- outbox;
- CDC later.

## Platform engineering

- Docker;
- Kubernetes;
- k3d;
- Strimzi;
- KEDA;
- Helm;
- GitOps.

## Observability / performance

- OpenTelemetry;
- Prometheus;
- Grafana;
- Loki;
- Tempo;
- Alertmanager;
- GlitchTip;
- k6.

The project is strong only if these systems are actually integrated and measurable.

---

# 65. Non-Goals for Early Phases

Do not spend early time on:

- multi-region deployment;
- internet-scale user management;
- custom Kubernetes operators;
- service mesh;
- separate vector database;
- five cloud providers at once;
- mobile native app;
- full GitOps before the application works;
- advanced knowledge-tracing ML before basic practice works;
- premature microservices.

The project already has enough complexity.

---

# 66. Engineering Rules

1. The note-taking experience remains the primary entry point.
2. The product should reduce the cost of re-engaging, not encourage disengagement.
3. Capture original evidence before generating conclusions.
4. Never blur professor/course content with AI-added explanation.
5. Keep lecture-time UI minimal.
6. Keep model providers swappable.
7. Keep large binary objects out of Kafka.
8. Partition lecture-scoped events by lecture_id.
9. Design for at-least-once delivery.
10. Make consumers idempotent.
11. Bound retries.
12. Use DLQs.
13. Use schema contracts.
14. Keep PostgreSQL as system of record.
15. Use pgvector before a dedicated vector DB.
16. Use Valkey only for ephemeral state.
17. Use object storage for media/documents.
18. Begin as a modular monolith with asynchronous workers.
19. Instrument from the beginning of the async pipeline.
20. Propagate trace IDs through Kafka.
21. Measure p50/p95/p99 instead of saying “fast.”
22. Use Docker Compose before Kubernetes.
23. Use Kubernetes only when its behavior can be demonstrated.
24. Use KEDA so autoscaling has a real signal.
25. Store benchmark artifacts.
26. Never invent throughput or latency claims.
27. Add infrastructure incrementally.
28. Preserve graceful degradation.
29. Keep privacy modes explicit.
30. If a tool cannot be defended in an interview, remove it.

---

# 67. Definition of Product Success

A successful student experience allows the user to:

1. create a course;
2. upload syllabus/slides/homework/readings;
3. create or choose a Note Profile;
4. select local/hybrid/cloud model behavior;
5. start a lecture;
6. receive timestamped live transcription;
7. receive live structured notes;
8. use Catch Me Up;
9. Mark Important;
10. pair a phone;
11. capture a board/screen image;
12. receive final source-linked notes;
13. identify professor vs course vs AI content;
14. ask for a better explanation;
15. complete short active-recall review;
16. accumulate mastery evidence;
17. receive increasingly personalized notes/practice.

---

# 68. Definition of Engineering Success

A successful engineering implementation should also:

1. process async work through Kafka;
2. preserve lecture event ordering;
3. tolerate duplicate delivery;
4. expose Kafka consumer lag;
5. recover from worker crashes;
6. bound retries and use DLQs;
7. use registered event schemas;
8. trace one request across the full async pipeline;
9. expose metrics, logs, and traces;
10. raise alerts on meaningful failures;
11. boot through Docker Compose;
12. boot in local Kubernetes;
13. operate Kafka through Strimzi;
14. autoscale workers from Kafka lag through KEDA;
15. produce a reproducible k6 benchmark report;
16. document important architecture decisions;
17. demonstrate at least one intentional fault and successful recovery.

---

# 69. Final Architecture Principle

The final system should be deliberately ambitious, but the project must never become an exercise in adding tools for their own sake.

The test for every infrastructure component is:

- What workload does it handle?
- What failure mode does it address?
- What metric proves it is working?
- What tradeoff did it introduce?
- Could you explain that tradeoff in an interview?

If the answer is no, the component should be removed.

The strongest version of this project is not the one with the most logos. It is the one where the product, AI pipeline, event architecture, reliability model, observability stack, Kubernetes deployment, and measured benchmarks all reinforce one coherent system.
