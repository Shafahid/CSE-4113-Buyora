# Buyora frontend

Buyora helps Bangladeshi social commerce sellers explore buyer reactions before publishing a promotional post. Existing Next.js screens now partially integrate with the FastAPI backend.

## Current integration

| Feature                                                    | Frontend                                                                | Backend                                                                                |
| ---------------------------------------------------------- | ----------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Registration, login, logout, current seller                | Connected; session loading, route guard and expiry handling             | Cookie sessions and seller profiles implemented                                        |
| Products                                                   | Server reads; create, edit, duplicate, archive, restore and soft-delete | Implemented with ownership checks                                                      |
| Product photos                                             | Multipart upload, signed previews and removal; up to 5 MB               | Private Storage integration implemented; requires bucket configuration                 |
| Promotional posts                                          | Server reads, create, revise, full saved-version history and delete     | Immutable content versions implemented; deletion also removes linked simulation drafts |
| Simulation drafts and personas                             | Browser-local setup; API wiring pending                                 | Draft and persona CRUD implemented                                                     |
| Simulation execution, AI, scores and retries               | Explicit demo preview                                                   | Pending                                                                                |
| Reports, history, comparisons and dashboard report metrics | Account-scoped local demo reports                                       | Report storage and APIs pending                                                        |
| Profile updates and password recovery                      | Profile is read-only; recovery is a preview                             | Update/recovery endpoints pending                                                      |

Products and posts have no local demo fallback. Server failures show errors and retry controls. The public landing page still uses sample illustrations and reactions.

## Run locally

Requires Node.js 20.9+ and the backend dependencies described in [backend/README.md](../backend/README.md).

```powershell
# From frontend/
npm ci --cache .npm-cache --no-audit --no-fund
npm run dev
```

Start FastAPI separately on port 8000 after configuring the backend and reviewing/applying its migrations. No migration is run by the frontend or the test fixture. Open `http://localhost:3000` and sign in or register. Workspace routes redirect to login when the API reports an unauthenticated session.

The API base defaults to the browser's protocol and hostname on port 8000. For a different API location, add this to an ignored `frontend/.env.local`, then restart Next.js:

```dotenv
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Only public configuration belongs in `NEXT_PUBLIC_*` variables. Database credentials and Supabase secrets stay in `backend/.env`. Set backend `CORS_ORIGINS` to the exact frontend origin. Both servers should use the same hostname locally. HTTPS deployments need secure cookies; cross-site HTTPS also needs `SameSite=none`. Cookies are HttpOnly and every API call sends credentials. Browser requests supply Origin automatically.

The example backend environment now has valid local cookie defaults and placeholder database values. The previously committed credential-like values were removed from the example file. If they were genuine, the owner must rotate the database password; editing the file does not remove Git history or revoke credentials.

## API contract and state

- `src/lib/api-schema.ts` is generated from the current FastAPI OpenAPI schemas. Regenerate from `backend/` with `uv run python scripts/export_frontend_contract.py`; this does not connect to the database.
- `api-client.ts` handles cookies, JSON/multipart requests, timeouts, network failures, 204 responses and API errors. FastAPI 422 errors retain field paths; 401 responses invalidate the workspace session.
- `auth-api.ts` and `catalog-api.ts` contain typed endpoint calls. Feature routes are `/auth/*`, `/me`, `/products/*` and `/posts/*`; only health uses `/api/v1`.
- `api-adapters.ts` maps numeric server IDs to UI strings, decimal prices to numbers, features/hashtags to arrays, nulls to UI strings, and backend policy/CTA names to the existing controls.
- `store.ts` loads seller-owned active and archived products, signed image details, posts and saved versions. Successful mutations update the shared snapshot used by all screens. Loading and session generations prevent an old account's results from entering a new account's workspace.
- Saved post revisions contain all content fields. Any content change creates a server version; unchanged saves do not. Existing posts cannot move between products. Restoring history copies saved content into a new revision.
- Product details and photos are separate API operations. If a photo fails after details save, the editor retains the saved product ID and reports partial success so retrying does not create another product. A network failure after a server commits but before its response arrives is inherently ambiguous; refresh before retrying a creation if unsure.
- Product details supply image URLs that expire after five minutes. Workspace data refreshes on focus and every four minutes while visible. Duplication copies details without photos.

`useDemo()` remains the existing screen-facing hook, but products/posts come from the server. `updateDemo()` can only change local simulation drafts and demo reports. Identity and server records cannot be replaced through this local updater.

Local previews use `buyora-account-v1:{sellerId}`. They are isolated by account and never import the old shared `buyora-workspace-v1` sample workspace. Signing out clears visible in-memory records. Clearing previews removes only the current account's local draft/reports; server products, images and versions remain. Account scoping prevents accidental mixing on shared browsers; local browser storage is not an access-control boundary against someone using the same browser profile.

## Simulation preview boundaries

Starting a demo simulation first saves its promotional post/version through the API, then generates illustrative reactions locally. Audience settings, selected personas and the resulting report remain browser-local until the simulation API integration is implemented. Demo retries, recommendations and revised-caption generation remain local; explicitly saving a revised caption creates a real server post version.

The seven demo scores are Interest, Relevance, Value, Price fit, Trust, Clarity and Purchase intent, each from 0 to 100. Failed reactions are excluded from averages. Reports retain original product/post text snapshots. The spread visualization derives 60 fictional viewers over three rounds from completed reactions; it does not measure real reach or predict sales. Language options are English and Bangla; the interface remains English.

## Routes and code

Public routes: `/`, `/login`, `/register`, `/forgot-password`.

Protected workspace routes: `/dashboard`, `/products`, `/posts`, `/simulate`, `/reports/[id]`, `/history`, `/compare`, `/settings`. The client guard controls screen visibility; backend session and ownership checks enforce access to server data.

`src/app/` contains routes, `src/components/` contains the existing screens and shared UI, and `src/lib/` contains API/state/domain helpers. Styling remains in global CSS and CSS Modules with local Aeonik fonts. `demo-data.ts`, `workflow.ts`, `spread-simulation.ts` and `spread-playback.ts` support the remaining demo functionality.

## Checks

```powershell
npm test
npm run test:integration
npm run lint
npm run build
```

`npm test` covers domain logic, adapters, request errors, multipart headers and account-local state. `test:demo` still runs the original demo-domain checks.

`npm run test:integration` requires `backend/.venv` and starts the real FastAPI routes on an ephemeral loopback port with an isolated shared in-memory SQLite database and fake image storage. It exercises the frontend API client/store across authentication, reloads, product actions, uploads/removal, post revisions, no-op saves, deletion and seller isolation. It never loads `.env` or contacts Supabase. SQLite and fake storage do not verify PostgreSQL migrations, production concurrency, real Storage permissions, deployed browser CORS or cookie policies.

## Pending work

Frontend: connect simulation draft/persona APIs; replace demo progress, generation, retries and reports when their APIs exist; connect dashboard/history/comparison data to those reports; connect profile editing and recovery once supported.

Backend: implement simulation execution/jobs, persona generation, AI evaluation and seven-dimension scoring, independent retries, immutable report snapshots and APIs, report-based metrics, profile updates and password recovery. Validate migrations against an isolated PostgreSQL instance and configure real private Storage before deployment.

The production build also reports an existing Next.js security advisory for the installed version. Dependency upgrading remains a separate follow-up.
