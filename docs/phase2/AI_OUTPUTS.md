# Stage 2 callable interfaces and example outputs

Contract version: 1.0. All fixture outputs are examples from test doubles.
Stage 1 installs no optional AI provider and performs no paid provider calls.

| Interface | Input | Output | Integration hook |
| --- | --- | --- | --- |
| `ImageAnalyzer.analyze` | `ImageAnalysisInput` | `ImageAnalysisResult` | `process_image_analysis(factory,id,analyzer,storage)` |
| `MarketAnalyzer.analyze` | `MarketInput` | `MarketResult` | `process_market_analysis(factory,id,analyzer,verify_grounding)` |
| `PlatformContentGenerator.generate` | `PlatformGenerationInput` | `PlatformGenerationResult` | Future durable worker saves a new AI revision after grounding review. |

Definitions are in `backend/app/services/image_analysis.py`, `market_analysis.py`
and `platform_content.py`. `ExecutionBudget` and immutable attachment envelopes
are in `backend/app/schemas/phase2.py`. JSON Schemas in `schemas/` and matching
fixtures in `fixtures/` are exercised by `tests/test_phase2_contract.py`.

Image results assess clarity, lighting, composition, background, readability and
description consistency. Each uses `good|needs_improvement|not_applicable|uncertain`
with feedback. These are observable presentation findings; do not claim
authenticity, actual quality or predicted sales. Signed image URLs are private,
short-lived inputs, never output fields or persisted provider payloads.

Market input includes seller product details and 1–20 seller-owned observations
with source URL/note and observation date. Comparisons preserve currencies and
mark unlike currencies `not_comparable`; this is not proof of equivalent units
or products. Stage 2 must check units/comparability/staleness and reject
unsupported claims through `verify_grounding`. Result fields are interpretation
strings/lists and required limitations, never independently verified facts.

Platform results contain content plus warnings. Preserve source-post facts;
do not invent policies, testimonials, discounts or urgency. Generated variants
must be grounded before creating an `origin:"ai"` revision. Seller revisions
remain `origin:"seller"` and never overwrite the source promotional post.

## Budget and durable integration

All input/output contracts default historical JSON to `schema_version:"1.0"`.
Input contracts include an `ExecutionBudget`: input/output token caps, one
attempt and a provider timeout. Use `request_budget(db,kind,resource_id)` to
read the saved admission policy. Image and market hooks already supply it to
their analyzers. The platform worker must supply it to its generator.

Before any paid call, tokenize the complete prompt (including instructions and
vision tokens), enforce the saved caps and deadline, and reject unsupported
capabilities. Schema validation alone proves neither grounding nor token use.
Retries require a new reservation. Unknown/failed usage retains its allowance.

The hooks atomically claim pending work and release DB transactions before
storage/provider calls. They catch provider/malformed-result failures and store
safe failed states. They are integration hooks, not a complete queue: the real
worker still needs leases, crash recovery, deadlines and usage accounting.
Never invoke them synchronously from an HTTP request.

Implement `DurableProcessingAdmission.verify_ready` and `enqueue` for all three
kinds (`image_analysis`, `market_analysis`, `platform_generation`). Verify a
healthy worker and persist dispatch using the passed session before its commit.
Do not commit inside admission or use an in-memory/background-task queue.
Production admission stays disabled until these obligations are met.

## Reports and optional failures

The committed `advanced_report.json` fixture defines only Stage 1's optional
attachment section (`OptionalAnalyses`), not Stage 3 advanced metrics or a PDF.
It contains image findings and market input/result snapshots. The existing seven
persona dimensions and score meanings remain unchanged. Attachment selection is
optional; absent findings never block ordinary simulations or historical reads.

## Regenerate and verify

```powershell
cd backend
uv run python scripts/export_phase2_contract.py
uv run python scripts/export_frontend_contract.py
uv run pytest -q tests/test_phase2_contract.py tests/test_phase2_limits.py tests/test_analysis_attachments.py
```

Read `API_CONTRACT.md` for endpoint/error examples and `HANDOVER_CHECKLIST.md`
for acceptance. Metadata for provider model/prompt versions, latency, actual
tokens and fallback flags must be added by the Stage 2 adapter without changing
existing score semantics; until then no such measurements are fabricated.
