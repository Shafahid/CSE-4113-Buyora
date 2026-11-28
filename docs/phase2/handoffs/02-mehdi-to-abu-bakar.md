# Stage 2 — Mehdi to Abu Bakar

Prepared: 2026-11-28. Contract: 1.0. Target migration: 0018.
Status: implementation and regression checks complete; PR merge and recipient
acceptance remain pending. No teammate approval is implied.

## Delivered scope

- **MH1:** 30 curated buyer profiles retaining the original IDs; category,
  priorities, budget and platform context; English/Bangla and explicit Banglish;
  duplicate-priority rejection, repeated-sentence removal and repeated-reaction
  flags. Quick 5, Standard 10, Deep 20 and Extended 30 work. Seven dimensions and
  the existing scoring-rule version retain their meanings.
- **MH2:** verified-capability vision adapter, safe bounded private image loading,
  six presentation dimensions with severity/observations/suggestions, strict
  schema and unavailable behavior. It does not fabricate image fallback results.
- **MH3:** source/date snapshots, declared-unit/currency/item comparisons,
  staleness exclusions and insufficient-data results. AI ranks finite eligible
  evidence/action IDs; code renders and verifies grounded statements.
- **MH4:** distinct Facebook, Instagram, TikTok and WhatsApp drafts using approved
  hooks and seller facts; whole-fact length limits; explicit fallback origin and
  metadata. There is no automatic publication or invented commercial claim.

Production modules: `backend/app/services/ai/{provider,image,market,platform,jobs}.py`.
The three Stage 1 Protocol methods and endpoint paths remain stable. Read
[AI outputs](../AI_OUTPUTS.md), [API contract](../API_CONTRACT.md) and
[data model](../DATA_MODEL.md) for exact fields and limitations.

## Integration changes

The documented integration additions are migration 0018 and nullable metadata
on existing image/market/platform records. Private `buyora.ai_jobs` stores an
immutable dispatch snapshot, saved execution budget, configuration, leases and
usage; `buyora.ai_worker_heartbeats` gates admission by capability and freshness.
Platform revision origin now accepts `fallback`. Existing public resource routes
add only optional metadata fields; existing results retain schema version 1.0.
Generated schemas, OpenAPI and frontend types reflect these additions.

Admission atomically saves reservation/resource/dispatch under the seller lock.
The optional worker runs beside the existing simulation/persona worker, embedded
or through `python worker.py`. Claims use PostgreSQL SKIP LOCKED, renewed leases
and protected completion tokens. One optional provider attempt is allowed per
reservation. Expired unknown calls fail as interrupted rather than rebilling.
Late AI completion cannot replace a seller's saved revision. Historical reports
and previously completed persona outputs are preserved across upgrades/retries.

## Configuration and live limitations

Keep provider/storage secrets backend-only. New settings are `PHASE2_AI_ENABLED`
(default true), optional `TOKEN_BD_VISION_MODEL`, and
`MARKET_EVIDENCE_MAX_AGE_DAYS` (90). Existing per-seller optional request/daily
reservation limits and input/output/deadline settings remain effective. Setting
`PHASE2_AI_ENABLED=false` disables optional admission and its worker.

The original DeepSeek catalog check omitted image-capability metadata and its
vision count was estimated. That model remains unverified for images. The user
subsequently selected `TOKEN_BD_VISION_MODEL=google/gemini-3.8-flash`, independently
of the unchanged DeepSeek text/simulation model.

Later on 2026-11-28, at the user's request, one capped live image diagnostic was
attempted with a synthetic 192×96 PNG and `max_tokens:256`. It failed with
`provider_unavailable`; no successful visual answer or usage response was received.
Billing is unknown and the inference was not retried. Unbilled follow-up checks
still found missing image-capability metadata and estimated counting. The 29
adapter/queue tests passed again at that point. Production settings and `.env`
were unchanged during that initial failed DeepSeek test.
See [the diagnostic evidence](../verification/vision_live_check.json).

The subsequent Gemini live challenge succeeded (1673 input / 426 output tokens)
and identified the undisclosed blue-square/green-circle geometry correctly.
The normal image adapter also succeeded with a real private Supabase upload and
signed URL (363 input / 525 output tokens, 23996 ms, input bound 11923). The
temporary object was removed. See [Gemini evidence](../verification/gemini_vision_live_check.json).
No application records were created by those adapter checks. Current runtime
schema and all three optional worker capabilities report ready/healthy.

The pinned Gemini policy uses full UTF-8 prompt bytes plus 8192 image tokens
and 1024 framing tokens for exactly one verified PNG with sides at most 1024.
This conservative allowance is based on Google's documented per-image allocation,
not the gateway's estimate. All saved input/output/deadline caps remain enforced.
Missing access or explicit capability denial still blocks it. Other models retain
the native-count requirement. Queue configuration is now `buyora-optional-ai-v2`.
Text market/platform execution retains bounded mock and fallback coverage.

Run from `backend/`:

```powershell
uv run python scripts/check_simulation_setup.py --apply
uv run python scripts/check_stage2_setup.py --provider
```

The second command never requests paid content. A successful schema check does
not by itself mean a worker is running. Restart API/worker after upgrading. When
using a standalone worker, disable the embedded worker in the API process.
Previously saved pending optional rows without durable dispatch require explicit
operator review; they are not silently charged or replayed by this migration.

## Validation evidence

Verified on 2026-11-28:

- Full backend suite with disposable PostgreSQL 17: **291 passed**. Seventeen
  existing LangSmith dependency deprecation warnings remain.
- Four PostgreSQL integration tests: clean upgrade/data preservation, concurrent
  quota admission, old report/API preservation, and queue locking/expired-call
  recovery. Each uses its own UUID database and refuses a remote test server.
- Tests cover 5/10/20/30 modes with metered mocked usage/latency, seven scores,
  catalog diversity, languages, private image dispatch, malformed output,
  vision/counting failures, unit/currency/staleness exclusions, grounded actions,
  platform differences, labeled fallbacks, budgets, snapshots and late writes.
- Ruff lint and format checks pass (131 Python files).
- Regenerated frontend contract passes `tsc --noEmit`.
- Configured application database upgraded from 0017 to **0018**. Both private
  queue tables, all three metadata columns and absence of public/client table
  grants were verified. Market/platform heartbeats were healthy; image admission
  was unavailable as intended. A transient database DNS failure occurred during
  one post-check; subsequent connectivity and revision checks succeeded. The final
  catalog response lacked capability metadata, rather than declaring text-only
  support; absence is treated as unknown, never as verified image support.
- `git diff --check` passes. The temporary PostgreSQL container is removed after
  verification; no test data is written to the application database.

Reproduce using the commands in [AI outputs](../AI_OUTPUTS.md). For PostgreSQL,
set `BUYORA_TEST_POSTGRES_URL` to a disposable localhost PostgreSQL admin URL;
ordinary pytest skips those four tests when it is absent. The test fixture never
reads the developer `.env` and drops only its own UUID database.

## Subsequent Gemini regression verification

After enabling the pinned Gemini policy: **294 passed, 4 skipped**, with the
four opt-in PostgreSQL tests skipped because no disposable server was configured
for this run. The earlier migration audit passed all four PostgreSQL tests; this
update makes no schema changes. The 36 focused Gemini/optional-AI tests and Ruff
lint/format checks (133 Python files) also passed. Runtime image, market and
platform heartbeats matched the new configuration and reported healthy.

## Abu Bakar's starting point

Use stored outputs and immutable `report.optionalAnalyses` snapshots for analytics
and PDFs. Do not call the provider while reading/exporting a report. Show simulated
buyer conclusions as simulated; distinguish `ai`, `fallback`, `unavailable` and
legacy null provenance. Preserve source/date, observation limitations and usage
unknowns. Optional findings never change the existing seven score meanings.

Synthetic examples are in [stage2_outputs.json](../fixtures/stage2_outputs.json):
30 profiles, three reaction languages, mocked vision success/unavailability,
market comparisons/insufficiency and four platform drafts. The example wrapper
and warnings identify synthetic values; no personal data or credentials appear.

Stage 3 analytics, PDF, Docker/CI/staging and Stage 4 feature UI remain outside
this implementation. The existing report attachment fixture is not a completed
advanced analytics/PDF contract.

## Remaining team acceptance

- [ ] Review and merge the Stage 2 implementation PR into main; record its URL.
- [ ] Abu Bakar accepts these stored contracts and samples for reporting/PDF work.
- [x] Configure and live-test Gemini 3.8 Flash for image analysis with a validated
      conservative token budget and healthy image worker capability.
- [ ] Perform the team's release smoke test and record deployment acceptance.
