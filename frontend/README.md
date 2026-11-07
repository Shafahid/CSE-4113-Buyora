# Buyora frontend

Buyora helps Bangladeshi social commerce sellers explore simulated buyer reactions before publishing or boosting a promotional post. This directory contains the public landing page, workspace, product/post editors, simulation flow, reports, and account screens.

**Current status: frontend demonstration with browser-local persistence.** There are no API requests, server-backed accounts, AI calls, or database integration in this frontend. The workspace is accessible without authentication. Proposed integration contracts below describe future work, not existing endpoints.

## Stack and setup

| Area        | Implementation                                                         |
| ----------- | ---------------------------------------------------------------------- |
| Framework   | Next.js 16.4.4, App Router                                             |
| UI          | React 19.2.8, TypeScript with strict checking                          |
| Styling     | Global CSS, CSS Modules, Tailwind CSS 4 tooling                        |
| State       | React state and a custom `useSyncExternalStore` store                  |
| Persistence | `localStorage`, with an in-memory fallback                             |
| Graphics    | Inline SVG icons, product illustrations, score rings, and viewer graph |
| Typography  | Local Aeonik files in `public/fonts/`                                  |
| Tests       | Node test runner and the installed TypeScript compiler                 |

Use Node.js **20.9 or newer**, as required by the installed Next.js package, and npm. From `frontend/`:

```sh
npm ci --cache .npm-cache --no-audit --no-fund
npm run dev
```

Open `http://localhost:3000`. Seed data is available immediately. No `.env` file, API key, backend process, or account is required. The project-local npm cache is ignored by Git.

| Command             | Purpose                                        |
| ------------------- | ---------------------------------------------- |
| `npm run dev`       | Development server                             |
| `npm run lint`      | ESLint checks                                  |
| `npm run test:demo` | Domain, persistence, workflow, and graph tests |
| `npm run build`     | Production build and TypeScript checks         |
| `npm start`         | Serve a completed production build             |

Deployment currently needs a Next.js-compatible Node runtime; static export is not configured. `next.config.ts` has no API proxy or integration settings. The `@/` import alias resolves to `src/`.

## Project structure

```text
frontend/
|-- public/
|   |-- fonts/                      Local Aeonik fonts
|   |-- references/                 Design reference images
|   |-- logo.png                    Brand asset
|   |-- avatar-*.png                Buyer persona portraits
|   |-- blue_bg.jpg                 Landing CTA background
|   |-- signin_page_bg.jpg          Account-screen background
|   `-- flowchart.jpg               Product flow reference
|-- src/
|   |-- app/
|   |   |-- layout.tsx              Metadata, theme bootstrap, shared providers
|   |   |-- page.tsx                Public landing page
|   |   |-- globals.css             Theme, shared, responsive, and print styles
|   |   |-- error.tsx               Route error boundary
|   |   |-- not-found.tsx           Not-found screen
|   |   |-- login/page.tsx
|   |   |-- register/page.tsx
|   |   |-- forgot-password/page.tsx
|   |   `-- (workspace)/            Route group; absent from URL paths
|   |       |-- layout.tsx          Shared workspace shell
|   |       |-- dashboard/page.tsx
|   |       |-- products/page.tsx
|   |       |-- posts/page.tsx
|   |       |-- simulate/page.tsx
|   |       |-- reports/[id]/page.tsx
|   |       |-- history/page.tsx
|   |       |-- compare/page.tsx
|   |       `-- settings/page.tsx
|   |-- components/
|   |   |-- workspace.tsx           Sidebar, navigation, profile, storage notice
|   |   |-- ui.tsx                  Shared controls, modals, toasts, theme, art
|   |   |-- dashboard.tsx           Overview metrics and recent reports
|   |   |-- products.tsx            Product management and photo selection
|   |   |-- posts.tsx               Post editor and caption history
|   |   |-- simulation.tsx          Three-step simulation workflow
|   |   |-- report.tsx              Report tabs, retries, revision, print/export
|   |   |-- history.tsx             History and Compare components
|   |   |-- auth.tsx                Login/register/recovery demonstrations
|   |   |-- settings.tsx            Profile, session, export, demo reset
|   |   |-- reaction-map.tsx        Interactive spread graph
|   |   |-- reaction-map.module.css
|   |   |-- count-up.tsx            Overview number and score-arc animation
|   |   |-- landing-reveals.tsx     One-time viewport reveals and stagger groups
|   |   |-- landing-reveals.module.css
|   |   |-- landing-refinements.css Landing styles and circle hover rings
|   |   |-- layout-adjustments.css Shared layout refinements
|   |   |-- footer.tsx
|   |   `-- footer.module.css
|   `-- lib/
|       |-- demo-data.ts            Types, fixtures, evaluation, report helpers
|       |-- store.ts                Subscriptions, mutations, downloads
|       |-- persistent-store.ts     Cached snapshots and storage recovery
|       |-- persistence.ts          Runtime saved-data validation
|       |-- workflow.ts             Workflow validation and compare selection
|       |-- spread-simulation.ts    Deterministic viewer network and states
|       |-- spread-playback.ts      Timeline timing and looping behavior
|       `-- browser-preferences.ts  Reduced-motion and page-visibility hooks
|-- tests/demo.test.mjs
|-- next.config.ts
|-- tsconfig.json
|-- eslint.config.mjs
|-- postcss.config.mjs
|-- package.json
`-- package-lock.json
```

Assets in `public/` are served from `/`. Reference images are design inputs, not application data. `node_modules/`, `.next/`, `.npm-cache/`, and TypeScript build caches are generated files.

## Routes and implemented features

| URL                         | Component      | Current behavior                                                                  |
| --------------------------- | -------------- | --------------------------------------------------------------------------------- |
| `/`                         | `app/page.tsx` | Hero, sample report preview, process steps, personas, CTA                         |
| `/dashboard`                | `Dashboard`    | User greeting, report/product counts, average trust, latest/recent results        |
| `/products`                 | `Products`     | Create, view, edit, duplicate, archive, restore, delete, search, choose photo     |
| `/posts`                    | `Posts`        | Create/edit promotional posts, search, caption versions, start simulation         |
| `/simulate`                 | `Simulation`   | Product/post, audience, editable personas, language, simulated progress           |
| `/reports/[id]`             | `ReportView`   | Overview, audience insights, spread simulation, buyer comments, improve-post tabs |
| `/reports/[id]?view=spread` | `ReportView`   | Open the spread simulation tab directly                                           |
| `/history`                  | `History`      | Search report title/headline, filter platform, sort, delete reports               |
| `/compare`                  | `Compare`      | Compare two fully completed reports and export dimension differences              |
| `/settings`                 | `Settings`     | Profile, theme, local session, workspace export, demo reset                       |
| `/login`, `/register`       | `Auth`         | Update local profile/session flag and open dashboard                              |
| `/forgot-password`          | `Auth`         | Confirmation state only; no email is sent                                         |

Route files mostly compose components; interactive screens are Client Components. The report route resolves asynchronous route/search parameters, then passes the ID to the client. Its report is looked up in browser state, not fetched on the server. Unknown IDs render an empty state.

## State and persistence

`DemoState` contains `version: 1`, `products`, `posts`, `reports`, `draft`, `profile: { name, email }`, and `signedIn`.

```text
Screen -> useDemo() / useWorkspace() -> cached workspace snapshot
Action -> updateDemo(updater) -> localStorage write -> subscriber notification
Simulation -> makeReport() -> saved report -> /reports/{id}
```

- `useDemo()` returns data. `useWorkspace()` returns `{ data, error }` for screens that display storage errors.
- `updateDemo()` accepts a synchronous immutable updater; it is not an async API client.
- `createPersistentStore()` provides a stable server snapshot and loads browser storage lazily during client use.
- Workspace storage key: **`buyora-workspace-v1`**. Appearance key: **`buyora-theme`**, with `light`/`dark` values. Without a stored theme, initial appearance follows the OS.
- Relevant cross-tab storage changes trigger reloads. Invalid data falls back to seed data with a notice. Failed writes retain updated in-memory state with a warning.
- Initial profile: **Soma Rahman / soma@example.com**. Seed reports include `sample-1`, used in landing links. `resetDemo()` restores the seeded workspace, including its profile and reports.
- Everyone using the same browser/origin shares this local workspace. Sign-out only clears the session flag; products/reports remain.
- Workspace/report/comparison downloads use browser-generated JSON. There is no workspace import screen or server export service.

## Data models and conventions

The exported types in [demo-data.ts](src/lib/demo-data.ts) define the current UI shapes. They are not a prescribed database schema.

| Type             | Fields                                                                                                                              |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| `Product`        | `id`, `name`, numeric `price`, `category`, `description`, `features`, `warranty`, `delivery`, `returns`, `image`, `art`, `archived` |
| `Post`           | `id`, `productId`, `headline`, `body`, `offer`, `cta`, `hashtags`, `platform`, `versions: PostVersion[]`                            |
| `PostVersion`    | `id`, previous caption `body`, `createdAt`                                                                                          |
| `Persona`        | `id`, `name`, `role`, `age`, `location`, `need`, `budget`, `color`, `initials`; all strings                                         |
| `Audience`       | `location`, `age`, `interests`, `preferences`, `budget`, `needs`; all strings                                                       |
| `Draft`          | `productId`, full `post`, `audience`, `personas`, `language`, demo-only `failOne`, UI `step`                                        |
| `Reaction`       | Full `persona`, seven-value `scores`, aggregate `score`, `status`, `sentiment`, `comment`, `reason`, `positive`, `question`         |
| `Report`         | `id`, `title`, `createdAt`, full `product`/`post`/`audience` snapshots, `language`, `reactions`, `revised`, `applied`               |
| `Recommendation` | `id`, `title`, `detail`, `priority`, `addition`; generated locally, not stored as a report field                                    |

Preserve these conventions or normalize responses in an adapter:

- IDs are strings; new demo records use `crypto.randomUUID()` where available. Production IDs should be authoritative server values.
- Dates are ISO strings. Display uses `en-GB` and `Asia/Dhaka`; money uses BDT, `৳`, and `en-BD` formatting. There is no currency field.
- String fields exist even when empty. Normalize `null` values before passing data into current consumers.
- `language` is exactly `"en"` or `"bn"` and selects response language. The interface remains English.
- Platform options are `Facebook`, `Instagram`, `Facebook Live`, and `WhatsApp`; the type itself is a string.
- Persona age is a string/range. Budget is descriptive, such as `High sensitivity`, rather than a numeric amount.
- `Product.image` is currently empty or a file data URL. `art` selects an illustration (`tote`, `audio`, `kurta` in seed data). Persona colors/initials are presentation fields.
- `Report.revised` starts as `""`; `applied` starts as `[]` and holds recommendation IDs.
- Draft `step` is `0`, `1`, or `2`. `failOne` demonstrates a failed evaluation. Neither is a production evaluation instruction.

### Score contract

`Reaction.scores` contains exactly **seven finite numbers from 0 to 100**, ordered as follows:

| Index | Dimension       |
| ----- | --------------- |
| 0     | Interest        |
| 1     | Relevance       |
| 2     | Value           |
| 3     | Price fit       |
| 4     | Trust           |
| 5     | Clarity         |
| 6     | Purchase intent |

`evaluate()` computes `Reaction.score` as the rounded mean of these values. `overall(report)` averages **completed** reaction scores and rounds the result; `overall(report, index)` averages that dimension. With no completed reactions, the value is zero. Failed reactions are excluded.

Reaction status is `"complete" | "failed"`. Sentiment is `"Interested" | "Has questions" | "Unconvinced"`. Demo sentiment thresholds are at least 76, at least 60, and below 60 respectively. These are placeholder rules.

A completed reaction compatible with the current UI:

```json
{
  "persona": {
    "id": "budget",
    "name": "Sample buyer",
    "role": "Budget student",
    "age": "18-24",
    "location": "Dhaka",
    "need": "An affordable everyday bag",
    "budget": "High sensitivity",
    "color": "blue",
    "initials": "SB"
  },
  "scores": [80, 78, 70, 60, 65, 85, 70],
  "score": 73,
  "status": "complete",
  "sentiment": "Has questions",
  "comment": "What is the total with delivery?",
  "reason": "The product fits, but delivery costs are unclear.",
  "positive": "The everyday use case is clear.",
  "question": "What is the delivery charge?"
}
```

The validator currently requires scores and text fields even on failed reactions. If the backend returns failures differently, update types, validation, and consumers together rather than fabricate results to fit the demo shape.

Dashboard average trust equally averages each report's trust average. The latest-report panel currently labels `overall(latest)` as **“Virality Score”**; there is no separate virality field or algorithm yet. Agree on production metric semantics before integration.

## Workflow rules

### Products, posts, and versions

- Products need a nonblank name/description and positive finite price. Form limits: name 100 characters, description 2,000, features 1,000, and warranty/delivery/returns 500 each. The price input allows 1–10,000,000 BDT in 0.01 increments.
- Posts need an existing product, nonblank headline, and at least 20 trimmed caption characters. Form maximums: headline 180, body 5,000, offer 250, CTA 200, hashtags 500.
- Caption edits save the **previous body** as a `PostVersion` only when the body changes. No-op saves and edits to other fields alone do not create caption versions.
- Archive/restore changes active simulation availability. Product deletion removes its associated working posts; historical reports retain their snapshots.
- Starting from a product/post pre-fills the draft. Draft fields and wizard position persist locally.

### Simulation and report lifecycle

1. Select an active product and matching post.
2. Review optional audience context.
3. Choose **2–8 personas** with unique IDs and nonblank name, role, age, location, and need. “Regeneration” currently rearranges templates and applies audience context; it does not call AI.
4. Validate the complete draft and clone inputs. Progress increments on a timer, independently of actual evaluation.
5. `makeReport()` creates demo reactions and snapshots. Save the report and working post/version history, then open `/reports/{id}`.

Reports preserve original product, post, audience, and persona data after working-record edits/deletions. Retry replaces only the failed persona's reaction; successful results remain. The current retry uses a local delay and `evaluate()`.

Recommendations use caption text and stored product policies. Revised captions concatenate selected additions with the original post; unverified payment/proof details remain bracketed for seller review. Saving a revision updates working-post caption history without rewriting the report's original post snapshot. Rerunning prepares a draft and creates a new report.

History sorting/filtering and comparisons run client-side over all reports. Comparison requires at least one reaction and every present reaction to be complete. The current report model has no separate job status or expected-result count, so the backend job contract must track unfinished work explicitly. JSON export and browser print/Save as PDF run locally.

### Spread simulation

[spread-simulation.ts](src/lib/spread-simulation.ts) derives **60 fictional viewers over three rounds** from completed persona reactions. It is a deterministic visualization, not measured reach or a sales forecast. Failed reactions do not seed viewers.

States are `unreached`, `viewing`, `ignored`, `engaged`, `objection`, `drop-off`, and `inboxed`. The graph supports playback, replay, stepping, speed, scrubbing, selection, pan/zoom, filters, and keyboard navigation. The compact landing preview loops after a two-second final hold, pauses when the page is hidden, and respects reduced-motion preferences.

No graph endpoint is required to retain the existing visualization with compatible server reactions. If production propagation results are desired, define a separate graph/timeline contract and replace the local model explicitly.
