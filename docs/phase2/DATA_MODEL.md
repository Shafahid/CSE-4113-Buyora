# Stage 1 data model and migration checklist

## Ownership and persistence

| Table | Location | Relationships and invariants |
| --- | --- | --- |
| `product_images` | public | Owned through product; private object reference; replace preserves ID/order. |
| `competitor_evidence` | public | Seller FK, optional owned-product FK; nonnegative price/currency pair; soft deletion; source URL/note/date. |
| `product_image_analyses` | public | Seller/product FKs; nullable active-image FK; permanent original ID and private snapshot key; completed-only result. |
| `market_analyses` | public | Seller/product FKs; immutable JSON product/evidence/source/date snapshot; completed-only result. |
| `platform_variants` | public | Exact source-post-version FK; constrained platform/language/state. |
| `platform_variant_revisions` | public | Variant FK; unique `(variant_id, revision_number)`; append-only seller/AI/fallback content. |
| `storage_cleanup_tasks` | public | Unique object reference; retryable cleanup skips referenced objects. |
| `ai_request_reservations` | buyora | Seller FK; unique `(kind,resource_id)`; positive reserved tokens; policy JSON and timestamp. |
| `ai_jobs` | buyora | Unique reservation/resource; immutable payload, configuration fingerprint, lease token/deadline, safe error and usage. |
| `ai_worker_heartbeats` | buyora | Worker configuration, advertised capabilities and freshness index. |

Public-schema placement preserves established Phase 1 relationships. Runtime
ownership is enforced in authenticated FastAPI routes. Migration grants revoke
access from PUBLIC and Supabase anon/authenticated roles; these tables must not
be used as an unrestricted Supabase Data API. Use a backend-only runtime role.
Private image references never appear as standalone API storage-key fields.

Owner/date and product/source indexes support paginated histories. Reservations
use `(seller_id, created_at)` for the rolling-minute/daily queries. PostgreSQL
seller row locks serialize admission across processes; acquire the seller before
post/image locks. Production uses the default READ COMMITTED isolation level.

## Versioning and historical data

AI input/output and attachment schemas use `schema_version:"1.0"`. Unknown
versions fail validation. Historical JSON missing this field reads as version
1.0. Provider-neutral Pydantic schemas live in `backend/app/services/` and
`backend/app/schemas/phase2.py`; generated JSON Schema files are in `schemas/`.
Content revision numbers remain distinct from contract schema versions.

Optional report findings are immutable copies in simulation-run inputs, with
completion timestamps, result versions and provenance. No dynamic join rewrites
a saved report. Legacy reports can omit optional findings. Legacy image analyses
without an exact image revision remain unknown and fail safely if dispatched.

## Migration history

- 0012: competitor observations.
- 0013: image-analysis requests/history.
- 0014: platform variants/revisions.
- 0015: market-analysis snapshots.
- 0016: immutable image references and durable storage cleanup.
- 0017: nullable competitor `source_url`/`source_note`; private AI reservations.
- 0018: private optional-AI queue/heartbeats, nullable public analysis/variant
  `processing_metadata`, and explicitly labeled fallback revision origin.

0017 is additive. Existing competitor records keep null provenance, and existing
products, posts, simulations and reports are not rewritten. No schema mutation
occurs at API startup.

## Apply and verify

1. Confirm the intended environment, backup/restore access, backend version and
   `DATABASE_URL`; set `MIGRATION_DATABASE_URL` only for the same database.
2. Run isolated migration and API tests before upgrading a shared database.
3. From `backend/`, run `uv run alembic current`, `uv run alembic heads`, then
   `uv run alembic upgrade head` as a separate deployment step.
4. Confirm revision 0018, provenance/processing metadata, reservation/queue tables,
   indices and restricted grants. Run `uv run python scripts/check_simulation_setup.py`
   and `uv run python scripts/check_stage2_setup.py --provider`.
5. Restart API/worker and smoke-test login, existing product/post/report access,
   image history and competitor CRUD. Optional generation requires a fresh matching
   capable worker; vision also requires a validated input-budget strategy.

## Downgrade and recovery policy

Phase 2 revisions deliberately refuse automatic destructive downgrades because
saved observations, analyses and reservations may contain data. The integration
suite verifies that refusal leaves both data and revision unchanged. This is
the reviewed policy, not an untested reversible downgrade claim.

For an application rollback, keep the additive schema and deploy the previous
compatible application. For schema rollback, export affected data, review the
exact rollback SQL and restore a verified backup into an isolated database
first. Never stamp an unverified schema revision or drop a shared database to
make a migration pass.
