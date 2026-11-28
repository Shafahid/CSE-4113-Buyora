# Buyora backend

FastAPI backend with SQLAlchemy 2, Psycopg 3, and Alembic, managed with uv.
Supabase provides PostgreSQL hosting; a Supabase Python SDK or API key is not
needed for this database connection.

## Phase 1 backend overview

The backend owns the complete seller-data and simulation lifecycle:

| Domain | Phase 1 implementation |
| --- | --- |
| Security | Argon2 password hashing, server sessions, HttpOnly cookies, trusted-Origin checks and seller ownership |
| Catalog | Product CRUD/lifecycle, private images, promotional posts and immutable post versions |
| Simulation setup | Frozen post version, structured audience, language and editable persona persistence |
| AI services | Persona adaptation, trust signals, seven-score evaluator, evidence validation, fallback and recommendations |
| Execution | Durable jobs, 5/10/20/30 named modes, custom 2–30 runs, bounded worker, leases, retries and safeguards |
| Reports | Immutable inputs/reactions, history search/filter, detail, delete, recommendations and comparison |
| Operations | Alembic revisions 0001–0011, liveness/readiness, standalone worker and actionable recovery logs |

The current built-in persona catalog contains 11 profiles, while the execution
contract accepts validated custom/edited profiles up to 30. The backend never
exposes database, Storage or model credentials to the browser.

## Setup

Requires Python 3.13+ and [uv](https://docs.astral.sh/uv/).

Run these commands from `backend/`:

```powershell
uv sync --locked
Copy-Item .env.example .env
```

Edit `.env` and set `DATABASE_URL` using **Connect > Session pooler** in your
Supabase dashboard. Use port **5432** and the dashboard's exact username and host.
URL-encode special characters in the database password (for example, `@` becomes
`%40`, `%` becomes `%25`). Keep this file private; it is ignored by Git.

The session pooler supports IPv4 and works for the API and migrations. A direct
connection is also supported but typically requires IPv6. Optionally set
`MIGRATION_DATABASE_URL` to a direct or session-pooler connection for Alembic.
Use a direct connection or session pooler for migrations, not the transaction
pooler on port 6543. Runtime connections disable prepared statements for pooler
compatibility. TLS defaults to `sslmode=require`; the example sets it explicitly.
For a local PostgreSQL server without TLS, explicitly use `?sslmode=disable`.

Environment variables override `.env`. The `.env` path is anchored to `backend/`.
Missing or invalid connection configuration fails at application startup.

Create the application schema before using database-backed features:

```powershell
uv run alembic upgrade head
```

## Run locally

```powershell
uv run uvicorn main:app --reload
```

API: http://127.0.0.1:8000

Interactive documentation: http://127.0.0.1:8000/docs

| Endpoint | Purpose |
| --- | --- |
| `GET /` | Original welcome response |
| `GET /api/v1/health/live` | Process health; does not connect to PostgreSQL |
| `GET /api/v1/health/ready` | Executes `SELECT 1`; returns 503 if the database is unavailable |

Readiness checks connectivity, not whether migrations are current. Apply migrations
as a separate deployment step. Starting the API never creates or modifies tables.
`CORS_ORIGINS` is a JSON array, defaulting to the two local frontend origins in
`.env.example`. Set it to your deployed frontend origin when deploying.

## Project layout

```text
backend/
├── app/
│   ├── main.py                     # App factory, lifespan, middleware and routers
│   ├── api/routes/
│   │   ├── auth.py                 # Registration, login, logout and session lookup
│   │   ├── products.py             # Products and private image operations
│   │   ├── posts.py                # Posts and immutable versions
│   │   ├── simulations.py          # Saved simulation drafts
│   │   ├── personas.py             # Draft persona CRUD
│   │   ├── execution.py            # Jobs, retries, reports and comparison
│   │   └── health.py               # Liveness and readiness
│   ├── core/                        # Settings, Storage and diversity validation
│   ├── db/                          # ORM metadata, engine and sessions
│   ├── models/                      # Auth, catalog and execution persistence
│   ├── schemas/execution.py         # AI/job/report API contracts
│   └── services/                    # AI, scoring, worker, reports and recommendations
├── docs/
│   ├── ai-simulation.md             # AI contract and scoring rubric
│   └── simulation-reports.md        # Worker/report operation and recovery
├── migrations/versions/             # Alembic revisions 0001–0011
├── scripts/                         # Contract export, migration and diagnostics
├── tests/                           # Unit, API, lifecycle and migration tests
├── main.py                          # Uvicorn compatibility entry point
├── worker.py                        # Standalone simulation worker
├── alembic.ini
├── pyproject.toml
└── uv.lock
```

Database operations are synchronous. Declare database-backed route handlers with
`def` so FastAPI runs them in its thread pool. Each request gets its own session
through `DbSession`; closing the session rolls back unfinished transactions.
Write operations explicitly call `db.commit()` after all work succeeds, or use
`with db.begin():` for a transaction. The engine is disposed on application shutdown.

## Add a feature

1. Add SQLAlchemy models under `app/models/`, inheriting from `Base`, and import
   them in `app/models/__init__.py`. Unrelated tables inherit the `buyora` schema; authentication models explicitly use `public`.
2. Add request/response schemas and business logic when the feature needs them;
   keep API validation and HTTP handling in `app/api/routes/<feature>.py`.
3. Register its router in `app/api/router.py` and inject `DbSession` where needed.
4. Generate and review a migration, then apply it:

```powershell
uv run alembic revision --autogenerate -m "add feature tables"
uv run alembic upgrade head
uv run alembic current
```

Alembic only inspects the `buyora` schema and model-owned tables. It will not
autogenerate deletions of unmanaged tables or Supabase's `auth`, `storage`, or
`public` tables. To remove an application table, write and review an explicit
`op.drop_table(..., schema="buyora")` migration. Never use `Base.metadata.create_all`
at API startup. The first migration creates the private schema and the auth migration uses public.

Keep `buyora` out of Supabase's exposed Data API schemas. Database access currently
uses the configured PostgreSQL role, not a user's Supabase JWT; add authentication
and ownership checks before exposing any business-data endpoints. Use a restricted
runtime role in production and a separate migration role if needed. Alembic's
revision bookkeeping table is `public.alembic_version`.

To undo the latest migration in a development database:

```powershell
uv run alembic downgrade -1
```

Review downgrade operations before running them on data you need to keep. The
initial downgrade drops `buyora` without `CASCADE`, refusing to delete a nonempty
schema.

## Checks

```powershell
uv run pytest
uv run ruff check .
uv run ruff format --check .
```

The current Phase 1 suite contains **146 passing backend tests**, including
authentication, ownership, storage, migrations, AI validation, 5/10/20/30
workloads, bounded concurrency, retry/restart recovery, immutable report
integrity, report search/filter/comparison and OpenAPI contracts.

Tests run without Supabase credentials. API/session tests use an isolated SQLite
database; migrations compile to PostgreSQL SQL offline. To verify a live Supabase
connection, configure `.env`, apply migrations, run the API, and open
`http://127.0.0.1:8000/api/v1/health/ready`.

## Add dependencies

```powershell
uv add <package-name>
```


## Seller authentication

Authentication uses public.users, public.user_profiles, and public.auth_sessions.
The unrelated application schema remains buyora. Revision 0002 creates the three
tables if all are absent; if all exist it checks the required columns, IDs,
keys and indexes before reusing them. A partial or incompatible schema requires
manual reconciliation. No existing rows or product foreign keys are moved.
Downgrade of this revision is intentionally blocked because tables may predate it.

Test the migration against an isolated PostgreSQL database before applying it
to Supabase. After verification and backup, configure DATABASE_URL or
MIGRATION_DATABASE_URL for the intended database and run:

    uv sync --locked
    uv run alembic upgrade head

Keep RLS disabled and ensure PUBLIC, anon and authenticated have no access to
these tables, including privileges inherited through other roles. Use a restricted
backend database role. Register, login and logout require an Origin matching
CORS_ORIGINS; browser requests need credentials: "include". Set
SESSION_COOKIE_SECURE=true for HTTPS, and SESSION_COOKIE_SAMESITE=none for a
cross-site HTTPS frontend. The session defaults to seven days.


## Product endpoints

After authentication, POST /products creates a product owned by the current
seller; GET /products lists that seller's active, non-deleted products.
Creation requires a trusted Origin header like the other state-changing routes.
Supply price as a decimal string with at most two fractional digits. Optional
fields are description, features (an array of strings), warranty, delivery_info
and return_policy; currency defaults to BDT.

Revision 0003 creates public.products when absent or checks the existing
table's columns and keys without replacing it. Its downgrade deliberately
requires manual review because the table may predate the migration. Test
the revision on an isolated PostgreSQL database before applying it to a
shared database, and back up existing data.


## Product image uploads

Configure the following in backend/.env (never expose the secret to the browser
or commit it): SUPABASE_URL, SUPABASE_SECRET_KEY, and SUPABASE_STORAGE_BUCKET.
Use the project URL, a backend-only Supabase secret key, and the name of an
existing **private** bucket. Set appropriate bucket MIME and size restrictions.
Image downloads use signed URLs that expire after five minutes.

Revision 0004 checks and reuses public.product_images if present, or creates it
if absent. Back up and test all migrations on an isolated PostgreSQL database
before applying them to a shared database. The backend does not create or alter
buckets. A failed database insert triggers a best-effort object deletion; monitor
backend logs and reconcile storage if cleanup fails.

Real upload test using PowerShell 7 (use a development project and private
bucket). After testing the migration in an isolated database, apply it only to
your intended development database:

    cd E:\CSE-4113-Buyora\backend
    uv sync --locked
    uv run alembic upgrade head
    uv run uvicorn main:app --reload

In another PowerShell 7 terminal, enter your seller email and password at the
credential prompt. Replace the product ID and path with an existing product owned
by that seller and a real local image:

    $credentials = Get-Credential -Message "Enter your Buyora seller credentials"
    $origin = @{ Origin = "http://localhost:3000" }
    $body = @{ email = $credentials.UserName; password = $credentials.GetNetworkCredential().Password } | ConvertTo-Json
    Invoke-RestMethod -Method Post -Uri "http://localhost:8000/auth/login" -Headers $origin -ContentType "application/json" -Body $body -SessionVariable session
    $productId = 1
    $imageFile = Get-Item "C:\path\to\your-image.png"
    Invoke-RestMethod -Method Post -Uri "http://localhost:8000/products/$productId/images" -Headers $origin -Form @{ file = $imageFile } -WebSession $session
    Invoke-RestMethod -Method Get -Uri "http://localhost:8000/products/$productId" -WebSession $session
    Remove-Variable body,credentials

Expect 201 for upload and a product response containing signed URLs. Verify a
URL opens before expiry, the object exists in the private bucket, and the row in
public.product_images contains the object key. Another seller receives 404.
These commands modify the configured database and bucket.


### Product management

Authenticated sellers can PATCH /products/{id} to change supplied fields or
set status to active or archived. Null clears optional descriptive fields;
required fields and features cannot be null. GET /products defaults to active;
pass ?status=archived to list archived products. POST /products/{id}/duplicate
creates an active copy of product details without copying images.
DELETE /products/{id} soft-deletes the product and retains its linked data.
DELETE /products/{id}/images/{image_id} removes an image from Storage and the
database; a Storage failure keeps its row so deletion can be retried. All
mutating requests require an Origin allowed by CORS_ORIGINS.


### Promotional posts and versions

Sellers can create a post with its first version using POST
/products/{product_id}/posts. GET /products/{product_id}/posts lists posts and
their latest version. GET /posts/{post_id} returns that latest version;
GET /posts/{post_id}/versions lists all versions newest first, and GET
/posts/{post_id}/versions/{version_id} retrieves an exact saved version.
POST /posts/{post_id}/versions saves a new immutable version. Headline, body,
and platform must be nonblank; hashtags is an array of strings. State-changing
requests require an allowed Origin. Ownership is checked through the product.

Revision 0005 validates and reuses compatible public.posts and
public.post_versions tables, or creates them if both are absent. A partial or
incompatible schema stops the migration without replacing existing tables.
Test the migration and concurrent version allocation against an isolated
PostgreSQL instance before applying it to a shared database.


### Simulation setup

POST /simulations saves a draft for an owned post_version_id. The optional
audience_settings object contains location, age_range (min and optional max),
interests (string array), purchasing_preference, budget_sensitivity, and
product_needs. The optional language is en or bn and defaults to en.
GET /simulations/{id} reloads the draft. PATCH /simulations/{id} updates
language and/or replaces the full audience_settings object; send {} for the
audience object to clear it. The post version cannot be changed. Non-draft
simulations reject updates, and write requests require an allowed Origin.

Alembic revision 0006 validates and reuses a compatible existing
public.simulations table or creates it when absent. It does not replace existing
data. Back up and review migrations before applying them to shared databases.


### Simulation personas

Persona payload shared with future generation workflows:

    {
      "name": "Nadia",
      "characteristics": {
        "label": "Budget student",
        "age_range": { "min": 18, "max": 24 }
      },
      "needs": ["Practical everyday essentials at a student-friendly price"],
      "preferences": [],
      "budget_sensitivity": "high",
      "is_selected": true
    }

Create with POST /simulations/{simulation_id}/personas and list with GET at
the same path. PATCH or DELETE /simulations/{simulation_id}/personas/{persona_id}
edits or removes a persona. Selection is a normal patch, e.g.
{"is_selected": false}. New personas default to selected; needs and preferences
default to empty arrays, and budget_sensitivity can be low, medium, high, or
null. Characteristics may include additional JSON fields; patches merge
provided characteristic fields so omitted fields are preserved. Only draft
simulations can be changed; sellers can read their personas after a simulation
starts. All write requests require a trusted Origin.

Alembic revision 0007 checks and reuses compatible public.simulation_personas
tables or creates them when absent. It does not move existing rows.


### Saved simulation execution

Migrations `0009_simulation_execution` and `0011_simulation_job_observability`
add durable runs, per-persona evaluations, cache pointers, persisted job stages and
expected-persona counts in the `buyora` schema. Configure `TOKEN_BD_API_URL`,
`TOKEN_BD_API_KEY`, `TOKEN_BD_MODEL` and optionally `LLM_PROVIDER`. LiteLLM
configures the provider; LangGraph dispatches selected profiles with bounded
concurrency. `LLM_MAX_OUTPUT_TOKENS` defaults to 8192 and `LLM_TIMEOUT_SECONDS`
to 90 for verdicts with seven score explanations. Never put these credentials
in frontend environment variables.

Named run modes are Quick (5), Standard (10), Deep (20) and Extended (30).
Sending a named `mode` requires exactly its configured number of distinct
profiles. Omitting `mode`, or sending `custom`, preserves editable custom
selections from 2 through `SIMULATION_MAX_PERSONAS` (default 30). Standard is
the advertised default for clients. The current persona catalog and the
execution limit are separate: clients may submit validated edited/custom
profiles up to the execution limit.

- `GET /simulation-options`: available profiles, selection limits, named modes
  and the default mode.
- `POST /simulation-runs`: start or reuse a run. A seller-scoped request UUID is idempotent; `fresh: true` explicitly requests new assessments.
- `POST /simulation-runs/preview`: check for matching saved inputs without saving or calling the model. Includes the unsaved `post` editor fields and owned `product_id` alongside run inputs. A changed editor value prevents a match.
- `GET /simulation-runs` and `GET /simulation-runs/{id}`: owned saved runs and reports.
- `GET /simulation-runs/{id}/progress`: evaluation progress without the duplicated full report payload.
- `POST /simulation-runs/{id}/retry`: retry one eligible failed evaluation by `evaluation_id`.
- `POST /simulation-runs/{id}/retry-failed`: retry eligible missing perspectives together using a `request_id` UUID. Completed evaluations are untouched; durable operation history prevents a delayed replay from queuing work again after completion.
- `PATCH /simulation-runs/{id}/report`: save caption annotations; `DELETE` removes a finished report.

Writes require an allowed Origin; every read and write checks seller ownership.
Configuration errors and the six-attempt limit block immediate retries. Progress
responses expose persisted `stage` and `expected_personas` plus queued, running,
processed, completed and failed counters. Report coverage is stored with
completed results; scores are aggregated only from completed verdicts. Preview
and progress do not call the model. A new run or explicitly requested retry can
call it. Reports record model calls, tokens, latency, configured budgets and
provider-reported USD cost when the provider supplies it; a missing cost remains
explicitly untracked rather than estimated.

For the simplest local setup, the worker runs through FastAPI lifespan when
`SIMULATION_WORKER_ENABLED=true`. It starts even without a provider key so
fallback-enabled runs cannot remain queued forever. Queued inputs and completed
outputs survive restarts; uncertain in-flight calls are marked interrupted
instead of silently repeated.

For a separate worker process, disable the embedded worker in the API process
and start both commands in different terminals:

```powershell
# API terminal
$env:SIMULATION_WORKER_ENABLED = "false"
uv run uvicorn main:app --reload

# Worker terminal (explicit startup ignores the API embedding switch)
uv run python worker.py
```

The database queue uses row locks, leases and heartbeats. Multiple worker
processes can safely compete for jobs, while each job respects
`SIMULATION_CONCURRENCY`. Apply migration 0011 before running this version.
Detailed operations, recovery behavior and report verification are documented
in [Simulation jobs, reports, and recovery](docs/simulation-reports.md).

### Report history and comparison

Finished seller-owned reports are available through dedicated report APIs in
addition to the existing simulation-run contract. `GET /reports` supports
immutable snapshot search, status/mode/date filters, newest/oldest ordering and
pagination. `GET /reports/{id}` returns the full report, while
`DELETE /reports/{id}` removes one finished owned report.

`POST /reports/compare` accepts exactly two distinct report UUIDs. Both reports
must be fully completed and owned by the current seller. It returns report-level
overall scores and seven dimension averages, and supports reports produced with
different persona counts. Listing, opening, searching and comparing reports do
not call the model.

### AI persona engine and recommendations (revision 0010)

The current catalog contains **11** built-in buyer perspectives. Selection
supports 2 through the configured maximum, including custom profiles, and the
execution layer validates Quick 5, Standard 10, Deep 20 and Extended 30 modes.
Expanding the curated built-in catalog to cover the larger modes remains future
persona-engine work. See [AI implementation and rubric](docs/ai-simulation.md)
for score definitions, fallback formulas, limits, API examples and test commands.

Apply `uv run alembic upgrade head` before starting the updated worker. Revision
0010 adds only `buyora.persona_adaptations`, its request-uniqueness constraint,
cache index and ownership foreign keys. It does not rewrite customer records.
Run `uv run python scripts/verify_ai_migration.py` to inspect the target schema.
The optional `--apply` mode accepts only a database currently at 0009 or 0010,
applies 0009 -> 0010 when necessary, and verifies the resulting structure without
printing connection secrets.

New endpoints use the same session, seller-ownership and Origin protections:

- `POST /persona-adaptations`: adapt/translate templates immediately with
  `mode: "context"`, or queue a saved variant job with `mode: "ai"`.
- `GET /persona-adaptations/{id}`: poll a saved AI variant job. Context-only
  responses are immediate and have no pollable job.
- `POST /simulation-runs/{id}/revise`: build a saved caption draft from
  `{ "applied": ["delivery", "payment"] }` and the immutable report snapshot.

Reports now include `evaluationSource`, `fallbackReason`, `scoreDrivers` and
`objections` per reaction, plus `trustSignals`, `objectionGroups`, `recommendations`,
`fallbackCount`, `promptVersion` and `usage`. Older reports remain readable.
The frontend exposes template adaptation and AI variants in the persona step,
polls saved jobs, and labels fallback assessments on screen and in print.
Recommendations and revisions for new server reports come from the backend.

<<<<<<< HEAD
Revision `0011` adds `simulation_runs.stage` and `expected_personas`, backfilling
existing runs from their saved inputs. New runs store the requested persona count
before the first insert; retries preserve that count. Apply
`uv run alembic upgrade head` before starting this backend on a database at `0010`.
Databases already at `0011` need only the updated backend code and a restart.
=======
## Backend ownership and contributors

| Member | GitHub | Backend-related Phase 1 contribution |
| --- | --- | --- |
| **Sumaiya Rahman Soma** | [@srs4929](https://github.com/srs4929) | Core database/authentication, ownership, products, images, posts, versions and foundational migrations |
| **Chowdhury Shafahid Rahman** | [@Shafahid](https://github.com/Shafahid) | Typed frontend integration, API workflow verification and user-facing error/progress handling |
| **H. M. Mehedi Hasan** | [@Mehedi26696](https://github.com/Mehedi26696) | Persona/AI services, trust scoring, evaluator validation, fallback, recommendations and revision logic |
| **Abu Bakar** | [@abs-Futy7](https://github.com/abs-Futy7) | Durable simulation/report backend, worker orchestration, retries/recovery, progress, safeguards, report APIs/comparison and B1–B4 integration verification |

## Future backend work

1. Expand realistic, diverse and dynamic personas across behavior, budget, age
   and preference contexts.
2. Add advanced analytics, segmentation, trust analysis, purchase-intention
   analysis and richer historical comparisons.
3. Add AI product-image quality and promotional-presentation analysis.
4. Add competitor pricing, promotion and market-trend analysis using properly
   sourced external data.
5. Add platform-specific optimization for Facebook, Instagram, TikTok and
   WhatsApp.
6. Add Docker, GitHub Actions CI/CD, cloud deployment, monitoring, backups and
   production cost/security controls.

See the [root Phase 1 README](../README.md) for the complete product overview,
team responsibilities and roadmap.

### Image analysis history and storage cleanup

Image analysis requests retain a private reference to the image object used at
request time. Product image responses expose an opaque `image_revision`; image
analysis responses expose the same value and `is_current_image`. A false value
means the analysis belongs to an earlier or deleted image. A null revision or
current-image flag identifies a legacy analysis whose exact image cannot be
established. Legacy analyses without a snapshot fail safely if processed.

Deleting an image prevents new analysis requests, but its existing analyses
remain available to the owning seller while the product is accessible. Objects
referenced by analyses remain private and are retained for the history. Image
replacement schedules old-object cleanup transactionally. A failed cleanup
remains queued and can be retried by an operator on the intended environment:

```powershell
uv run python cleanup_storage.py
```

The command processes up to 100 unreferenced objects per run. It skips objects
still referenced by an active image or analysis. Review the target environment
before running it; it deletes eligible objects from that environment's bucket.

## Recovery of previously pending AI requests

Image-analysis and platform-generation requests now return `503` without saving a
new pending record when durable processing is unavailable. Previously saved
pending records are not changed automatically and remain available through the
existing history endpoints. After a worker and its transactional admission
integration are connected, the team should review those records and explicitly
requeue eligible work or mark it failed through an approved recovery procedure.
Do not enable acceptance based only on a provider callable or configuration flag.
The integration must verify a healthy worker and persist dispatch in the same
database transaction as the request, with recovery for interrupted work.
>>>>>>> 7c316b1109eba01b8e367b41828175e3b27b24e5
