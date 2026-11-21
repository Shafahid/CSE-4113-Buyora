# Core backend handoff

This reference describes the current `main` checkout. Full setup and commands are in the [backend README](README.md).

## What’s implemented

| Feature | Current status |
| --- | --- |
| Authentication | Seller registration, login, session lookup and logout; passwords are hashed and sessions use an HttpOnly cookie.|
| Products and images | Seller-owned create, list, detail, edit, archive/restore, duplicate and soft-delete. Images can be uploaded and removed; product detail returns short-lived signed URLs. |
| Promotional posts | Create a post, list posts, read a post or version, and save new versions without changing earlier ones. |
| Simulation drafts | Create, load and update audience settings and language for a fixed post version. Starting or running a simulation is pending. |
| Personas | List, add, edit, select/deselect and remove saved personas. Writes require a draft; reads also work after it starts. Automated generation is pending. |

## Database tables



| Full table name | Purpose | Key foreign keys | Revision |
| --- | --- | --- | --- |
| `public.users` | Seller account and password hash | — | [0002](migrations/versions/0002_auth.py) |
| `public.user_profiles` | Seller display name | `user_id → public.users.id` | 0002 |
| `public.auth_sessions` | Hashed session tokens, expiry and revocation | `user_id → public.users.id` | 0002 |
| `public.products` | Seller-owned product details and status | `seller_id → public.users.id` | [0003](migrations/versions/0003_products.py) |
| `public.product_images` | Product image object keys and order | `product_id → public.products.id` | [0004](migrations/versions/0004_product_images.py) |
| `public.posts` | Promotion linked to a product | `product_id → public.products.id` | [0005](migrations/versions/0005_posts.py) |
| `public.post_versions` | Saved promotion content and version number | `post_id → public.posts.id` | 0005 |
| `public.simulations` | Simulation status, selected post version and audience setup | `post_version_id → public.post_versions.id` | [0006](migrations/versions/0006_simulations.py) |
| `public.simulation_personas` | Saved personas and selection flags | `simulation_id → public.simulations.id` | [0007](migrations/versions/0007_simulation_personas.py) |
| `public.persona_evaluations` | Evaluation status, scores and reaction data; **no model or API in this checkout** | `persona_id → public.simulation_personas.id` | None in this checkout |

`public.persona_evaluations` was observed in the configured database; its presence in other databases is not confirmed. Migration application status on shared Supabase is unconfirmed. Revisions 0002–0007 create missing feature tables or validate and reuse existing ones; review the revisions and database before applying them.

## API reference

Except for auth registration/login, health and documentation, feature routes require a valid session cookie. Browser clients must send credentials, for example `credentials: "include"`. State-changing routes require an `Origin` accepted by `CORS_ORIGINS`. Seller-owned resources return `404` when missing or inaccessible. See [auth routes](app/api/routes/auth.py) for `get_current_user` and the origin check.

### Authentication and health

| Method and path | What it does / main input or output |
| --- | --- |
| `POST /auth/register` | Create seller and profile; input `email`, `password`, `display_name`. |
| `POST /auth/login` | Verify credentials, set session cookie and return public profile. |
| `GET /me` | Return the current seller’s ID, email and display name. |
| `POST /auth/logout` | Revoke the session and clear the cookie; returns `204`. |
| `GET /` | Return the API welcome message. |
| `GET /api/v1/health/live` | Check the API process. |
| `GET /api/v1/health/ready` | Check database connectivity. |

### Products and images

| Method and path | What it does / main input or output |
| --- | --- |
| `POST /products` | Create an owned product with name, category and nonnegative price. |
| `GET /products` | List active products; `?status=archived` lists archived products. |
| `GET /products/{product_id}` | Return an owned product and its images with signed URLs. |
| `PATCH /products/{product_id}` | Update supplied fields or set status to `active` or `archived`. |
| `POST /products/{product_id}/duplicate` | Copy product details into a new active product, without images. |
| `DELETE /products/{product_id}` | Soft-delete the product and retain linked data; returns `204`. |
| `POST /products/{product_id}/images` | Upload one JPEG, PNG or WebP as multipart field `file`, up to 5 MB. |
| `DELETE /products/{product_id}/images/{image_id}` | Remove an owned image from Storage and the database; returns `204`. |

### Promotional posts and versions

| Method and path | What it does / main input or output |
| --- | --- |
| `POST /products/{product_id}/posts` | Create a post and version 1 from seller-written content. |
| `GET /products/{product_id}/posts` | List product posts with latest version ID, number, headline and platform. |
| `GET /posts/{post_id}` | Return a post and its latest saved version. |
| `GET /posts/{post_id}/versions` | List saved versions, newest first. |
| `GET /posts/{post_id}/versions/{version_id}` | Return the exact saved version belonging to the post. |
| `POST /posts/{post_id}/versions` | Save a new version; earlier versions remain unchanged. |

### Simulation drafts and personas

| Method and path | What it does / main input or output |
| --- | --- |
| `POST /simulations` | Create a draft from `post_version_id`; optional `audience_settings` and `language`. |
| `GET /simulations/{simulation_id}` | Reload an owned simulation’s setup. |
| `PATCH /simulations/{simulation_id}` | Update a draft’s language or replace audience settings; `{}` clears the supplied audience object. |
| `GET /simulations/{simulation_id}/personas` | List saved personas; returns `[]` when none exist. |
| `POST /simulations/{simulation_id}/personas` | Add a persona to a draft; returns the saved persona. |
| `PATCH /simulations/{simulation_id}/personas/{persona_id}` | Edit supplied fields or set `is_selected`; characteristic fields are merged. |
| `DELETE /simulations/{simulation_id}/personas/{persona_id}` | Remove a persona from a draft; returns `204`. |

## Handoff and pending work

- **Simulation teammate:** drafts pin `post_version_id`; personas belong to `simulation_id`. Use [simulation routes](app/api/routes/simulations.py), [persona routes](app/api/routes/personas.py), [simulation model](app/models/simulation.py), [persona model](app/models/simulation_persona.py), and revisions [0006](migrations/versions/0006_simulations.py)–[0007](migrations/versions/0007_simulation_personas.py). Persona input examples are in the [README](README.md#simulation-personas).
- **Frontend teammate:** use the API tables above, send the cookie and trusted origin, and handle `401`, `403`, `404`, `409` and `422` responses. Draft audience updates replace the whole supplied object; omitting it preserves the saved object.
- **Pending:** persona generation/regeneration, simulation execution and evaluation jobs, retries, scoring and report APIs. The existing `public.persona_evaluations` table is not yet integrated. Social publishing, AI-written post revisions, password recovery and post deletion are also pending.
- **Checks:** [auth](tests/test_auth.py), [products](tests/test_products.py), [images](tests/test_product_images.py), [posts](tests/test_posts.py), [simulations](tests/test_simulations.py), [personas](tests/test_personas.py), and [migrations](tests/test_migrations.py). Tests use isolated SQLite and offline PostgreSQL migration SQL; check PostgreSQL behavior separately.
- **Configuration:** [settings](app/core/config.py) and [.env.example](.env.example) cover the database, CORS, cookie settings and private Supabase Storage. Keep secrets on the backend. Use the [README](README.md) for setup, migration and run commands.
