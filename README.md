# Notetaker App

A lecture note-taking application focused on turning dense, content-heavy lectures into detailed, organized, trustworthy notes.

The current product priority is **reliable lecture capture → timestamped transcription → high-quality, source-linked notes**. Notes should preserve definitions, explanations, worked examples, reasoning, qualifications, and professor emphasis. A short summary is an optional companion to the detailed notes.

## Current phase

**Phase 6 / M01: building the application.** A Next.js/FastAPI course-and-lecture workspace now runs locally, with private sessions, persistent records, migrations and application tests. Recording and generated notes are not implemented yet. PostgreSQL/SeaweedFS/Kafka configuration is ready for integration testing; Docker Desktop is installed but its Linux engine needs WSL setup.

- [Run the app and review M01 results](docs/implementation/phase-6-m01.md): preview instructions, service setup, implemented behavior and remaining verification.

After dependency installation, run `pwsh -File scripts/Start-Preview.ps1 -NewUnlockCode`, open `http://127.0.0.1:3000`, and use `.local/unlock-code.txt`. The explicitly labeled preview uses a local SQLite file; PostgreSQL remains the intended application store and has no automatic fallback. See the linked guide before switching modes or handling existing data.

- [Current product and technical specification](multimodal_academic_learning_system_spec.md): consolidated scope, selected architecture, evidence boundaries and release gates.
- [Current architecture artifact](multimodal_academic_learning_system_architecture_v2.html): standalone visual overview, version 0.3; the existing filename is retained.
- [Phase 5 implementation roadmap](docs/implementation/phase-5-roadmap.md): M01–M08, dependencies, migration/interface sequence, all 32 acceptance cases and six open qualification gates.
- [Phase 5 reconciliation](docs/implementation/phase-5-reconciliation.md): decisions changed from the originals and unresolved evaluation work.
- [Phase 5 verification](docs/implementation/phase-5-verification.md): checks performed on the consolidated documents and artifact.

The next check is **M01's real service qualification**, then M02 microphone capture and recovery. Human review, real-audio quality and usable live performance remain required release evidence. Earlier design records follow:

- [Phase 1 product brief](docs/product/phase-1-product-brief.md): audience, first-release scope, note requirements, quality gates, and open decisions.
- [Phase 2 student experience](docs/product/phase-2-student-experience.md): screens, lecture workflows, recording states, source inspection, editing, export, and accessibility requirements.
- [Phase 2 acceptance scenarios](docs/product/phase-2-acceptance-scenarios.md): observable outcomes and coverage of every core Phase 1 requirement.
- [Phase 2 verification](docs/product/phase-2-verification.md): documentation checks and the boundary between reviewed requirements and future application tests.
- [Phase 3 architecture](docs/architecture/phase-3-architecture.md): chosen components, capture recovery, processing, revisions, privacy, and deployment boundaries.
- [Phase 3 data model](docs/architecture/phase-3-data-model.md): entities, relationships, constraints, and transaction boundaries.
- [Phase 3 API and events](docs/architecture/phase-3-api-events.md): write, replay, retry, and synchronization contracts.
- [Phase 3 verification](docs/architecture/phase-3-verification.md): scenario traceability, reference tests, and remaining integration work.
- [Phase 4 AI pipeline](docs/ai/phase-4-pipeline.md): speech/note settings, evidence boundaries, context handling, and provider contracts.
- [Phase 4 evaluation plan](docs/ai/phase-4-evaluation.md): fixtures, scoring, review requirements, and qualification gates.
- [Phase 4 results](docs/ai/phase-4-results.md): executed checks, local model trials, and outstanding validation.
- [Project phases](docs/project-phases.md): the sequence from product definition through implementation and expansion.

The consolidated specification controls current scope. Earlier phase documents retain detailed contracts and the history of design/evaluation decisions.

## Original design references

- [Archived v0.2 specification](docs/archive/original-spec-v0.2.md)
- [Archived v0.2 architecture artifact](docs/archive/original-architecture-v0.2.html)

Practice generation, mastery tracking, personalization, and advanced infrastructure demonstrations follow validation of the core note-taking experience.

## Documentation verification

Install pinned JavaScript dependencies with `npm ci --ignore-scripts`. Run `npm test` for architecture/AI contracts, `.venv/Scripts/python.exe -m pytest -q` for backend application tests after Python setup, `npm run typecheck` and `npm run build:web` for the frontend, and `npm run verify:docs` for planning links/traceability. The default backend tests use isolated SQLite preview databases; the M01 guide describes real-service tests. Run `git diff --check` before committing edits.

With Qwen3 4B already installed in a local Ollama service, run `npm run eval:notes -- qwen3:4b` for the three synthetic CS cases. This command contacts only the loopback Ollama endpoint, never downloads a model, and writes results under the ignored `evaluations/local-runs/` directory. Valid structure is not a passing educational-quality score. Selected reviewed run artifacts belong in `evaluations/reports/`; model weights and caches do not belong in Git.
