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
   them in `app/models/__init__.py`. Tables inherit the private `buyora` schema.
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
at API startup. The first migration only creates the schema; feature tables and
authentication are added with their features.

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
