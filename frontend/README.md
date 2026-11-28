# Buyora frontend

Buyora helps Bangladeshi social commerce sellers explore buyer reactions before publishing a promotional post. The Next.js workspace integrates with the FastAPI backend for catalog management and saved AI simulations.

## Phase 1 frontend overview

The frontend provides the complete authenticated seller workspace from product
setup to saved-report review:

| Area | Phase 1 implementation |
| --- | --- |
| Account access | Registration, login, logout, session loading, protected routes and expiry handling |
| Catalog | Product create/edit/duplicate/archive/restore/delete, private-image upload and post version history |
| Simulation setup | Product/post selection, audience settings, English/Bangla output and editable persona selection |
| Execution | Real server job creation, persisted progress polling, partial-result handling and retry controls |
| Reports | Server-backed detail, history, search/filter, delete, comparison, dashboard summaries and print/PDF |
| Safety | Fictional-simulation labels, unavailable-score handling and separation of demo data from seller data |

The backend accepts Quick 5, Standard 10, Deep 20 and Extended 30 modes. The
current frontend still uses editable/custom persona selection and the committed
built-in catalog contains 11 profiles, so a complete named four-mode selector
and 30-template browser remain future integration work.

## Current integration

| Feature                                                    | Frontend                                                                | Backend                                                                                |
| ---------------------------------------------------------- | ----------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| Registration, login, logout, current seller                | Connected; session loading, route guard and expiry handling             | Cookie sessions and seller profiles implemented                                        |
| Products                                                   | Server reads; create, edit, duplicate, archive, restore and soft-delete | Implemented with ownership checks                                                      |
| Product photos                                             | Multipart upload, signed previews and removal; up to 5 MB               | Private Storage integration implemented; requires bucket configuration                 |
| Promotional posts                                          | Server reads, create, revise, full saved-version history and delete     | Immutable content versions implemented; deletion also removes linked simulation drafts |
| Simulation drafts and personas | Browser-local editor with selectable, editable buyer profiles | Extensible persona catalog and validated execution inputs |
| Simulation execution, AI, scores and retries | Live per-persona progress, usable coverage and independent/bulk retries | Durable worker, LiteLLM/LangGraph evaluation and seller-scoped cache |
| Reports, history, comparisons and dashboard report metrics | Saved server reports with partial-result guidance; old browser demos remain readable | Immutable input snapshots, saved evaluations and report annotations |
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
- `auth-api.ts`, `catalog-api.ts` and `simulation-api.ts` contain typed endpoint calls. They cover `/auth/*`, `/me`, `/products/*`, `/posts/*`, `/simulations/*`, `/personas/*`, `/persona-adaptations`, `/simulation-runs/*` and `/reports/*`; only health uses `/api/v1`.
- `api-adapters.ts` maps numeric server IDs to UI strings, decimal prices to numbers, features/hashtags to arrays, nulls to UI strings, and backend policy/CTA names to the existing controls.
- `store.ts` loads seller-owned active and archived products, signed image details, posts and saved versions. Successful mutations update the shared snapshot used by all screens. Loading and session generations prevent an old account's results from entering a new account's workspace.
- Saved post revisions contain all content fields. Any content change creates a server version; unchanged saves do not. Existing posts cannot move between products. Restoring history copies saved content into a new revision.
- Product details and photos are separate API operations. If a photo fails after details save, the editor retains the saved product ID and reports partial success so retrying does not create another product. A network failure after a server commits but before its response arrives is inherently ambiguous; refresh before retrying a creation if unsure.
- Product details supply image URLs that expire after five minutes. Workspace data refreshes on focus and every four minutes while visible. Duplication copies details without photos.

`useDemo()` remains the existing screen-facing hook, but products/posts come from the server. `updateDemo()` edits local drafts and report annotations in memory; dedicated API calls persist server changes. Identity and catalog records cannot be replaced through this local updater.

Local previews use `buyora-account-v1:{sellerId}`. They are isolated by account and never import the old shared `buyora-workspace-v1` sample workspace. Signing out clears visible in-memory records. Clearing previews removes only the current account's local draft/reports; server products, images and versions remain. Account scoping prevents accidental mixing on shared browsers; local browser storage is not an access-control boundary against someone using the same browser profile.

## Frontend data flow

```text
Login/register
    -> authenticated workspace
    -> product and promotional post
    -> audience and editable buyer perspectives
    -> create durable simulation run
    -> poll real processing and usable-coverage progress
    -> saved report
    -> history, comparison and print/PDF
```

The API remains the authority for seller identity, products, posts, simulation
runs and new reports. Browser state supports drafts, UI preferences and legacy
sample reports; it does not replace backend ownership checks.

## Simulation assessment boundaries

Starting a simulation first saves its promotional post/version through the API, then queues the selected personas on the backend. Audience settings, personas, product/post snapshots and results are saved to the account. Report recommendations and revised-caption assembly use the saved data without extra model calls; explicitly saving a revised caption creates a separate server post version. The public landing page and older demo reports retain illustrative local reactions.

The seven assessment scores are Interest, Relevance, Value, Price fit, Trust, Clarity and Purchase intent, each from 0 to 100. Failed reactions are excluded from averages. Reports retain original product/post text snapshots. The spread visualization derives 60 fictional viewers over three rounds from completed reactions; it does not measure real reach or predict sales. Language options are English and Bangla; the interface remains English.

## Routes and code

Public routes: `/`, `/login`, `/register`, `/forgot-password`.

Protected workspace routes: `/dashboard`, `/products`, `/posts`, `/simulate`, `/reports/[id]`, `/history`, `/compare`, `/settings`. The client guard controls screen visibility; backend session and ownership checks enforce access to server data.

`src/app/` contains routes, `src/components/` contains the existing screens and shared UI, and `src/lib/` contains API/state/domain helpers. Styling remains in global CSS and CSS Modules with local Aeonik fonts. `demo-data.ts`, `workflow.ts`, `spread-simulation.ts` and `spread-playback.ts` support the remaining demo functionality.

## Checks

```powershell
npm test
npm run test:integration
npm run lint
npx tsc --noEmit
npm run build
```

`npm test` covers domain logic, adapters, request errors, multipart headers and account-local state. `test:demo` still runs the original demo-domain checks.

`npm run test:integration` requires `backend/.venv` and starts the real FastAPI routes on an ephemeral loopback port with an isolated temporary file-backed SQLite database and fake image storage. It exercises the frontend API client/store across authentication, reloads, product actions, uploads/removal, post revisions, no-op saves, deletion and seller isolation. It never loads `.env` or contacts Supabase. SQLite and fake storage do not verify PostgreSQL migrations, production concurrency, real Storage permissions, deployed browser CORS or cookie policies.

At the current Phase 1 handoff, **37 frontend unit tests** and the isolated live
API integration test pass. ESLint, TypeScript checking and the Next.js
production build also complete successfully.

## Current limitations

Remaining work includes the full four-mode selector and 30-template persona
browser, account-saved persona presets, profile editing and password recovery.
Production queue concurrency, deployed cookie/CORS behavior, accessibility and
cross-browser print output need deployment-specific checks.



## Simulation experience

The final setup step checks for a saved run using the current product, exact post version, editor contents, audience, selected personas, language and model/rubric configuration. Preview does not save or enqueue work. Starting checks the cache again; choosing a fresh simulation explicitly bypasses it.

Progress distinguishes processing completion from usable assessment coverage. Compact polling fetches the full report once the run finishes. Reports exclude failed evaluations from scores and display unavailable scores when none finished. Bulk retry preserves completed outputs and uses a request UUID persisted in evaluation history to prevent a repeated HTTP request from scheduling the same operation twice. Service configuration failures need attention before retrying; exhausted retries require a fresh run.

The spread animation expands completed persona scores into 60 illustrative viewers. It makes no independent model calls and is not a reach forecast.

## Print and PDF reports

Open a saved report and choose **Print / Save PDF**, then select the browser's PDF destination or a printer. The A4 report has a branded executive summary, numbered contents guide, dimension scores, publishing checklist, persona scorecard, buyer explanations and evidence, immutable product/post and audience snapshots, and a revised caption when saved. Footer page numbers are supported by Chromium's print engine. Print colors and font sizes are independent of workspace theme and text scaling; missing evaluations display as unavailable and are excluded from scores. Long captions and feedback continue across pages without clipping.

The print document lives in `src/components/print-report.tsx` with separate print styles in `print-report.module.css`; workspace print isolation remains in `globals.css`. All content is derived from the saved report without additional model requests.

## Manual Phase 1 walkthrough

1. Open `/register` or `/login`, then confirm protected routes become available.
2. Open `/products`; create a product, upload an image, edit it, and exercise
   duplicate/archive/restore actions.
3. Open `/posts`; create a promotional post, revise it, and inspect its saved
   version history.
4. Open `/simulate`; select a product/post, configure the audience and personas,
   start a run, and verify that progress changes from backend polling rather than
   a visual-only timer.
5. Open the completed `/reports/{id}` page; verify reactions, seven scores,
   fallback labels, recommendations, immutable snapshots and Print / Save PDF.
6. Open `/history`; search/filter reports, reopen one and delete a test report.
7. Open `/compare`; select two completed reports and verify overall and
   seven-dimension comparisons.
8. Sign in as a second seller and verify that the first seller's products,
   simulation runs and reports are not visible.

## Frontend ownership and contributors

| Member | GitHub | Phase 1 responsibility reflected in the frontend |
| --- | --- | --- |
| **Sumaiya Rahman Soma** | [@srs4929](https://github.com/srs4929) | Supplied the authenticated product/post APIs, ownership rules and immutable versions consumed by the UI |
| **Chowdhury Shafahid Rahman** | [@Shafahid](https://github.com/Shafahid) | Owned the Next.js screens, typed API client, session flow, catalog integration, simulation/report workflow, history, comparison and UI tests |
| **H. M. Mehedi Hasan** | [@Mehedi26696](https://github.com/Mehedi26696) | Supplied persona, scoring, objection, fallback, recommendation and caption-revision contracts displayed by the UI |
| **Abu Bakar** | [@abs-Futy7](https://github.com/abs-Futy7) | Supplied the B1–B4 job progress, retry, report history/detail/delete and comparison APIs integrated into the workflow |

## Future frontend work

1. Expose more realistic, diverse and dynamic personas across age, behavior,
   budget and preference contexts, including all named simulation modes.
2. Build advanced analytics for buyer behavior, audience segmentation, trust,
   purchase intention and richer report comparisons.
3. Add product-image quality, visual-attractiveness and presentation analysis.
4. Present competitor pricing, promotional-strategy and market-trend insights
   with clear source and freshness information.
5. Add platform-specific caption and content optimization for Facebook,
   Instagram, TikTok and WhatsApp.
6. Support the production deployment work with environment-aware builds,
   automated browser tests, observability and reliable cloud delivery.

See the [root Phase 1 README](../README.md) for the complete project status,
team ownership and shared roadmap.
