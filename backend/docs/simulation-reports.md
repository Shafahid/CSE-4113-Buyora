# Simulation jobs, reports, and recovery

This document covers the Phase 1 B1-B4 simulation/report backend. It describes
local operation without containing provider keys, database credentials, or
customer inputs.

## Data ownership and persistence

`buyora.simulation_runs` is the seller-owned durable job and report record.
`buyora.simulation_run_evaluations` stores each selected fictional buyer
perspective independently. The run's immutable `inputs` snapshot contains the
original product, exact post version, audience, language, selected profiles,
mode, scoring/prompt versions, provider identity and execution safeguards.

The finished report is stored on the run. Each evaluation also retains its own
output, error code, attempt count and event history, so partial failure never
deletes successful reactions. Product edits and later post versions do not
rewrite saved reports. Every API query checks the authenticated seller ID.

## Migrations

Apply migrations before starting the API or worker:

```powershell
uv run alembic upgrade head
uv run alembic current
```

The worker requires revision `0011` or later. Revision 0011 adds persisted job
stage and expected-persona count and backfills existing runs transactionally.
Use `alembic heads` to see the current repository target.

If either queue logs `Simulation worker unavailable (OperationalError)`, run:

```powershell
uv run python scripts/check_simulation_setup.py
```

The check tests the runtime database connection, compares applied revisions with
the repository heads, and verifies mapped columns and SELECT access for all four
worker tables, including `persona_adaptations`. It reads no job payloads and
prints no credentials. A ready worker schema and pending later migrations are
reported separately. The command exits with code 1 for connection/schema errors
or pending migrations. After reviewing pending migrations, use
`uv run python scripts/check_simulation_setup.py --apply` to upgrade a known
revision 0007 or later to head and recheck the runtime database.

Worker warnings distinguish authentication, DNS, timeout, refused/dropped
connections, pooler capacity and permission failures. Repeated failures back off
from 1 to 30 seconds; a successful queue poll resets the delay and logs recovery.
If checks pass while warnings recur, inspect network and pooler availability at
the time of the warning. Readiness alone does not verify the worker schema.

## Starting the API and worker

For local development, the API can embed the worker:

```powershell
uv run uvicorn main:app --reload
```

`SIMULATION_WORKER_ENABLED=true` is the default. The embedded worker starts even
without a model key, allowing `LLM_FALLBACK_ENABLED=true` runs to finish with
clearly labeled deterministic assessments.

To operate the worker separately, run these in different terminals:

```powershell
# API terminal
$env:SIMULATION_WORKER_ENABLED = "false"
uv run uvicorn main:app --reload
```

```powershell
# Worker terminal
uv run python worker.py
```

The explicit worker command does not read the API embedding switch. PostgreSQL
row locks prevent two workers from claiming the same run. A lease and heartbeat
allow another worker to recover an expired job.

## Modes and progress

Named modes require exact counts: Quick 5, Standard 10, Deep 20 and Extended 30.
Custom requests may select 2 through `SIMULATION_MAX_PERSONAS`. Progress responses
include `stage`, `expected_personas`, queued/running/processed/completed/failed
counters and `processing_percent`.

Stages are `queued`, `evaluating`, `report_ready`, `report_ready_partial` and
`failed`. Processing progress counts both completed and failed evaluations;
coverage counts only usable completed assessments.

The worker dispatches at most `SIMULATION_CONCURRENCY` persona evaluations at
once. Saved and current model-call/token safeguards are both honored. Reports
include actual provider token and latency metadata, provider-reported USD cost
when available, fallback count and whether a safeguard blocked work. No cost is
invented when a provider does not supply one.

## Failure and retry behavior

| Condition | Stored result | Recovery |
| --- | --- | --- |
| Transient provider error | Automatic bounded retry with backoff | Worker retries up to the configured per-execution limit |
| One persona fails | Other completed reactions remain saved | Retry that perspective or use bulk retry |
| Worker stops before dispatch | Queued evaluations remain queued | Restart any worker |
| Worker stops during an unknown provider call | In-flight evaluation becomes `interrupted` | Explicit seller retry prevents accidental double billing |
| Model-call/token safeguard | Failed or labeled fallback result | Review limits; start a fresh run only when appropriate |
| Provider configuration/authentication error | Non-actionable failure | Correct backend configuration before retrying |
| Fallback enabled | Deterministic labeled assessment | A later explicit retry may replace fallback with AI |

Completed AI reactions are never rerun by a retry. Bulk retries use a durable
request UUID so a delayed repeated HTTP request cannot schedule duplicate work.
Manual retries are capped at six attempts per perspective.

## Report APIs

- `GET /reports`: seller history with `q`, status, mode, date, order and
  pagination filters. Search uses immutable product/post snapshots.
- `GET /reports/{id}`: full saved report and per-persona evaluation metadata.
- `DELETE /reports/{id}`: delete one finished owned report.
- `POST /reports/compare`: compare two fully completed owned reports, including
  reports with different persona counts, across all seven score dimensions.

The older `/simulation-runs` endpoints remain available for the existing
frontend. The report endpoints use the same stored records and do not call the
model when listing, viewing, searching or comparing.

## Verification

Run the complete automated checks:

```powershell
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

From `frontend/` run `npm test`, `npm run test:integration`, `npm run lint`,
`npx tsc --noEmit` and `npm run build`.

Automated coverage includes 5/10/20/30-persona workloads, bounded concurrency,
snapshot integrity after product/post edits, history search/filter/pagination,
different-size comparison, ownership, retries, partial results, expired worker
leases, idempotency, usage safeguards, OpenAPI schemas and migration SQL.

For a manual check, start a simulation at `/simulate`, observe its persisted job
stage, leave the page, and resume it from `/history`. Open the finished report and
inspect `GET /reports/{id}` or compare it with another completed report through
the interactive API documentation at `/docs`.
