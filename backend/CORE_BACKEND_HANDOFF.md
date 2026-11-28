# Core backend handoff

This handoff describes the backend APIs and database changes in the current checkout. See [README.md](README.md) for local setup and the running API's `/docs` for full request and response schemas.

## Authentication and API access

The backend uses seller accounts and database-backed sessions. `POST /auth/login` sets an HttpOnly cookie; browser clients should send credentials with requests. State-changing requests must include an allowed `Origin` from `CORS_ORIGINS`. Protected endpoints enforce seller ownership and return `404` for missing or inaccessible resources.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/auth/register` | Create a seller account. |
| POST | `/auth/login` | Sign in and set the session cookie. |
| GET | `/me` | Get the current seller. |
| POST | `/auth/logout` | Revoke the session and clear the cookie. |
| GET | `/api/v1/health/live` | Check that the API process is running. |
| GET | `/api/v1/health/ready` | Check database connectivity. |

## Products and images

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/products` | Create a product. |
| GET | `/products` | List active products, or archived products with `?status=archived`. |
| GET | `/products/{product_id}` | Get product details and its image IDs, sort order, revisions and signed URLs. |
| PATCH | `/products/{product_id}` | Update product fields or archive/restore it. |
| POST | `/products/{product_id}/duplicate` | Copy product details to a new product without copying images. |
| DELETE | `/products/{product_id}` | Soft-delete a product. |
| POST | `/products/{product_id}/images` | Upload a JPEG, PNG or WebP using multipart field `file`, up to 5 MB. |
| PUT | `/products/{product_id}/images/{image_id}` | Replace an image while preserving its ID and sort order. |
| DELETE | `/products/{product_id}/images/{image_id}` | Delete an image from the gallery. |

Product images use private Supabase Storage. Product detail and replacement responses provide signed URLs valid for 300 seconds. Product detail also provides an opaque `image_revision`, which can be matched with image-analysis history. There is no separate image-list endpoint: use product detail.

Replacement writes a new object before updating the image record. Obsolete objects are tracked by cleanup tasks; objects referenced by image analyses are retained. To retry eligible cleanup tasks on the intended environment, run `uv run python cleanup_storage.py` from `backend/`.

## Promotional posts and versions

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/products/{product_id}/posts` | Create a post and its first version. |
| GET | `/products/{product_id}/posts` | List posts for a product. |
| GET | `/posts/{post_id}` | Get a post and its latest version. |
| GET | `/posts/{post_id}/versions` | List saved post versions. |
| GET | `/posts/{post_id}/versions/{version_id}` | Get an exact post version. |
| POST | `/posts/{post_id}/versions` | Save a new post version without overwriting earlier versions. |
| DELETE | `/posts/{post_id}` | Permanently delete a post and its linked versions, simulations, runs and reports. |

## Competitor evidence

These endpoints manage seller-entered observations. Evidence may optionally refer to an owned product. Prices are nonnegative and must be paired with a three-letter uppercase currency; observation dates cannot be in the future. The records are seller-provided observations, not verified or live market prices.

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/competitor-evidence` | Save a competitor observation. |
| GET | `/competitor-evidence` | List records with pagination, search, product, platform and observation-date filters. |
| GET | `/competitor-evidence/{evidence_id}` | Get an owned record. |
| PATCH | `/competitor-evidence/{evidence_id}` | Update supplied fields. |
| DELETE | `/competitor-evidence/{evidence_id}` | Soft-delete a record. |

Example request:

```json
{
  "competitor_name": "TechZone BD",
  "product_name": "Wireless Mouse",
  "competitor_description": "Rechargeable mouse with quiet clicks.",
  "category": "Electronics",
  "price": "950.00",
  "currency": "BDT",
  "offer": "10% discount on two items",
  "platform": "facebook",
  "observed_at": "2025-11-20",
  "notes": "Price observed on the seller's post."
}
```

## Image analysis

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/products/{product_id}/images/{image_id}/analyses` | Save an analysis request for the exact current image object. |
| GET | `/products/{product_id}/images/{image_id}/analyses` | List analysis history with pagination. |
| GET | `/products/{product_id}/images/{image_id}/analyses/{analysis_id}` | Get an analysis, its status and any saved result. |

Request body: `{"language": "en"}`; `bn` is also accepted. When processing is not connected, a new request returns `503` without creating a record. Responses include `image_revision` and `is_current_image` so clients can identify results for an earlier or deleted image. Legacy analyses without a known image revision return `null` for these fields. Existing analysis history remains accessible after image deletion while the product remains accessible.

## Market comparisons

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/products/{product_id}/market-analyses` | Request a comparison using selected seller-owned competitor records. |
| GET | `/products/{product_id}/market-analyses` | List saved analyses with pagination. |
| GET | `/products/{product_id}/market-analyses/{analysis_id}` | Get an analysis, its input snapshot and any saved result. |

Request body: `{"competitor_evidence_ids": [1, 2], "language": "en"}`. One to 20 unique records can be selected, including records linked to another product owned by the seller. The backend snapshots product and competitor details, preserving the observations if the source records are edited or deleted. Missing prices are `null`; prices with different currencies are marked `not_comparable`. The request currently returns `503` when market processing is not configured.

## Platform content variants

| Method | Endpoint | Purpose |
| --- | --- | --- |
| POST | `/posts/{post_id}/variants` | Create a variant or request generation for an exact source post version. |
| GET | `/posts/{post_id}/variants` | List variants with pagination and optional platform filter. |
| GET | `/posts/{post_id}/variants/{variant_id}` | Get a variant and its latest revision. |
| POST | `/posts/{post_id}/variants/{variant_id}/revisions` | Save a seller-written revision. |
| GET | `/posts/{post_id}/variants/{variant_id}/revisions` | List revision history. |

Supported platform values are `facebook`, `instagram`, `tiktok` and `whatsapp`. To save content immediately, include `source_version_id`, `platform`, optional `language`, and a `content` object containing `headline`, `body`, optional `offer`, `call_to_action`, and `hashtags`. Omitting `content` requests generation; it returns `503` without creating a variant while processing is not connected. Creating and revising variants does not overwrite the source post version.

Example seller-written variant:

```json
{
  "source_version_id": 1,
  "platform": "instagram",
  "language": "en",
  "content": {
    "headline": "Everyday essentials",
    "body": "Explore our latest collection.",
    "offer": null,
    "call_to_action": "Message us for details",
    "hashtags": ["shoplocal"]
  }
}
```

## Simulation and reports

The existing simulation workflow includes setup, editable personas, execution, progress, retries and saved reports.

- Setup and personas: `/simulations`, `/simulations/{simulation_id}`, `/simulations/{simulation_id}/personas` and persona detail routes.
- Options and adaptation: `GET /simulation-options`, `POST /persona-adaptations`, `GET /persona-adaptations/{job_id}`.
- Execution: `POST /simulation-runs/preview`, `POST /simulation-runs`, `GET /simulation-runs`, `GET /simulation-runs/{run_id}`, `GET /simulation-runs/{run_id}/progress`, and the `retry`, `retry-failed`, `report`, `revise` and delete routes under a run.
- Reports: `GET /reports`, `GET /reports/{report_id}`, `POST /reports/compare` and `DELETE /reports/{report_id}`.

## Database and migrations

The Alembic revision chain in this checkout ends at `0017`. Revision `0017` adds
nullable competitor provenance and private optional-AI budget reservations.
The detailed Stage 1 package, contract fixtures and acceptance status are in
[docs/phase2](../docs/phase2/handoffs/01-shoma-to-mehdi.md).

| Revision | Database change |
| --- | --- |
| `0001`–`0007` | Base schema, accounts and sessions, products, images, posts and versions, simulations, and personas. |
| `0008`–`0011` | Existing simulation execution, persona adaptations, and job observability changes. |
| `0012` | `public.competitor_evidence`. |
| `0013` | `public.product_image_analyses`. |
| `0014` | `public.platform_variants` and `public.platform_variant_revisions`. |
| `0015` | `public.market_analyses`, including input snapshots. |
| `0016` | Private image snapshot references and `public.storage_cleanup_tasks`. |
| `0017` | Competitor source URL/note and private per-seller AI admission reservations. |

Before upgrading, confirm the target database and back up its data. Configure `DATABASE_URL` and, if needed, `MIGRATION_DATABASE_URL` for the intended environment. From `backend/`:

```powershell
uv sync --locked
uv run alembic current
uv run alembic history
uv run alembic upgrade head
uv run alembic current
```

Review the existing schema and migration output before applying changes to a shared environment. Downgrades of the Phase 2 revisions require manual review to protect existing records. Existing image analyses cannot be reliably backfilled to an old image revision; revision `0016` leaves those references unknown.

## Configuration and handoff

Configuration names and examples are in [.env.example](.env.example) and [app/core/config.py](app/core/config.py). The main backend settings are `DATABASE_URL`, optional `MIGRATION_DATABASE_URL`, `CORS_ORIGINS`, session-cookie settings, and the backend-only `SUPABASE_URL`, `SUPABASE_SECRET_KEY` and `SUPABASE_STORAGE_BUCKET`. Simulation model and worker settings are also documented in `.env.example`. Do not put secrets in frontend code or commit them.

Provider-neutral interfaces for teammate integration are in [image_analysis.py](app/services/image_analysis.py), [market_analysis.py](app/services/market_analysis.py) and [platform_content.py](app/services/platform_content.py). The current API behavior for unavailable processing is described in the relevant sections above.


