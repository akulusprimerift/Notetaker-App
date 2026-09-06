# Notetaker App

A lecture note-taking application focused on turning dense, content-heavy lectures into detailed, organized, trustworthy notes.

The current product priority is **reliable lecture capture → timestamped transcription → high-quality, source-linked notes**. Notes should preserve definitions, explanations, worked examples, reasoning, qualifications, and professor emphasis. A short summary is an optional companion to the detailed notes.

## Current phase

**Phase 2: Student experience.** Product scope and student workflows are documented. The repository currently contains planning documents; application implementation has not started.

- [Phase 1 product brief](docs/product/phase-1-product-brief.md): audience, first-release scope, note requirements, quality gates, and open decisions.
- [Phase 2 student experience](docs/product/phase-2-student-experience.md): screens, lecture workflows, recording states, source inspection, editing, export, and accessibility requirements.
- [Phase 2 acceptance scenarios](docs/product/phase-2-acceptance-scenarios.md): observable outcomes and coverage of every core Phase 1 requirement.
- [Phase 2 verification](docs/product/phase-2-verification.md): documentation checks and the boundary between reviewed requirements and future application tests.
- [Project phases](docs/project-phases.md): the sequence from product definition through implementation and expansion.

The Phase 1 brief records the current note-taking priority. The original documents remain broader references; their feature lists and infrastructure phases are not all requirements for the first release.

## Original design references

- [Product and technical specification](multimodal_academic_learning_system_spec.md)
- [HTML architecture artifact](multimodal_academic_learning_system_architecture_v2.html)

Practice generation, mastery tracking, personalization, and advanced infrastructure demonstrations follow validation of the core note-taking experience.

## Documentation verification

Run `pwsh -NoProfile -File scripts/Verify-PlanningDocs.ps1` to check local Markdown file links and Phase 2 acceptance coverage. This validates planning documents, not application behavior. Run `git diff --check` before committing edits.
