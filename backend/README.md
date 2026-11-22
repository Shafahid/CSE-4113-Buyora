# Buyora backend

FastAPI backend with SQLAlchemy 2, Psycopg 3, and Alembic, managed with uv.
Supabase provides PostgreSQL hosting; a Supabase Python SDK or API key is not
needed for this database connection.

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
  app/
    main.py             # Application factory, lifespan, middleware, route registration
    api/
      router.py         # Versioned API router
      routes/health.py  # Liveness and database readiness
    core/config.py      # Validated environment settings
    db/
      base.py           # ORM base, private schema, constraint naming
      session.py        # Engine and request-scoped session dependency
    models/__init__.py  # ORM model imports for Alembic discovery
  migrations/
    env.py              # Shared settings and ORM metadata for Alembic
    versions/           # Reviewed, version-controlled schema changes
  tests/                # Configuration, API, transaction, and migration checks
  main.py               # Uvicorn entry point
  alembic.ini
  .env.example
  pyproject.toml
  uv.lock
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

Migration `0009_simulation_execution` adds durable runs, per-persona evaluations and cache pointers in the `buyora` schema. Configure `TOKEN_BD_API_URL`, `TOKEN_BD_API_KEY`, `TOKEN_BD_MODEL` and optionally `LLM_PROVIDER`. LiteLLM configures the provider; LangGraph dispatches selected profiles with bounded concurrency. `LLM_MAX_OUTPUT_TOKENS` defaults to 4096. Never put these credentials in frontend environment variables.

- `GET /simulation-options`: available profiles and selection limits.
- `POST /simulation-runs`: start or reuse a run. A seller-scoped request UUID is idempotent; `fresh: true` explicitly requests new assessments.
- `POST /simulation-runs/preview`: check for matching saved inputs without saving or calling the model. Includes the unsaved `post` editor fields and owned `product_id` alongside run inputs. A changed editor value prevents a match.
- `GET /simulation-runs` and `GET /simulation-runs/{id}`: owned saved runs and reports.
- `GET /simulation-runs/{id}/progress`: evaluation progress without the duplicated full report payload.
- `POST /simulation-runs/{id}/retry`: retry one eligible failed evaluation by `evaluation_id`.
- `POST /simulation-runs/{id}/retry-failed`: retry eligible missing perspectives together using a `request_id` UUID. Completed evaluations are untouched; durable operation history prevents a delayed replay from queuing work again after completion.
- `PATCH /simulation-runs/{id}/report`: save caption annotations; `DELETE` removes a finished report.

Writes require an allowed Origin; every read and write checks seller ownership. Configuration errors and the six-attempt limit block immediate retries. Report coverage is stored with completed results; scores are aggregated only from completed verdicts. Preview and progress do not call the model. A new run or explicitly requested retry can call it.

The worker runs through FastAPI lifespan when `SIMULATION_WORKER_ENABLED` is enabled. Queued inputs and completed outputs survive restarts; uncertain in-flight calls are marked interrupted instead of silently repeated. No migration is required for the preview, compact progress or bulk-retry endpoints beyond revision 0009.
