# Stage 2 AI interfaces and stored outputs

Contract version remains **1.0**. Stage 2 adds optional metadata and observations;
historical JSON validates with defaults. All fixtures are synthetic and marked
`example_only:true`. Initial implementation checks used mocks and unbilled probes.
The initial DeepSeek live diagnostic failed; later Gemini verification passed,
as recorded below.

| Interface | Production implementation | Stored result |
| --- | --- | --- |
| `ImageAnalyzer.analyze` | `ai.image.VisionImageAnalyzer` | Six presentation findings, severity, observations, suggestions, metadata |
| `MarketAnalyzer.analyze` | `ai.market.GroundedMarketAnalyzer` | Source-derived comparisons, approved actions, limitations, data status, metadata |
| `PlatformContentGenerator.generate` | `ai.platform.GroundedPlatformGenerator` | Platform draft, warnings, metadata; a new immutable revision |

`ai.jobs.DatabaseAdmission` and `ai.jobs.worker_loop` provide production dispatch.
The older direct `process_image_analysis`/`process_market_analysis` hooks remain
for compatibility/tests; they are not the production queue.

## Personas and versions

`GET /simulation-options` exposes 30 distinct profiles and Quick 5, Standard 10,
Deep 20 and Extended 30 modes. The original 11 IDs remain stable. Nineteen new
profiles express buying priorities without demographic inference. Adaptation
includes category, price, priorities, budget and platform; custom edits survive.
Near-duplicate priorities are rejected. Exact repeated sentences are removed;
repeated cross-persona reactions are flagged as `repeatedLanguage` without
removing scores or rewriting previously completed evaluations.

Use `language:"en"` or `"bn"`. Romanized Bangla requests use `language:"en"` plus
`writing_style:"banglish"` for simulations/persona adaptations. Script/word checks
reject obvious mismatches, not certify fluency. Seven scores retain their
existing meanings and `buyer-perspectives-v2` rules. Buyers are fictional.

Current versions: `contextual-personas-v2`, `buyer-evaluator-v2.3`,
`image-presentation-v1`, `market-evidence-v1`, `platform-grounded-v1`.
Queue configuration includes `buyora-optional-ai-v2`; bump this whenever optional
adapter behavior changes. Changed configuration fails queued work safely.
Historical reports keep their saved versions and results.

## Metadata and provenance

Results expose `metadata`; resource responses also expose `processing_metadata`,
including failed work. Historical metadata can be null.

- `source`: `ai`, `fallback` or `unavailable`.
- `model`, `prompt_version`, `evaluated_at`, safe `failure_code` and `warnings`.
- `input_tokens`/`output_tokens`: provider usage or null when unknown.
- `latency_ms`: measured adapter duration, not a performance guarantee.
- `input_token_bound`: preflight allowance check, separate from actual usage.

Platform revision `origin` is `ai`, `fallback` or `seller`. Unknown usage never
becomes zero or a refunded reservation. Synthetic samples explicitly say tokens
and latency were not measured. Analytics/PDF consumers must support null metadata.

## Vision capability and limitations

The configured model must be accessible to the API key and have verified image
support. Explicit capability denials are always honored. The pinned
`google/gemini-3.8-flash` policy is verified against provider documentation and a
live image challenge; other models require explicit `/models` capabilities.
The adapter validates private PNG/JPEG/WebP bytes (5 MB, 25 MP, nonanimated),
applies orientation and downsizes to 1024 pixels before sending base64. Signed
URLs must match the configured storage origin/bucket and cannot redirect. They
are not persisted or forwarded to the model; only the private backend snapshot
key persists to preserve the historical image.

Gemini uses `/chat/completions` with one bounded PNG and low image detail. The
complete system/schema/messages are counted conservatively as UTF-8 bytes,
plus **8192 image tokens and 1024 framing tokens**. Every call validates PNG
bytes/dimensions (maximum 1024 pixels per side) and enforces the saved input cap
before inference, plus the saved output cap/deadline. Provider usage exceeding
the bound fails safely without retry. This is a conservative budget strategy,
not the gateway's flat image estimate or a currency-charge guarantee. Google
documents image allocations of 1120 tokens at default/high and 2240 at ultra high
for Gemini 3; the reserved allowance includes substantial headroom. See
[Google media resolution](https://ai.google.dev/gemini-api/docs/media-resolution)
and [the exact provider model](https://tokens.bd/models/google/gemini-3.8-flash).

For other models, `/messages/count_tokens` must natively count the complete
prompt/image. `x-tokens-estimated:true` is rejected. Native counts receive 10%
plus 512 tokens of headroom. The unknown-capability DeepSeek configuration remains
unverified for images. Use `TOKEN_BD_VISION_MODEL` to select a separate image
model; the text/simulation model remains independent. Readiness never generates
paid content. Missing/invalid/oversized images, malformed output and unsupported
budget strategies fail safely. There is no fabricated image fallback. Findings
describe presentation, not authenticity, actual quality or predicted conversion.

Provider references: [vision](https://tokens.bd/docs/vision),
[token counting](https://tokens.bd/docs/token-counting),
[model catalog](https://tokens.bd/docs/model-catalog).

### Requested live verification

On 2026-11-28, one diagnostic image-inference request was attempted against the
previous DeepSeek model with a synthetic 192×96 PNG and a 256-token cap. It failed
with `provider_unavailable`; no usage response or visual answer was received and
the billing outcome is unknown. It was not retried. Subsequent unbilled checks
found the exact model accessible, with missing capability metadata and an
estimated image-token count (`x-tokens-estimated:true`). These checks do not prove
the model lacks vision; successful DeepSeek image reading remains unverified.

The 29 adapter/queue regression tests passed. Production admission and `.env`
were not changed. The structured diagnostic evidence is in
[vision_live_check.json](verification/vision_live_check.json). This diagnostic
does not establish a successful production storage-to-analysis workflow.

The user then selected Gemini 3.8 Flash. Its diagnostic challenge passed: the
model identified the blue square on the left and green circle on the right and
returned valid analysis JSON (1673 input / 426 output tokens reported). The normal
`VisionImageAnalyzer` subsequently passed using an actual private Supabase upload
and signed URL, with 363 input / 525 output tokens reported, 23996 ms adapter
latency and a conservative 11923-token input bound. The temporary object was
deleted successfully. `.env` now selects Gemini for images, while text/simulation
keeps DeepSeek. Structured findings and usage are saved in
[gemini_vision_live_check.json](verification/gemini_vision_live_check.json).
The model/adapter/private-storage path is live-verified; this check created no
application records and does not claim a persisted HTTP job was submitted.

## Grounded market and platform output

Market snapshots preserve source URL/note, observation date and comparison date.
Price comparisons require matching product names/categories, equal currencies
and explicit compatible package units. kg/g, l/ml and pieces normalize, including
Bangla numerals. Ambiguous quantities, unlike currencies/items, missing sources,
stale/future records and unknown units are excluded with limitations. The default
maximum age is 90 days (`MARKET_EVIDENCE_MAX_AGE_DAYS`). Matching names/units do
not verify quality or offer eligibility; source offer terms display separately.

No eligible evidence produces `data_status:"insufficient_data"` without a model
call. AI ranks eligible evidence and finite action IDs; code renders source facts
and verifies grounding. There is no browsing, currency conversion or invented
market trend. The service accepts empty evidence; HTTP creation still requires
1–20 selected evidence IDs, so the UI should avoid generation without competitors.

Platform AI selects approved hooks and seller fact IDs. Code composes Facebook
paragraphs, Instagram bullets/hashtags, TikTok walkthrough plans and compact
WhatsApp drafts. Whole facts are kept or omitted to fit channel draft limits;
policies are not cut midway. Supplied offers/CTAs survive or a generic message
CTA is used. New reviews, discounts, urgency and shipping promises are forbidden.
These are bounded suggestions for review, not publication or unrestricted copy
rewriting. Seller claims remain unverified. Provider/schema/grounding failures
produce labeled deterministic fallbacks when `LLM_FALLBACK_ENABLED=true`;
otherwise the resource fails safely. Core simulations do not depend on optional AI.

## Durability and budgets

Admission needs a matching heartbeat newer than 30 seconds advertising the kind.
A provider callable or flag alone cannot enable acceptance. Seller lock,
reservation, resource and immutable dispatch snapshot commit together. The
optional queue runs beside the core queue in the embedded worker or `worker.py`.
Provider calls never run inside HTTP requests or database transactions.

Workers use PostgreSQL `FOR UPDATE SKIP LOCKED`, renewed 90-second leases,
per-call deadlines and saved output/input caps. Text bounds include full UTF-8
instructions/schema/messages plus headroom. Each optional reservation allows
one provider attempt with no SDK retry. Expired in-flight work becomes
`interrupted` and is never automatically replayed. Unknown usage keeps the daily
allowance. Lease tokens prevent late writes; seller revisions win over in-flight
AI completion. Old pending rows without dispatch are not silently recharged.

## Reproduce samples and checks

`fixtures/stage2_outputs.json` provides 30 profiles, English/Bangla/Banglish
reactions, mocked vision success/unavailability, comparable/insufficient market
results and four labeled platform fallbacks. JSON schemas and OpenAPI are in
this directory; generated frontend types match current routes.

```powershell
cd backend
uv run python scripts/export_phase2_contract.py
uv run python scripts/export_stage2_examples.py
uv run python scripts/export_frontend_contract.py
uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv run python scripts/check_simulation_setup.py
uv run python scripts/check_stage2_setup.py --provider
```

The last command only probes catalog/counting; it never generates paid content.
See [Mehdi's handoff](handoffs/02-mehdi-to-abu-bakar.md). Stage 3 owns advanced
analytics, PDFs and deployment.
