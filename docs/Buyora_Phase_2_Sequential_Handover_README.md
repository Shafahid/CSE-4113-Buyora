# Buyora — Phase 2 Final Development README

> **Development strategy:** One member finishes an owned stage, tests it, merges it, and hands it over to the next member.  
> **Order:** **Shoma → Mehdi → Abu Bakar → Shafayet → Final release verification**  
> **Team:** 4 members · **Planned Phase 2 effort:** 100 points (25 per member)  
> **Status:** Proposed execution plan, based on the team's reported Phase 1 completion and the six approved future-work features.

---

## 1. Objective and final features

Buyora is a pre-publish buyer-reaction simulator for Bangladeshi social-commerce sellers. Phase 1 established the core product/post, persona simulation, job/report, and frontend flows **according to the team's progress report**. Phase 2 should add meaningful seller-facing capabilities without rebuilding those modules.

### Six approved Phase 2 features

1. **Realistic & diverse buyer personas** — More context-aware and differentiated buyer behavior; improved Bangla/Banglish/English reactions.
2. **Advanced analytics & reporting** — Audience segments, trust/purchase-intent breakdowns, objection patterns, report comparisons, and PDF export.
3. **Product image analysis** — AI-assisted feedback on clarity, composition, legibility, presentation, and consistency with seller-supplied descriptions.
4. **Competitor & market analysis** — Source-grounded price, offer, and promotional comparisons based on seller-provided or lawfully available competitor evidence.
5. **Multi-platform content optimization** — Recommendations and content variants for Facebook, Instagram, TikTok, and WhatsApp.
6. **Cloud deployment & DevOps** — Docker, GitHub Actions CI/CD, staging, monitoring, backups, and a verified final release.

**Out of scope:** Automatic publishing/boosting, guaranteed sales or virality prediction, unsupported competitor price claims, and claims of product authenticity based only on images.

### Carry over from Phase 1

- **Frontend:** Next.js + React + TypeScript. Preserve working product, post, simulation, graph, history, and report screens.
- **Backend:** FastAPI + SQLAlchemy + Alembic + Supabase PostgreSQL.
- **AI:** Tokens.bd integration, 30 baseline buyer personas, and simulation modes: **Quick (5), Standard (10), Deep (20), Extended (30)**.
- **Execution:** Server-side simulation jobs, partial failures, retries, and immutable historical reports.

> **Verification note:** The original uploaded frontend/backend READMEs describe the earlier demo/backend foundation. The team says Phase 1 is now finished, but this file is not an independent code audit. Run the Phase 1 smoke test before beginning Stage 0.

---

## 2. One-way handover workflow

```text
BEFORE DEVELOPMENT
All 4: One contract-review meeting and Phase 1 smoke test
                    │
                    ▼
STAGE 1 — SHOMA
Database extensions + feature APIs + authentication/permissions
                    │
       Tested API + schema + fixtures + OpenAPI
                    ▼
STAGE 2 — MEHDI
Persona improvements + image AI + market insights + platform AI
                    │
       Tested AI service + structured outputs + sample results
                    ▼
STAGE 3 — ABU BAKAR
Analytics + PDF reports + Docker + CI/CD + staging
                    │
       Tested reporting API + downloadable PDF + staging URL
                    ▼
STAGE 4 — SHAFAYET
Image/market/analytics/platform UI + full frontend integration
                    │
       Tested, polished application + end-to-end tests
                    ▼
FINAL GATE
Automated pipeline + whole-team smoke test + release approval
```

**Yes, Shafayet can do the final feature integration.** He does **not** have to build the new screens first. The exception is that **all four members must review the contracts before Stage 1**—otherwise Shoma may choose schemas that the later AI/report/UI features cannot use.

**Minimizing rework ≠ guaranteeing zero changes.** A handover is accepted only when its tests and sample responses pass. Subsequent changes should be limited to small bug-fix PRs or explicitly approved contract changes.

### What gets frozen at Stage 0 (all four, one meeting)

- [ ] Agree on the six features, page flows, and **which items are optional** during simulation.
- [ ] Freeze JSON request/response formats, error format, status values, stable IDs, and ownership rules.
- [ ] Freeze the seven existing persona score dimensions and define *new* analytics separately.
- [ ] Confirm 30 curated persona templates and 5/10/20/30 simulation modes remain unchanged.
- [ ] Choose common schemas for `ImageInsight`, `CompetitorEvidence`, `MarketComparison`, `PlatformVariant`, and `AdvancedReport`.
- [ ] Choose how AI tasks are invoked: **FastAPI route → existing simulation/service layer → Mehdi's provider-independent functions**.
- [ ] Decide where image files go (authenticated object storage), and how competitor data sources and dates are recorded.
- [ ] Define where optional results live in immutable report snapshots and how old reports remain readable.
- [ ] Shafayet signs off on UI-required data; Mehdi on AI input/output; Abu Bakar on reporting/job fields; Shoma on DB/API conventions.

**Stage 0 deliverables:** `docs/phase2/API_CONTRACT.md`, `DATA_MODEL.md`, `AI_OUTPUTS.md`, `HANDOVER_CHECKLIST.md`, and committed JSON fixtures. Shoma owns the documentation PR, but **everyone reviews it before merge**.

---

## 3. Work ownership — balanced at 25 points each

| Order | Member | Responsibility | Effort | Handover recipient |
|:--:|:--|:--|--:|:--|
| **1** | **Shoma** | Stable backend: database, image/competitor/platform APIs, security | **25** | Mehdi |
| **2** | **Mehdi** | All AI features: dynamic personas, vision, grounded market insights, platform content | **25** | Abu Bakar |
| **3** | **Abu Bakar** | Analytics/PDF services, Docker, CI/CD, staging, monitoring | **25** | Shafayet |
| **4** | **Shafayet** | All final frontend screens, integrations, accessibility, browser/E2E QA | **25** | Final release |
| | **Total** | | **100** | |

Points are **planning estimates**, not a measure of hours or actual completed work. Each owner's implementation includes their own tests and documentation.

---

# 4. STAGE 1 — Shoma: Finish backend APIs, schema & security


**Implementation update (2026-11-28):** Stage 1 technical work is verified: 260 backend tests passed, including isolated PostgreSQL checks; lint, formatting and frontend type checking passed. Team contract approval, PR merge and Mehdi acceptance remain pending. See the [Stage 1 handover package](phase2/handoffs/01-shoma-to-mehdi.md).

**Start:** After the contract PR is approved.  
**Rule:** Do not wait for Mehdi to implement AI. Create stable service interfaces and use mocks in backend tests.  
**Primary ownership:** `backend/app/models/`, `backend/app/api/routes/`, schema and migration files, security/dependencies.

### SH1. Contracts & version-safe database extensions — **5 points**

- [ ] Lead Stage 0 contract meeting; record decisions and data examples.
- [x] Create SQLAlchemy models for image metadata, competitor evidence, source/date fields, saved platform variants, and **optional** analysis attachments.
- [x] Define foreign keys, indexes, ownership checks, unique constraints, timestamps, and schema versions.
- [x] Preserve Phase 1 product/post/report data; make migrations **backwards compatible**.
- [x] Review Alembic upgrade and downgrade behavior against PostgreSQL in a test/staging DB.
- [x] Provide representative JSON responses for every new API.

### SH2. Product images + competitor evidence APIs — **8 points**

- [x] Implement authenticated image upload, replace, list, and delete operations.
- [x] Validate file type, size, user ownership, and object-storage access; never expose storage keys.
- [x] Return secure image references for AI analysis without exposing private seller content publicly.
- [x] Add competitor records: name/category, current observed price, offer, platform, source, observation date, and optional seller notes.
- [x] Support manually entered competitor evidence first; any external ingestion must be lawful, source-grounded, and explicitly optional.
- [x] Implement list/search/filter/delete and ownership validation on competitor entries.
- [x] Add validation and cross-user access tests.

### SH3. Platform variants & AI integration endpoints — **6 points**

- [x] Define and implement versioned content-variant storage for Facebook, Instagram, TikTok, and WhatsApp.
- [x] Preserve original promotional posts and immutable historical report inputs.
- [x] Provide request/response endpoints to submit/retrieve image analysis, market comparisons, and platform content suggestions.
- [x] Define provider-neutral *service interfaces* that Mehdi will implement in Stage 2.
- [x] For Stage 1 tests, return explicit **mock/example data** through test doubles only—do not label placeholder output as live AI results.
- [x] Add status/error responses for unavailable image, missing market evidence, timeouts, and unsupported inputs.

### SH4. API quality, security & final handover — **6 points**

- [x] Enforce authentication, record-level authorization, input validation, and safe uploaded-file handling.
- [x] Add rate limiting and AI request/cost limits at expensive API entry points.
- [x] Check query/index performance, pagination, appropriate session lifecycles and CORS configuration.
- [x] Run backend pytest, Ruff, PostgreSQL migration tests, and API contract tests.
- [x] Generate/update OpenAPI docs; provide example `curl`/HTTP requests, required env-variable names (not values), and a migration checklist.
- [x] Demonstrate old Phase 1 APIs still work with the new migration.

**Stage 1 handover package → Mehdi**

- [ ] All Shoma PRs merged into `main`.
- [x] A reproducible database migration and populated test fixtures.
- [x] Working authentication/image/competitor/platform endpoints in the API docs.
- [ ] Frozen AI callable interfaces with documented Pydantic schemas and sample payloads.
- [ ] Passing security/API/migration tests and no secrets committed.

**Handover acceptance:** Mehdi can call the new service interfaces with sample inputs without changing database tables or endpoint names.

---

# 5. STAGE 2 — Mehdi: Finish all AI intelligence features

**Start:** Only after accepting Shoma's backend handover.  
**Rule:** Implement within the approved interfaces; avoid editing Shoma's database models/routes except for documented integration hooks agreed in Stage 0.  
**Primary ownership:** `backend/app/services/ai/`, prompts, provider adapters, AI test fixtures.

### MH1. Realistic & diverse personas — **7 points**

- [ ] Retain the 30 baseline buyer personas and all four 5/10/20/30 modes.
- [ ] Personalize personas using product category, buying priorities, budget sensitivity, shopping habits and platform context.
- [ ] Detect/remove duplicate personas and repeated reaction language without erasing useful viewpoints.
- [ ] Improve Bangla/Banglish/English naturalness and local commerce objections.
- [ ] Keep the existing seven scores and stable scoring rules; explain simulated conclusions.
- [ ] Avoid unsupported demographic stereotypes or claims about actual shoppers.
- [ ] Test persona diversity, output validity, latency, and token usage per mode.

### MH2. AI product image analysis — **7 points**

- [ ] Integrate a **verified vision-capable** Tokens.bd model/provider if available; support a graceful unsupported/unavailable result otherwise.
- [ ] Analyze observable image characteristics: clarity, framing, background distraction, text readability and product-description consistency.
- [ ] Return severity, observation/evidence, and actionable presentation suggestions in the frozen JSON schema.
- [ ] Work with Shoma's authorized image reference; never put API keys in the frontend.
- [ ] Handle poor-quality, unrelated, missing, or large images robustly.
- [ ] Avoid asserting product authenticity, actual quality, or predicted conversion rates from images alone.
- [ ] Write mocked tests covering malformed model responses and failure cases.

### MH3. Evidence-grounded competitor & market insights — **6 points**

- [ ] Read Shoma's competitor evidence records and preserve their source/date metadata.
- [ ] Compare only genuinely comparable prices/units/offer terms.
- [ ] Explain price positioning, offer differences, opportunities and limitations without inventing market facts.
- [ ] Clearly separate seller-supplied data, source observations and AI interpretation.
- [ ] Provide `insufficient_data` results if competitors/sources are missing or stale.
- [ ] Test mismatched products, unsupported claims, stale records, and multi-currency inputs if supported.

### MH4. Platform-aware content optimization & AI handover — **5 points**

- [ ] Implement distinct content suggestions for Facebook, Instagram, TikTok and WhatsApp.
- [ ] Improve hooks, CTA style, clarity, length and local language without inventing policies, reviews, discounts or urgency.
- [ ] Integrate AI features into Shoma's frozen service interfaces.
- [ ] Include deterministic fallback/error behavior where meaningful; preserve core simulation if optional features fail.
- [ ] Run a regression suite for response schemas, grounded claims, provider failure, prompt versions and token budgets.

**Stage 2 handover package → Abu Bakar**

- [ ] All Mehdi PRs merged into `main`.
- [ ] AI endpoints return validated real or explicitly labeled fallback results.
- [ ] Sample JSON outputs for persona, image, competitor and platform recommendations are committed (no personal data/API keys).
- [ ] Model/prompt version fields, sources, latency/token counts, and failure flags are documented.
- [ ] Tests pass with mocked Tokens.bd calls and the 5/10/20/30 simulation modes still work.

**Handover acceptance:** Abu Bakar can generate stable analytics and PDFs from stored AI outputs without redesigning the AI schema.

---

# 6. STAGE 3 — Abu Bakar: Reporting, PDF, DevOps & staging

**Start:** Only after accepting Mehdi's AI handover.  
**Rule:** Use stable backend/AI schemas, and test reporting APIs using fixtures without requiring the final Phase 2 UI.  
**Primary ownership:** analytics/reporting service layer, PDF generator, Docker files, GitHub Actions, staging, operational documentation.

### AB1. Advanced analytics and comparative reporting — **8 points**

- [ ] Calculate per-persona score distributions and category/behavior groupings.
- [ ] Analyze trust, purchase intention, common objections and recurring information gaps.
- [ ] Compare two completed reports with explicit score definitions, scoring versions and different persona counts.
- [ ] Persist optional image and competitor findings in immutable report snapshots with sources and analysis dates.
- [ ] Label simulation values as **AI-simulated**, not actual customer statistics.
- [ ] Add authenticated, paginated report/analytics APIs with secure user ownership.
- [ ] Implement deterministic aggregation unit tests and partial/failed persona scenarios.
- [ ] Provide documented JSON examples for Shafayet's final UI.

### AB2. Downloadable PDF reports — **5 points**

- [ ] Generate PDF with product/post summary, persona scores, objections, trust and purchase-intent insights, and recommendations.
- [ ] Include image analysis and competitor comparisons **only when available**, including data provenance.
- [ ] Include methodology/model versions, dates, simulation disclaimers, and readable Bangla text when supported.
- [ ] Implement authenticated download endpoint with reliable filenames and error handling.
- [ ] Test long captions, missing optional findings, cross-user access, and PDF rendering.

### AB3. Docker, CI/CD, staging deployment — **7 points**

- [ ] Containerize Next.js frontend, FastAPI backend, and separate simulation worker.
- [ ] Provide a local Compose setup and documented environment-variable names.
- [ ] Integrate the existing Supabase PostgreSQL configuration without committing credentials.
- [ ] Create GitHub Actions: frontend lint/test/build; backend Ruff/pytest; migration/integration checks on disposable PostgreSQL.
- [ ] Use mocked AI calls in routine CI rather than consuming paid Tokens.bd tokens.
- [ ] Build versioned images, deploy to staging after `main` merges, and require approval for production releases.
- [ ] Verify existing Phase 1 frontend and all new APIs are accessible from staging.

### AB4. Monitoring, reliability & handover — **5 points**

- [ ] Add health checks, structured application logs, worker failure/queue visibility, and AI cost/latency counters.
- [ ] Monitor image-analysis failures, stale competitor data warnings and PDF-export errors.
- [ ] Establish secrets management, backup/restore verification, migration safety and rollback guidance.
- [ ] Test a staged failed AI call, a worker retry, and a complete report export.
- [ ] Deliver a stable staging URL, OpenAPI docs, report fixtures and a UI integration checklist to Shafayet.

**Stage 3 handover package → Shafayet**

- [ ] All Abu Bakar PRs merged into `main` and automated tests green.
- [ ] Advanced analytics and PDF endpoints tested with real database fixtures.
- [ ] Staging API URL, auth method, documented CORS and test accounts/fixtures available securely.
- [ ] OpenAPI schema and sample success/error responses for every screen.
- [ ] CI/CD, Docker and recovery documentation working against the **current** frontend.

**Handover acceptance:** Shafayet can implement the complete final frontend against an existing staging API without asking the other three members to invent or rename endpoints.

**Important:** This is a **staging-ready** DevOps handover, not the final production deployment. The final frontend merges in Stage 4 and is released through this same pipeline.

---

# 7. STAGE 4 — Shafayet: Complete frontend features and final integration

**Start:** After Abu Bakar's staging and reporting handover.  
**Rule:** Reuse the Phase 1 Next.js components and integrate the already-finished APIs; avoid redesigning the backend.  
**Primary ownership:** `frontend/src/components/`, UI routes, typed API adapters, responsive layout, browser/E2E tests.

### SF1. Image analysis frontend — **6 points**

- [ ] Add image upload, preview, replace and remove to the existing product workflow.
- [ ] Trigger image analysis from the approved API and show actual status/loading/failures.
- [ ] Display clarity, framing, presentation, consistency and improvement suggestions.
- [ ] Distinguish observed image findings from model interpretation.
- [ ] Support no-image and unsupported-analysis states gracefully.
- [ ] Test authenticated upload, retry, mobile view and keyboard access.

### SF2. Competitor and multi-platform screens — **6 points**

- [ ] Add competitor entry forms and market comparison cards/tables with source/date labels.
- [ ] Show price/offer comparisons separately from AI explanations.
- [ ] Handle missing/stale/uncomparable competitor records without misleading charts.
- [ ] Add Facebook/Instagram/TikTok/WhatsApp selection and platform-specific suggestions.
- [ ] Let sellers preview, copy, edit and save content variants without overwriting original posts.
- [ ] Test each platform and its save/reload behavior.

### SF3. Advanced analytics, reports and export UI — **8 points**

- [ ] Build score distribution charts, segmented persona analysis, trust and purchase-intent breakdowns.
- [ ] Show recurring objections, missing information, evidence-backed advice and report-to-report comparisons.
- [ ] Connect API-backed image insights, market comparisons and platform content sections to reports.
- [ ] Display clear simulation disclaimers and source/method/version information.
- [ ] Add authenticated PDF export/download and errors/empty states.
- [ ] Keep the existing fictional spread graph clearly labeled and provide accessible tabular alternatives.
- [ ] Verify score behavior for 5/10/20/30 persona simulations and partial failures.
- [ ] Reuse existing report/history/dashboard components rather than rebuilding them.

### SF4. UX quality and final end-to-end tests — **5 points**

- [ ] Finish responsive/mobile layouts, accessibility, keyboard behavior and Bangla text rendering.
- [ ] Add loading/skeleton, auth-expiry, offline/network-error and retry states consistently.
- [ ] Run end-to-end tests for login → product → image → post → persona simulation → market insights → advanced report → PDF.
- [ ] Verify optional features failing does not break the core simulation or saved reports.
- [ ] Merge all final frontend PRs, confirm CI passes and demonstrate the app on staging.

**Stage 4 final handover → release gate**

- [ ] All Shafayet PRs merged into `main`.
- [ ] Working full-stack staging UI with all six features.
- [ ] Browser/E2E tests passing in the automated pipeline.
- [ ] Mobile/desktop screenshots, known limitations, and final demonstration script available.
- [ ] No breaking changes to approved APIs.

---

## 8. GitHub PR order — **strict one-way sequence**

> **Push** work to an individual branch whenever ready; **merge** in the order below. For this plan, only one owner's stage is active at a time. The contract PR is reviewed by all four, but it does not require early frontend feature coding.

| Planned PR | Owner | Suggested branch | Merge output / acceptance |
|:--:|:--|:--|:--|
| **#00** | Shoma + team review | `docs/phase2-contracts` | Frozen schemas, user flows, fixtures, endpoints |
| **#01** | Shoma | `feat/phase2-db-extensions` | Compatible DB migrations/models |
| **#02** | Shoma | `feat/images-competitor-apis` | Image and competitor evidence CRUD |
| **#03** | Shoma | `feat/platform-ai-endpoints` | Platform variants + AI service hooks |
| **#04** | Shoma | `test/backend-phase2-handover` | Auth/security/API tests + Swagger docs |
| **#05** | Mehdi | `feat/persona-diversity-v2` | Adapted 30 personas, 5/10/20/30 modes |
| **#06** | Mehdi | `feat/product-image-ai` | Structured visual findings |
| **#07** | Mehdi | `feat/market-insight-ai` | Source-grounded competitor insights |
| **#08** | Mehdi | `feat/platform-ai-and-regression` | Platform suggestions + AI regression tests |
| **#09** | Abu Bakar | `feat/advanced-analytics-api` | Advanced aggregation/comparison endpoints |
| **#10** | Abu Bakar | `feat/pdf-report-export` | Verified server-generated PDFs |
| **#11** | Abu Bakar | `devops/docker-ci-staging` | Docker + GitHub Actions + staging deployment |
| **#12** | Abu Bakar | `devops/monitoring-handover` | Monitoring, backup/recovery, integration fixtures |
| **#13** | Shafayet | `feat/image-analysis-ui` | Full image upload/insight UI |
| **#14** | Shafayet | `feat/competitor-platform-ui` | Competitor and platform screens |
| **#15** | Shafayet | `feat/advanced-analytics-ui` | Reports, charts, comparison, PDF button |
| **#16** | Shafayet | `test/final-ui-e2e` | Mobile/browser checks + final E2E |

**After PR #16:** Tag the release candidate and let the **already configured** CI/CD pipeline redeploy staging. All four members verify the same final build; production release requires explicit approval. This is a release gate, not a second development assignment for Shoma/Mehdi/Abu Bakar.

### Per-PR rules

- [ ] Pull latest `main`, create a new feature branch, and keep PR scope narrow.
- [ ] Link an issue, list affected files/APIs/migrations, and attach test evidence.
- [ ] Review shared contracts **before** merging breaking changes.
- [ ] Keep one responsible code owner per module; do not rewrite another member's work without discussion.
- [ ] Protect `main`; require at least one reviewer and passing checks.
- [ ] Never commit `.env`, Tokens.bd tokens, database passwords or private seller data.
- [ ] On a failed handover check, the current owner fixes that stage **before** it is accepted.

### Basic Git commands

```bash
git switch main
git pull --ff-only origin main
git switch -c feat/phase2-db-extensions
# edit files, run tests
git add <changed-files>
git commit -m "feat(db): extend Buyora phase 2 schema"
git push -u origin feat/phase2-db-extensions
# Open a pull request to main, obtain review, merge.
```

---

## 9. Handover files — required at the end of each stage

Every owner places a brief handover document in `docs/phase2/handoffs/`.

```text
docs/phase2/
  API_CONTRACT.md
  DATA_MODEL.md
  AI_OUTPUTS.md
  HANDOVER_CHECKLIST.md
  fixtures/
    image_insight.json
    market_comparison.json
    platform_variant.json
    advanced_report.json
  handoffs/
    01-shoma-to-mehdi.md
    02-mehdi-to-abu-bakar.md
    03-abu-bakar-to-shafayet.md
    04-shafayet-to-release.md
```

Each handover file must include:

1. **What changed:** PR links, modules owned, new features.
2. **How to run it:** local commands, environment-variable **names** and migrations.
3. **Contract:** API URLs, request/response examples, status/error formats.
4. **How to test it:** reproducible commands, sample fixtures, passing result evidence.
5. **Known limitations:** optional failures, external dependencies, remaining risks.
6. **Next owner's starting point:** exact service functions or endpoints to consume.

No stage is complete until the next owner verifies the examples and accepts the handover.

---

## 10. Release architecture

```text
Next.js frontend — Shafayet (integrated LAST)
  ├─ Product image upload & insights
  ├─ Competitor / market comparisons
  ├─ Dynamic personas & multi-platform suggestions
  └─ Advanced analytics / PDF download
                │ HTTPS + session/auth
                ▼
FastAPI routes / PostgreSQL models — Shoma (completed FIRST)
  ├─ Protected product images and evidence records
  ├─ Platform variant storage + stable AI service interfaces
  └─ Existing product, post and account APIs
                │
                ▼
AI services — Mehdi (completed SECOND)
  ├─ Adaptive 30-persona evaluations
  ├─ Optional product image analysis
  ├─ Grounded competitor comparisons
  └─ Platform-specific content suggestions
                │
                ▼
Reporting + operations — Abu Bakar (completed THIRD)
  ├─ Existing simulation worker & reliable job processing
  ├─ Advanced analytics and immutable report history
  ├─ PDF generation and download
  └─ Docker / GitHub Actions / staging / monitoring
                │
                ▼
PostgreSQL (Supabase) + authorized file/object storage
```

*The order above shows ownership/handover, not physical network routing: FastAPI coordinates appropriate services, and database-backed services access PostgreSQL via validated backend sessions.*

---

## 11. Final validation and demo checklist

### Features

- [ ] All 30 baseline personas and 5/10/20/30 modes still work.
- [ ] Improved diversity is observable without implying actual buyer feedback.
- [ ] Product image upload and structured presentation feedback work.
- [ ] Competitor analysis shows provenance, observations dates and appropriate no-data behavior.
- [ ] Facebook/Instagram/TikTok/WhatsApp suggestions are distinct and factual.
- [ ] Analytics charts, trust/purchase intent, persona comparisons and report history work.
- [ ] Seller can export a readable PDF with optional findings and disclaimers.
- [ ] Failure of optional AI services does **not** interrupt ordinary product-post simulation.

### Quality & operations

- [ ] Users cannot access other users' files, competitor data, posts or reports.
- [ ] Database migrations work from a clean database and preserve existing records.
- [ ] CI runs frontend lint/tests/build and backend Ruff/pytest/migration checks.
- [ ] Tokens.bd keys, Supabase credentials and private seller data do not appear in frontend bundles or Git history.
- [ ] Dockerized frontend/backend/worker start successfully in staging.
- [ ] Logs, health checks, job failure visibility, backup and rollback steps are tested.
- [ ] Mobile/desktop and end-to-end flows pass after Shafayet's final merge.
- [ ] A final staged release is approved and verified by all four members.

### Final demo flow

1. **Sign in** to Buyora.
2. **Create a product and post; upload an image.**
3. **Select a platform and simulation size**, then run buyer-persona evaluation.
4. **View image insights** and add at least one **source-labeled competitor observation**.
5. **Inspect improved analytics**, recurring objections and report comparisons.
6. **View platform-specific content suggestions** and export the final report to **PDF**.
7. **Reopen the saved report**, show that results persist, and explain the automated deployment pipeline.

---

## 12. Technical baseline / test commands

Run existing checks from the relevant directories; extend the suites as Phase 2 features are merged.

**Backend**

```bash
cd backend
uv sync --locked
uv run ruff check .
uv run ruff format --check .
uv run pytest
# With a configured staging/test database:
uv run alembic upgrade head
```

**Frontend**

```bash
cd frontend
npm ci
npm run lint
npm run test:demo
npm run build
# Add Playwright or similar real end-to-end tests in Stage 4.
```

**Operational requirements**

- Production migrations run as a separate reviewed deployment step; the API does not create tables at startup.
- Use the existing Python/Node runtime requirements from the repository lockfiles.
- Do not expose the PostgreSQL app schema through an unrestricted public data API.
- Keep CI fake/mock tokens and sample data separate from real Tokens.bd credentials.
- Use provider-specific image capabilities only after verifying the selected model supports vision.

---

## 13. One-line rule for the whole team

> **Shoma builds and freezes the new backend interfaces → Mehdi fills them with AI intelligence → Abu Bakar turns the results into analytics, PDFs and deployable services → Shafayet connects everything in one final frontend pass.**

**The team should change a completed stage only to fix a verified defect or an approved contract problem—not because the next member needs to redesign its interface.**
