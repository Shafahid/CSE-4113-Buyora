# Stage 1 — Shoma to Mehdi

This is the historical Stage 1 baseline. The implemented adapters, durable queue,
current migration and runtime limitations are recorded in
[Stage 2 — Mehdi to Abu Bakar](02-mehdi-to-abu-bakar.md).

Status: implementation baseline for review. No teammate acceptance is implied.
Prepared: 2026-11-28. Contract version: 1.0. Target migration: 0017.

## What changed

The existing image, competitor, platform and analysis APIs are extended with
explicit competitor provenance, versioned AI contracts, shared optional-AI
admission limits, immutable report findings and reproducible contract fixtures.
Market dispatch now uses the same verified transactional admission interface as
image/platform dispatch. Failed/unavailable admissions do not consume allowance.

Owned modules: `backend/app/models/`, feature routes, `services/ai_limits.py`,
`services/analysis_attachments.py`, provider-neutral service contracts,
`migrations/versions/0017_phase2_handover.py`, tests and `docs/phase2/`.
Existing simulation worker diagnostics from the preceding repair are retained.

PR links: pending reviewer-created PRs. This work has not been committed,
pushed or merged by this handoff preparation.

## Run and configure

Use Python/uv versions from the lockfile. From `backend/`, run `uv sync --locked`,
configure `.env`, run `uv run alembic upgrade head`, then
`uv run uvicorn main:app --reload`. `/docs` and committed `../openapi.json` expose
the APIs. API startup never mutates schema.

Environment names: `DATABASE_URL`, optional `MIGRATION_DATABASE_URL`,
`CORS_ORIGINS`, session-cookie settings, `SUPABASE_URL`,
`SUPABASE_SECRET_KEY`, `SUPABASE_STORAGE_BUCKET`, and the five `PHASE2_AI_*`
settings documented in `../API_CONTRACT.md`. Provider keys remain backend-only.
No real values are included here. Existing simulation settings remain supported.

## Contracts and examples

Read `../API_CONTRACT.md`, `../DATA_MODEL.md` and `../AI_OUTPUTS.md`.
The JSON fixture families contain `example_only:true`; their `payload`
validates against committed JSON Schema. They are not live AI findings.
The advanced-report fixture covers Stage 1 attachment storage; analytics/PDF
implementation remains Stage 3 work.

## Test evidence

Verified on 2026-11-28:

- Full backend suite with disposable PostgreSQL enabled: **260 passed**, including
  three PostgreSQL integration tests. Existing LangSmith dependencies emit 17
  deprecation warnings; no test failures.
- `uv run ruff check .`: passed.
- `uv run ruff format --check .`: passed (119 Python files).
- Frontend `tsc --noEmit`: passed after regenerating API types.
- `git diff --check`: passed.

PostgreSQL 17.12 ran in a disposable Docker container bound to localhost. Each
integration test created and dropped only its own UUID-named database. Coverage
includes a clean upgrade chain, old product/post/report access and report
preservation across 0017, downgrade refusal without data loss, reservation
index/uniqueness and concurrent admission. No live provider calls were used.
Reproduction commands are in `../HANDOVER_CHECKLIST.md`.

The configured application database was upgraded from 0016 to **0017** on
2026-11-28. Connectivity, worker schema, competitor provenance columns and the
private reservation table/index/uniqueness/grants were verified successfully.
The disposable test container and its anonymous volume were removed afterward.

## Known limitations and next owner's starting point

Implement `ImageAnalyzer.analyze`, `MarketAnalyzer.analyze` and
`PlatformContentGenerator.generate` using the frozen Pydantic contracts. Respect
the saved budget, validate complete input/vision tokens and output caps, enforce
the provider timeout, and ground outputs before saving them.

Connect a durable worker through `DurableProcessingAdmission.verify_ready` and
`enqueue`; include leases/crash recovery and transactional dispatch. Until then
new optional AI requests return 503. Do not replace this gate with a boolean flag
or a fire-and-forget task. Test doubles stay in tests.

Nullable source fields preserve legacy observations; their provenance remains
unknown. Existing reports without optional sections stay readable. The seven
persona score definitions are unchanged. Provider model/prompt/latency/token
measurements and advanced analytics/PDF outputs remain later-stage work.

Meeting approvals, PR review/merge and Mehdi's acceptance are pending. Record
them in `../HANDOVER_CHECKLIST.md` after the team reviews this concrete package.
