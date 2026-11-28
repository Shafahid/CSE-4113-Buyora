# Stage 1 handover checklist

Stage 2 implementation and its current runtime limitations are recorded in
[Mehdi's handoff](handoffs/02-mehdi-to-abu-bakar.md). This checklist retains the
Stage 1 verification record; it does not imply team acceptance or PR merge.

Status: technical implementation verified (260 backend tests passed); team
approval and PR merge are pending.
This file records evidence, not inferred meeting attendance or reviewer consent.

## Implementation evidence

- [x] Authenticated image upload/replace/list/delete, byte validation, 5 MB limit,
      private signed references, ownership and cleanup/history tests.
- [x] Competitor CRUD, pagination/search/date/platform filters, source URL/note,
      observation timestamps, validation and seller isolation.
- [x] Four platform variants and append-only revisions preserving source posts.
- [x] Image/market/platform request/read APIs and typed provider-neutral hooks.
- [x] Unavailable durable processing returns 503 without accepting stranded work;
      test doubles only produce example AI results.
- [x] Shared database-backed per-seller rolling-minute and UTC-day token limits,
      transaction rollback on failed dispatch, Retry-After and saved budgets.
- [x] Version 1.0 contracts, legacy JSON defaults, immutable optional findings in
      simulation/report snapshots and source/date preservation.
- [x] OpenAPI export, JSON Schemas and example-only fixtures with contract tests.
- [x] Additive migration 0017 and documented manual-review downgrade policy.
- [x] Full backend pytest, Ruff lint/format, PostgreSQL migration/concurrency/API
      checks and frontend TypeScript validation passed on 2026-11-28.
- [x] Configured application database upgraded to 0017; provenance columns,
      reservation table/index/uniqueness/grants and worker schema verified.

## Reproducible verification

From `backend/`:

```powershell
uv sync --locked
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

For PostgreSQL checks, use a disposable localhost server. The test fixture
creates/drops only a unique `buyora_test_<uuid>` database. It refuses remote
hosts or a non-`postgres` admin database and never reads the developer `.env`.

```powershell
docker run --detach --name buyora-stage1-test --env POSTGRES_PASSWORD=local-test-only --publish 127.0.0.1:55439:5432 postgres:17
$env:BUYORA_TEST_POSTGRES_URL = "postgresql://postgres:local-test-only@127.0.0.1:55439/postgres?sslmode=disable"
uv run pytest -q tests/test_postgres_migrations.py
docker stop buyora-stage1-test
docker rm buyora-stage1-test
```

The password above belongs only to the disposable local example; never reuse it
for a shared database. Ordinary pytest skips these three tests without the opt-in
variable. PostgreSQL evidence includes clean upgrades, preservation of existing
records, safe downgrade refusal, index presence and concurrent quota admission.
Final results are recorded in [the handoff](handoffs/01-shoma-to-mehdi.md).

## Team and release acceptance — pending human evidence

- [ ] Shoma records Stage 0 decisions and contract-review PR link.
- [ ] Mehdi approves input/output schemas and verifies fixture callable examples.
- [ ] Abu Bakar approves report attachment/job fields.
- [ ] Shafayet approves UI-required data and error/status handling.
- [ ] Relevant implementation/documentation PRs are merged into main with review
      and passing checks; record their URLs in the handoff.
- [ ] Confirm backup/restore readiness and revision 0017 for the intended release
      environment (the configured application database is already verified).
- [ ] Mehdi records the date and acceptance of the Stage 1 handover.

Do not mark these entries complete on behalf of teammates. Until recorded,
the package is ready for review rather than an accepted/merged handover.
