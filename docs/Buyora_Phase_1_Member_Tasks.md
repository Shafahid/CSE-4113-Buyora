# Buyora — Phase 1 Development Plan

> **Internet Programming Lab · Four-member team · Updated scope: 30 buyer personas**  
> **Purpose:** Assign implementation tasks, identify code owners, and organize Phase 1 pull requests for the Buyora AI buyer-reaction simulator.

---

## Team & Ownership

| Member | Role | Primary responsibility | Phase 1 effort |
|:--|:--|:--|--:|
| **1. Shoma** | Core Backend Developer | Database, authentication, product and post APIs | **25 points** |
| **2. Shafayet** | Frontend & Integration Developer | Next.js UI, API integration, user workflows | **25 points** |
| **3. Mehdi** | AI Simulation Developer | Persona generation, AI evaluation, scoring and recommendations | **25 points** |
| **4. Abu Bakar** | Simulation & Report Backend Developer | Simulation jobs, worker orchestration, retries and reports | **25 points** |
| | | **Total** | **100 points** |

> **Workload note:** These are relative planning points for *new Phase 1 work*, not verified hours or total historical contribution. Every owner also tests and documents their own features.

## Updated Phase 1 Scope — Personas & AI

The original PRD introduced **10 baseline personas** and the frontend demo currently supports **2–8 selected personas**. The team has now **expanded the proposed implementation** to **30 curated templates** and configurable evaluation sizes. These are new development decisions, **not functionality already implemented**.

| Simulation mode | Persona evaluations | Purpose |
|:--|--:|:--|
| **Quick** | **5** | Fast feedback on key objections |
| **Standard (default)** | **10** | Balanced analysis |
| **Deep** | **20** | Broader coverage of buyer concerns |
| **Extended** | **30** | All curated perspectives; enable after latency/cost testing |

**Implementation agreements**

- [ ] Keep **30 predefined persona templates**, retaining the original 10 as part of the library.
- [ ] Allow **5 / 10 / 20 / 30** persona selections via modes; custom selection within the supported maximum may be added if all layers agree.
- [ ] Adapt persona descriptions to the **product, post, audience and platform**, and support AI-generated variants with a diversity/duplicate check.
- [ ] Evaluate **only selected personas** against the **same immutable input snapshot**.
- [ ] Use the team's **Tokens.bd API access through the backend only**. Keep provider base URL, model and API key configurable; never send secrets to the browser or Git.
- [ ] Add concurrency limits, retry/backoff, token-usage tracking, spend safeguards and deterministic fallback. More personas mean more work, not necessarily better analysis.
- [ ] Preserve the frontend's **seven persona score dimensions** (Interest, Relevance, Value, Price fit, Trust, Clarity, Purchase intent). Report-level virality or boost-readiness scores need their own documented definitions.
- [ ] Label all reactions and viewer-network visualizations as **fictional AI simulations**, not real customer behavior or reliable sales forecasts.

### Curated 30-Persona Library

| Category | Personas |
|:--|:--|
| **Price & Value** | Budget-Conscious Student · Bargain Hunter · Premium Buyer · Price Comparator · Value-for-Money Buyer |
| **Trust & Security** | COD-First Buyer · Scam-Aware Skeptic · Review-Dependent Buyer · Authenticity Checker · Return-Policy-Conscious Buyer |
| **Shopping Behavior** | Impulse Buyer · Casual Scroller · Repeat Buyer · First-Time Buyer · Research-Heavy Buyer |
| **Convenience** | Busy Professional · Urgent Buyer · Gift Buyer · Delivery-Sensitive Buyer · Easy-Ordering Buyer |
| **Product & Lifestyle** | Trend Follower · Quality-Focused Buyer · Practical Buyer · Feature-Oriented Buyer · Durability-Focused Buyer |
| **Social Commerce** | Facebook Live Viewer · Social-Proof Buyer · Inbox-First Buyer · Video-Demo Buyer · Comment-Section Reader |

---

## Member 1 — Shoma: Core Backend Developer

**Code ownership:** SQLAlchemy models, Alembic migrations, authentication, products and posts.  
**Total assigned effort:** **25 points**.

### M1 · Database Schema & Contracts — 7 points

**PRs:** `#00–01` · **Start first**

- [ ] Draft the shared **API contract, data model and AI output contract** with review by all four members.
- [ ] Create `User`, `Session`, `Product`, `Post` and `PostVersion` SQLAlchemy models.
- [ ] Define user ownership, relationships, foreign keys, indexes and constraints.
- [ ] Generate and review Alembic migrations for core business tables.
- [ ] Test schema upgrades and basic model relationships.
- [ ] Publish model conventions for Abu Bakar's simulation/report tables, including **configurable persona counts** and snapshot ownership.

### M2 · Authentication & Ownership — 7 points

- [ ] Create registration, login, logout and current-user endpoints.
- [ ] Hash passwords securely; never store plaintext credentials.
- [ ] Implement server-managed sessions and authentication dependencies.
- [ ] Configure credentialed CORS and appropriate cookie/CSRF protections.
- [ ] Reject protected requests without valid authentication.
- [ ] Verify users cannot access other users' products or posts.
- [ ] Add authentication and authorization tests.

### M3 · Product Management APIs — 4 points

- [ ] Implement product create, list, detail, update and delete operations.
- [ ] Implement duplicate, archive and restore operations.
- [ ] Validate product name, price, descriptions and other required fields.
- [ ] Enforce ownership and preserve historical report snapshots when products change.
- [ ] Test CRUD operations, invalid inputs and cross-user requests.

### M4 · Promotional Post APIs — 4 points

- [ ] Implement post create, list, detail, update and delete operations.
- [ ] Associate each post with an authorized product.
- [ ] Preserve previous caption bodies as versions when captions change.
- [ ] Validate headline, caption, CTA and platform fields.
- [ ] Prevent editing or accessing posts owned by another user.
- [ ] Add post-version and product-deletion behavior tests.

### M5 · Backend Integration Review — 3 points

- [ ] Review Abu Bakar's migrations for compatibility with core tables.
- [ ] Test authentication and ownership on integrated simulation/report endpoints.
- [ ] Resolve backend contract inconsistencies with Shafayet and Mehdi.
- [ ] Confirm pytest, Ruff and relevant migration tests pass.

**Deliverable:** Secure, tested APIs and database models for products, posts, users and their ownership.

---

## Member 2 — Shafayet: Frontend & Integration Developer

**Code ownership:** Next.js screens, typed API integration and end-to-end UI workflows.  
**Total assigned effort:** **25 points**.

> **Preserve the existing frontend.** Replace its demo-only persistence with real server-backed actions; do not rebuild working screens unnecessarily.

### S1 · Typed API Client & Authentication — 6 points

- [ ] Create a centralized typed API client for backend requests.
- [ ] Define request/response TypeScript types from the agreed OpenAPI contract.
- [ ] Support session cookies, credentialed requests and common errors.
- [ ] Connect registration, login, logout and current-user screens.
- [ ] Protect workspace routes and implement session-loading states.
- [ ] Create mock API responses so UI development starts before all backend endpoints are ready.

### S2 · Product & Post Integration — 6 points

- [ ] Replace demo product reads/writes with real product endpoints.
- [ ] Connect product create, edit, duplicate, archive, restore and delete actions.
- [ ] Connect promotional post forms and caption version history.
- [ ] Synchronize products/posts after successful mutations.
- [ ] Handle server validation errors, loading states and network failures.
- [ ] Keep the public sample/demo mode separate from real user data.

### S3 · Simulation Wizard Integration — 7 points

- [ ] Connect **30 persona templates**, dynamic persona-generation APIs and editable persona selection.
- [ ] Add **Quick (5), Standard (10), Deep (20), Extended (30)** simulation modes; make Standard the default.
- [ ] Remove the demo's **2–8 persona limit** and enforce the agreed selection rules and server validation messages.
- [ ] Submit product, post, audience and selected personas; save the returned job ID.
- [ ] Poll the backend for **actual** job status and progress instead of relying on timer-only progress.
- [ ] Display completed, failed and partially completed evaluations correctly.
- [ ] Connect retry actions, redirect to the finished report and preserve the draft after recoverable failures.

### S4 · Reports, History & UI Testing — 6 points

- [ ] Fetch report data from the API instead of browser `localStorage`.
- [ ] Connect report tabs, dashboard summaries and history.
- [ ] Compare two completed reports using real API data.
- [ ] Retain the existing local **fictional 60-viewer spread graph** using server persona reactions; clearly distinguish graph viewers from evaluated personas.
- [ ] Implement consistent loading, empty, expired-session and error states, including long-running Extended simulations.
- [ ] Add tests for login, product-to-report workflow, simulation modes and failure recovery.

**Deliverable:** A fully integrated frontend that runs 5-, 10-, 20- or 30-persona workflows without relying on demonstration data as the authoritative source.

---

## Member 3 — Mehdi: AI Simulation Developer

**Code ownership:** Persona generation, trust-signal detection, deterministic scoring, AI evaluation, recommendations and fallback.  
**Total assigned effort:** **25 points**.

> **Parallel development:** Mehdi can begin after the AI output contract is agreed, using fixed fixtures without waiting for the product APIs or background worker.

### A1 · Buyer Persona Engine — 5 points

- [ ] Expand the **original 10 baseline personas** to a curated **30-persona library** across six shopping-behavior categories.
- [ ] Implement persona generation/adaptation from product, post, audience and platform inputs.
- [ ] Support English and Bangla persona descriptions and reactions (and test Banglish inputs).
- [ ] Allow editing/customization without losing required persona fields.
- [ ] Validate unique persona IDs, prevent near-duplicate perspectives and support **5/10/20/30** selections.
- [ ] Add deterministic tests for template coverage, diversity and stable results using fixed inputs.

### A2 · Trust & Scoring Engine — 7 points

- [ ] Detect price clarity, delivery, return policy, product details and other trust signals.
- [ ] Define the **seven persona-level score dimensions** and versioned scoring rules.
- [ ] Calculate scores consistently within **0–100**.
- [ ] Create sentiment classification and explainable score drivers.
- [ ] Define report-level scores separately, only where supported by a documented rubric.
- [ ] Version the scoring methodology and test edge cases for **5, 10, 20 and 30 personas**.
- [ ] Exclude failed persona evaluations from completed-score averages.

### A3 · AI Buyer-Reaction Evaluator — 8 points

- [ ] Create a replaceable AI provider adapter, with **Tokens.bd** connection values supplied from backend environment settings.
- [ ] Build buyer-specific prompts using the **same immutable product/post snapshot** for each persona.
- [ ] Generate structured comments, reasons, objections, positives and questions.
- [ ] Validate all AI responses against the shared reaction schema; reject or safely recover from malformed output.
- [ ] Support English/Bangla responses and local social-commerce concerns without stereotyping groups.
- [ ] Handle provider failures, request timeouts and throttling; expose errors in a form the job worker can process.
- [ ] Return model/prompt version and token-usage metadata for persistence and monitoring.
- [ ] Write mocked provider tests so automated checks do not use paid API calls.

### A4 · Fallback & Recommendations — 5 points

- [ ] Implement deterministic evaluation for unavailable or failing AI services.
- [ ] Extract recurring objections, redundant concerns and missing information across larger persona sets.
- [ ] Generate prioritized, evidence-backed recommendations.
- [ ] Generate revised captions without inventing discounts, stock claims, warranties or delivery promises.
- [ ] Test AI/fallback consistency, factual grounding, language quality and duplicate detection.

**Deliverable:** A backend-only, testable AI service that produces diverse structured reactions for up to 30 selected personas, including a meaningful fallback path.

---

## Member 4 — Abu Bakar: Simulation & Report Backend Developer

**Code ownership:** Job lifecycle, worker orchestration, concurrency, retries and stored reports.  
**Total assigned effort:** **25 points**.

> This work forms the foundation for Abu Bakar's **Phase 2 DevOps/CI/CD** responsibilities.

### B1 · Simulation Data Models & Job APIs — 7 points

- [ ] Create `SimulationJob`, `JobPersona`, `Report` and `Reaction` persistence models.
- [ ] Create reviewed Alembic migrations **after Shoma's core schema** is merged.
- [ ] Implement request validation and job creation for **5/10/20/30 selected personas**.
- [ ] Expose actual status, progress counters and job-stage metadata (including expected persona count).
- [ ] Add persona template/generation endpoints that call **Mehdi's** service.
- [ ] Apply authentication and seller ownership to all job endpoints.
- [ ] Add tests for invalid requests, selection limits and job-state transitions.

### B2 · Processing Worker & Retry Engine — 8 points

- [ ] Create a separate background worker that processes durable simulation jobs.
- [ ] Invoke **Mehdi's** evaluator for each selected persona, with bounded concurrency rather than 30 unlimited simultaneous calls.
- [ ] Track pending, running, complete and failed evaluations and report *real* progress.
- [ ] Persist successful persona results independently so partial failures do not discard them.
- [ ] Retry failed personas without rerunning completed ones; apply bounded retry/backoff for provider rate limits and transient errors.
- [ ] Support worker interruption recovery and idempotent job creation.
- [ ] Record per-job token usage, provider latency, fallback usage and cost/spending-limit signals where available.
- [ ] Test worker failures, AI timeouts and **5/10/20/30-persona** workloads.

### B3 · Report Persistence & Retrieval — 7 points

- [ ] Preserve immutable original product, post, audience and persona snapshots.
- [ ] Store reactions, recommendations, report metadata, scoring/model/prompt versions and fallback indicators.
- [ ] Implement report detail, list, delete, search/filter and history APIs.
- [ ] Support comparison of two fully completed reports, including runs with different persona counts.
- [ ] Return data compatible with the agreed frontend adapter and existing seven-score conventions.
- [ ] Prevent users from retrieving or deleting other sellers' reports.
- [ ] Test report integrity after the original product or post changes.

### B4 · Integration & API Verification — 3 points

- [ ] Test the complete simulation-to-report backend lifecycle for every simulation mode.
- [ ] Verify retry behavior, partial results and accessibility of reports after worker restart.
- [ ] Document local worker setup, provider configuration requirements and failure recovery **without publishing secrets**.
- [ ] Check OpenAPI responses, ownership, tests and relevant migrations.

**Deliverable:** Persistent, observable simulation jobs and reports for up to 30 evaluated personas, with bounded concurrency and per-persona recovery.

---

## Recommended Pull Request Order

> **Branch pushes can occur in parallel; merge only after the listed dependencies are available.** PR numbers below are planning identifiers rather than guaranteed GitHub numbers.

| Order | Owner | PR / branch | Depends on |
|:--|:--|:--|:--|
| 00 | **Shoma + team review** | `docs/phase1-contract` | Existing `main` |
| 01 | **Shoma** | `feat/core-schema` | 00 |
| 02 | **Mehdi** | `feat/persona-engine-30` | 00 |
| 03 | **Shafayet** | `feat/api-client` | 00 |
| 04 | **Mehdi** | `feat/trust-scoring` | 02 |
| 05 | **Shoma** | `feat/auth-api` | 01 |
| 06 | **Shoma** | `feat/product-api` | 05 |
| 07 | **Abu Bakar** | `feat/simulation-jobs` | 01, 05 |
| 08 | **Shoma** | `feat/post-api` | 06 |
| 09 | **Mehdi** | `feat/tokensbd-ai-evaluator` | 04 |
| 10 | **Shafayet** | `feat/auth-product-post-ui` | 03, 05, 06, 08 |
| 11 | **Mehdi** | `feat/ai-fallback-recommendations` | 09 |
| 12 | **Abu Bakar** | `feat/simulation-worker-30` | 07, 08, 09, 11 |
| 13 | **Abu Bakar** | `feat/report-services` | 12 |
| 14 | **Shafayet** | `feat/persona-modes-simulation-ui` | 10, 12 |
| 15 | **Abu Bakar** | `test/simulation-integration` | 13 |
| 16 | **Shafayet** | `feat/report-history-ui` | 13, 14 |
| 17 | **Shoma** | `test/backend-security` | 13, 15 |

### Merge rules

- [ ] Create a feature branch from the latest `main` for each PR.
- [ ] Open one reviewable PR per feature, with associated tests and documentation.
- [ ] Ask **Shoma** to review cross-module database models and migrations.
- [ ] Ask **Mehdi** to review all changes to AI reaction/scoring schemas.
- [ ] Ask **Abu Bakar** to review job-status and report API changes.
- [ ] Ask **Shafayet** to review frontend contract and user-workflow changes.
- [ ] Never commit Tokens.bd keys, `.env` files, or production database credentials.
- [ ] Merge only when applicable lint, unit tests, builds and migration checks pass.

---

## Phase 1 Definition of Done

- [ ] A seller can register, log in, create a product and create a promotional post.
- [ ] User-owned data is persisted in PostgreSQL and isolated from other users.
- [ ] The interface offers **Quick (5), Standard (10), Deep (20) and Extended (30)** persona modes.
- [ ] The backend exposes **30 curated persona templates** and supports relevant AI customization.
- [ ] Simulation jobs use **real worker progress**, bounded concurrency and independent retries.
- [ ] AI reactions include seven scores, reasons, comments and concerns, with fallback on provider failure.
- [ ] Recommendations and revised captions do not invent commercial facts.
- [ ] Reports store immutable input snapshots and can be reopened after refresh.
- [ ] Reports/history/compare pages display server-backed results; the spread graph remains explicitly simulated.
- [ ] Every member has reviewed, tested pull requests demonstrating their individual contribution.

**Phase 2 (later):** Production Dockerization, GitHub Actions CI/CD, automated staging/production deployment, monitoring, backups, and broader security/accessibility/performance work. **Abu Bakar leads DevOps**, with all members responsible for tests and deployability of their own modules.
