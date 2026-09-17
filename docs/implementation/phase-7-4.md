# Phase 7.4 — Measured infrastructure

Active since 2026-09-17, explicitly selected by the user. This first increment supplies read-only processing diagnostics and a reproducible history-growth experiment. It does not close earlier note/question quality or M08 release gates.

## Implemented

`GET /diagnostics/processing` requires the existing workspace session and returns a no-store snapshot of due, running and failed jobs grouped by kind/status. It reports ready versus delayed jobs, expired/missing running leases, and the oldest currently due time. One SQL aggregate query avoids loading individual job histories into Python. Ownership, course/lecture tombstones and lifecycle/audio epochs filter the result. No student text, source IDs, lecture IDs, error details, model names or credentials are returned. No mutations, migration, new service, cache or automatic polling are introduced. This is an engineering API; a student-facing diagnostics panel is deferred.

Due time changes when a retry is scheduled, so oldest-due seconds is **not** original queue age or end-to-end latency. Expired leases indicate work eligible for recovery, not proof of a dead worker. Failed counts include current-epoch failures and are not necessarily unresolved student-visible incidents. Source/settings supersession within the same epoch still relies on existing worker validation. Audio saves, broker health, outbox lag and model throughput are not measured by this endpoint.

## Named experiment: monitoring cost as history grows

Question: can current processing state be inspected without transferring full job histories or introducing another service? The synthetic workload uses 100 lectures, three job kinds, 10% due jobs and 90% completed history. It exercises the actual aggregate function in a fresh temporary SQLite database at each size; it cannot open the student library. Twenty serial warm samples follow the first query. Allocation measurement is a separate invocation to avoid distorting timings.

Run from the repository root:

```powershell
$env:PYTHONPATH='apps/api'
uv run --no-project python -m notetaker.benchmark_diagnostics --output .local/phase-7-4-benchmark.json
```

[Recorded Windows results](phase-7-4-benchmark.json), Python 3.12.14 / SQLAlchemy 2.0.52:

| Total jobs | Due jobs | Median query ms | p95 query ms | Response bytes |
| --- | --- | --- | --- | --- |
| 1,000 | 100 | 1.194 | 1.532 | 622 |
| 10,000 | 1,000 | 2.806 | 2.967 | 628 |
| 100,000 | 10,000 | 72.962 | 98.234 | 634 |

Benefit: the response remains three aggregate rows, with approximately 36 KB peak traced Python allocations at each size. Cost: query duration grows with active workload, and each request consumes an authoritative database read. This does not demonstrate a speedup against a competing implementation. No automatic polling is enabled. There is no measured justification yet for Valkey, pgvector, Kubernetes or a separate monitoring service.

Limitations: temporary SQLite with model-created tables, not production PostgreSQL or migration performance; first query is not cold-disk latency; Python tracing excludes native database memory; no concurrent writers, model calls, audio capture, resource contention, or representative lecture workload. No live-performance threshold or release claim is inferred.

## Verification and next work

Executed on Windows: full backend **218 passed, 1 service-only skip**; **60 JavaScript contracts** and **12 desktop tests** passed. Typecheck, frontend/Python lint, production web build, documentation links/structure and whitespace checks passed. No UI changes, browser-flow checks, real-service qualification or installer rebuild were performed.

Tests cover unauthenticated access, ownership filtering, deleted courses/lectures, old epochs, response privacy, due-time boundaries, delayed retries, missing/expired/valid leases, terminal-state exclusion and read-only single-query execution. Initial test setup hit existing Windows temporary/cache permissions; isolated `.local` directories resolve that environment issue. An initial query-counter assertion also observed the lifecycle coordinator's independent queries; the counter now observes only the diagnostic connection.

Next increment: repeat the experiment against an isolated PostgreSQL schema with concurrent synthetic job transitions and audio saves, record query plans and save latency, and compare monitoring disabled/enabled at a declared sampling interval. Use that evidence before adding indexes or caching. A student-facing panel and inference timing history follow only with clear semantics and capture-overhead evidence. Existing-library preservation, synthetic-only audio, explicit local models and standalone Windows follow-on remain unchanged.
