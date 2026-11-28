# Buyora — Phase 1

Buyora is an AI-assisted pre-publish buyer-reaction simulator for Bangladeshi
social-commerce sellers. A seller can save a product and promotional post,
select fictional buyer perspectives, run an AI-backed simulation, and review
likely questions, objections, trust gaps and content-improvement suggestions
before publishing or boosting the post.

Phase 1 delivers the authenticated product-to-report workflow, durable
background simulation processing, deterministic recovery when the model is
unavailable, immutable saved reports, report history and comparison, and a
responsive Next.js workspace connected to a FastAPI backend.

> Buyora produces fictional AI simulations. Reactions, scores and the 60-viewer
> spread visualization are not real customer feedback, calibrated purchase
> probabilities, reach forecasts or guarantees of sales.

## Phase 1 status

| Area | Implemented |
| --- | --- |
| Seller accounts | Registration, login, logout, current-user session and seller isolation |
| Products | Create, read, update, archive/restore, duplicate, soft-delete and private image upload/removal |
| Promotional posts | Create, read, permanently delete and preserve immutable caption versions |
| Simulation setup | Audience, language, editable persona selection and contextual/AI persona adaptation |
| Simulation modes | Backend validation for Quick 5, Standard 10, Deep 20 and Extended 30, plus custom 2–30 selection |
| Job processing | Durable queue, persisted stages, bounded concurrency, retry/backoff, idempotency, leases and restart recovery |
| AI evaluation | Seven scores, comments, reasons, positives, questions, objections, evidence and score drivers |
| Safeguards | Deterministic fallback, token/model-call budgets, retry caps, usage/latency and provider-cost metadata when available |
| Reports | Immutable snapshots, recommendations, caption revision, history, search/filter, deletion and seven-dimension comparison |
| Frontend | Dashboard, products, posts, simulation progress, reports, history, comparison, settings and print/PDF output |
| Verification | Backend unit/API/migration tests, frontend unit/integration tests, lint, type-check and production build |

The execution backend supports up to 30 submitted personas. The currently
committed built-in catalog contains 11 curated profiles, and the frontend still
uses editable/custom selection rather than a complete four-mode selector.
Expanding the built-in catalog and exposing all four named modes directly in the
UI remain integration work.

## How Buyora works

```text
Seller account
    ↓
Product + private images
    ↓
Promotional post + immutable version
    ↓
Audience + selected fictional buyer personas
    ↓
Durable simulation job
    ↓
Bounded worker → AI evaluator → deterministic fallback when required
    ↓
Independent saved reactions + real progress
    ↓
Immutable report → recommendations → history → comparison → print/PDF
```

The backend freezes the product, exact post version, audience, language,
personas, model identity, prompt/rules versions and execution policy when a run
is created. Later product edits or post revisions do not rewrite an old report.

## Technology stack

### Frontend

- Next.js 16 App Router
- React 19 and TypeScript
- CSS Modules and global CSS
- Browser print/PDF support
- Typed FastAPI contract generated from OpenAPI

### Backend

- Python 3.13
- FastAPI and Pydantic
- SQLAlchemy 2 and Alembic
- PostgreSQL hosted through Supabase
- Private Supabase Storage for product images
- LiteLLM provider adapter and LangGraph worker orchestration
- Pytest and Ruff

## Repository structure

```text
CSE-4113-Buyora/
├── backend/
│   ├── app/
│   │   ├── api/routes/        # Authentication, catalog, simulation and report APIs
│   │   ├── core/              # Configuration, storage and persona diversity
│   │   ├── db/                # SQLAlchemy engine/session setup
│   │   ├── models/            # Persistent application models
│   │   ├── schemas/           # Execution and report contracts
│   │   └── services/          # AI, worker, scoring, recommendations and reports
│   ├── migrations/versions/   # Reviewed Alembic revisions 0001–0011
│   ├── tests/                 # Backend, worker, migration and lifecycle tests
│   ├── docs/                  # AI and simulation/report operational documentation
│   └── worker.py              # Standalone durable worker entry point
├── frontend/
│   ├── src/app/               # Public and authenticated App Router pages
│   ├── src/components/        # Workspace, simulation and report UI
│   ├── src/lib/               # Typed API clients, state and domain helpers
│   └── tests/                 # Unit and live isolated API integration tests
└── docs/
    ├── PRODUCT_REQUIREMENTS_DOCUMENT.md
    └── Buyora_Phase_1_Member_Tasks.md
```

## Phase 1 capabilities

### Authentication and ownership

Passwords are Argon2-hashed and sessions are stored server-side. The browser
receives an HttpOnly session cookie. Protected operations enforce seller
ownership in the backend; inaccessible resources return `404` to avoid exposing
another seller's data. State-changing browser requests require an allowed
Origin.

### Product and post management

Products support descriptive fields, BDT pricing, features, delivery, warranty,
return policy, lifecycle status and private images. Promotional posts are linked
to an owned product. Every meaningful content edit creates a new immutable post
version, allowing simulations to reference the exact tested caption.

### Personas and AI evaluation

Persona profiles are fictional buying perspectives, not real demographic
records. Profiles can be selected and edited, adapted to saved product/post and
audience context, and evaluated in English or Bangla. Duplicate identities and
near-duplicate priorities are rejected.

Each completed reaction contains seven scores from 0–100:

1. Interest
2. Relevance
3. Value
4. Price fit
5. Trust
6. Clarity
7. Purchase intent

The AI response must also include grounded evidence, objections and one driver
for every score. Invalid or unsupported output is rejected. When enabled,
deterministic fallback produces an explicitly labeled information-completeness
assessment instead of pretending a model response succeeded.

### Durable jobs and retries

Simulation runs persist `queued`, `evaluating`, `report_ready`,
`report_ready_partial` or `failed` stages and expose expected, queued, running,
processed, completed and failed counts. Persona outputs are saved independently.
Completed AI outputs are not rerun when another perspective is retried.

The worker uses PostgreSQL row locks, leases and heartbeats. Unknown in-flight
provider calls after interruption are marked `interrupted` for explicit retry,
preventing accidental duplicate billing. Request UUIDs make creation and bulk
retry operations idempotent.

### Reports and comparison

Reports contain immutable inputs, completed and failed reactions,
recommendations, grouped objections, revised-caption annotations, scoring/model/
prompt versions, fallback indicators and usage metadata.

Dedicated report APIs support seller-owned history, snapshot search, status/mode/
date filters, pagination, detail, deletion and comparison of two fully completed
reports with different persona counts. Comparison calculates overall and all
seven dimension averages while excluding failed evaluations.

## Main routes

| Frontend route | Purpose |
| --- | --- |
| `/` | Public product landing page |
| `/login`, `/register` | Seller authentication |
| `/dashboard` | Workspace overview and saved metrics |
| `/products` | Product and image management |
| `/posts` | Promotional posts and version history |
| `/simulate` | Audience, persona selection and simulation execution |
| `/reports/[id]` | Full saved report, recommendations, retries and print/PDF |
| `/history` | In-progress and completed simulation history |
| `/compare` | Compare completed reports |
| `/settings` | Local display preferences and account overview |

Interactive backend documentation is available at `/docs` while FastAPI is
running. Important APIs include `/auth/*`, `/products`, `/posts`,
`/simulation-options`, `/persona-adaptations`, `/simulation-runs` and `/reports`.

## Local development

### Prerequisites

- Node.js 20.9 or newer
- Python 3.13 or newer
- `uv`
- PostgreSQL/Supabase connection
- Optional private Supabase Storage bucket
- Optional Tokens.bd-compatible model endpoint; deterministic fallback can run
  without a model key

### 1. Configure and migrate the backend

```powershell
cd backend
uv sync --locked
Copy-Item .env.example .env
```

Replace placeholders in `backend/.env`. Never commit `.env`, database passwords,
Supabase secret keys or model API keys.

```powershell
uv run alembic upgrade head
uv run alembic current
```

The current Phase 1 schema revision is `0011`.

### 2. Start the backend

The simplest local configuration embeds the worker:

```powershell
uv run uvicorn main:app --reload
```

API: `http://127.0.0.1:8000`
OpenAPI: `http://127.0.0.1:8000/docs`

For a separate worker process:

```powershell
# API terminal
$env:SIMULATION_WORKER_ENABLED = "false"
uv run uvicorn main:app --reload
```

```powershell
# Worker terminal
uv run python worker.py
```

### 3. Start the frontend

```powershell
cd frontend
npm ci --cache .npm-cache --no-audit --no-fund
npm run dev
```

Frontend: `http://localhost:3000`

The frontend defaults to port 8000 on the browser's current hostname. Set
`NEXT_PUBLIC_API_URL` in ignored `frontend/.env.local` when using another API
origin.

## Verification

Backend:

```powershell
cd backend
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
```

Frontend:

```powershell
cd frontend
npm test
npm run test:integration
npm run lint
npx tsc --noEmit
npm run build
```

At the current Phase 1 handoff, the automated result is 146 passing backend
tests, 37 passing frontend unit tests, one passing isolated live API integration
test, clean Ruff/ESLint/TypeScript checks and a successful production build.

## Team and Phase 1 ownership

| Member | GitHub | Phase 1 ownership and contribution |
| --- | --- | --- |
| **Sumaiya Rahman Soma** | [@srs4929](https://github.com/srs4929) | Core backend: schema conventions, authentication, seller ownership, products, product images, promotional posts, immutable post versions and migrations |
| **Chowdhury Shafahid Rahman** | [@Shafahid](https://github.com/Shafahid) | Frontend and integration: Next.js workspace, authentication flow, product/post screens, API client/state integration, simulation/report UI, history, comparison and responsive presentation |
| **H. M. Mehedi Hasan** | [@Mehedi26696](https://github.com/Mehedi26696) | AI simulation: persona catalog/adaptation, trust-signal detection, seven-dimension scoring, Tokens.bd/LiteLLM evaluator, deterministic fallback, objections, recommendations and caption revision |
| **Abu Bakar** | [@abs-Futy7](https://github.com/abs-Futy7) | Simulation and report backend: durable jobs, persisted progress, 5/10/20/30 validation, bounded worker orchestration, retries, interruption recovery, usage safeguards, immutable report APIs, search/filter, comparison, integration tests and operational documentation |

GitHub contributor activity is also available on the
[repository contributors page](https://github.com/Shafahid/CSE-4113-Buyora/graphs/contributors).

## Future work

1. **Realistic and diverse buyer personas**
   Make AI buyer personas more realistic, diverse and dynamic across age groups,
   shopping behavior, budgets and customer preferences. Expand the built-in
   catalog and improve contextual persona generation without stereotyping.

2. **Advanced analytics and reporting**
   Add deeper buyer-behavior analysis, audience segmentation, trust analysis,
   purchase-intention insights and richer longitudinal comparison reports.

3. **Product image analysis**
   Use AI to evaluate product-image quality, visual attractiveness, product
   presentation and promotional effectiveness.

4. **Competitor and market analysis**
   Analyze similar-product pricing, promotional strategies and market trends to
   provide better evidence-backed recommendations to sellers.

5. **Multi-platform content optimization**
   Generate and evaluate platform-specific promotional captions and
   recommendations for Facebook, Instagram, TikTok and WhatsApp.

6. **Cloud deployment and DevOps**
   Add Docker, GitHub Actions CI/CD, automated deployment, monitoring, backups
   and scalable cloud hosting so Buyora becomes publicly accessible and reliable.

Additional production work includes profile editing, password recovery,
accessibility testing, deployed cookie/CORS validation, database backup drills,
cost monitoring and security hardening.

## Documentation

- [Product requirements](docs/PRODUCT_REQUIREMENTS_DOCUMENT.md)
- [Phase 1 member tasks](docs/Buyora_Phase_1_Member_Tasks.md)
- [Backend setup and APIs](backend/README.md)
- [Frontend setup and integration](frontend/README.md)
- [AI implementation and scoring rubric](backend/docs/ai-simulation.md)
- [Simulation jobs, reports and recovery](backend/docs/simulation-reports.md)
