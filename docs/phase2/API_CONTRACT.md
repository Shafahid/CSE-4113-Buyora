# Phase 2 API contract — Stage 1 baseline

Contract version: **1.0**. This is the implemented baseline for team review;
approval and Mehdi's acceptance must be recorded in HANDOVER_CHECKLIST.md.
Machine-readable requests, responses and validation rules are in [openapi.json](openapi.json).
Regenerate from `backend/` with `uv run python scripts/export_phase2_contract.py`.

## Authentication and errors

Use `POST /auth/login` and the HttpOnly `buyora_session` cookie. Send credentials
on browser requests and an allowed `Origin` on mutations. `CORS_ORIGINS` controls
allowed origins; `Retry-After` is exposed to browser clients.
Ownership failures return 404 without revealing another seller's records.
Ordinary errors use `{"detail":"message"}`; Pydantic validation uses FastAPI's
422 `detail` array. Codes: 401 session missing/expired, 403 untrusted Origin,
404 inaccessible record, 409 conflicting revision, 413 upload over 5 MB,
422 invalid/oversized AI input, 429 rate/token allowance exhausted, 503 storage
or durable processor unavailable. 429 includes `Retry-After` in seconds.

## Endpoint inventory

| Method | Path | Behavior |
| --- | --- | --- |
| POST | `/products/{product_id}/images` | Multipart `file`; validated JPEG/PNG/WebP, up to 5 MB; 201. |
| GET | `/products/{product_id}` | Includes owned images and five-minute signed URLs. |
| PUT | `/products/{product_id}/images/{image_id}` | Replace object, preserve image ID/order; 200 or race conflict 409. |
| DELETE | `/products/{product_id}/images/{image_id}` | Remove gallery entry; retain objects referenced by analysis history; 204. |
| POST | `/competitor-evidence` | Save a seller observation; 201. |
| GET | `/competitor-evidence` | Search `q`; filter product/platform/date; paginated. |
| GET/PATCH/DELETE | `/competitor-evidence/{id}` | Read/edit/soft-delete owned observation. |
| POST | `/products/{product_id}/images/{image_id}/analyses` | `{"language":"en"}`; 202 only after transactional admission. |
| GET | `/products/{product_id}/images/{image_id}/analyses` | Paginated history, including replaced/deleted images. |
| GET | `/products/{product_id}/images/{image_id}/analyses/{id}` | Owned analysis/result/status. |
| POST | `/products/{product_id}/market-analyses` | `{"competitor_evidence_ids":[1],"language":"en"}`; 202. |
| GET | `/products/{product_id}/market-analyses` | Paginated snapshot/result history. |
| GET | `/products/{product_id}/market-analyses/{id}` | Owned immutable input snapshot and result. |
| POST | `/posts/{post_id}/variants` | Exact `source_version_id`, platform and optional seller content; 201. |
| GET | `/posts/{post_id}/variants` | Paginated variants, optional `platform` filter. |
| GET | `/posts/{post_id}/variants/{id}` | Variant and latest revision. |
| POST/GET | `/posts/{post_id}/variants/{id}/revisions` | Append seller revision/list revision history. |

Pagination uses `offset>=0`, `1<=limit<=100`, default limit 50. Lists return
`items,total,offset,limit`; revision lists return an array. IDs are positive
integers, except existing simulation-run UUIDs. Languages are `en` and `bn`.
Platforms are `facebook`, `instagram`, `tiktok`, `whatsapp`.

## Competitor provenance

Competitor name, product name and observation date are required. Price/currency
must be provided together. `source_url` is an optional HTTP(S) reference without
embedded credentials; it is stored, never fetched. `source_note` describes an
offline/manual source. Both remain nullable for compatibility with old clients
and observations whose source is unknown. Unknown provenance must be displayed
as unknown, never invented. All records are seller-supplied and unverified.
Market snapshots copy these fields and the observation date before dispatch.

```json
{
  "competitor_name": "Example Store",
  "product_name": "Canvas bag",
  "price": "125.00",
  "currency": "BDT",
  "platform": "facebook",
  "observed_at": "2026-11-28",
  "source_url": "https://example.com/listing",
  "source_note": "Seller-entered example observation"
}
```

## Job states and availability

Image/market: `pending -> processing -> completed|failed`.
Platform: `pending -> processing -> ready|failed`; seller-written content starts
at `ready`. Results are null until completed. Errors never include provider
messages, keys, SQL or private storage keys.

No production optional-AI processor is installed in Stage 1. All three request
paths reject new generated work with 503 until a `DurableProcessingAdmission`
implementation verifies worker health and enqueues transactionally. A boolean
flag cannot enable processing. Manual variants and saved history remain usable.
Only test doubles produce sample results during Stage 1.

## Admission limits and Stage 2 budget obligation

The three optional AI kinds share each seller's allowance, across API processes:

| Setting | Default | Meaning |
| --- | --- | --- |
| `PHASE2_AI_REQUESTS_PER_MINUTE` | 10 | Accepted jobs in the preceding 60 seconds. |
| `PHASE2_AI_DAILY_TOKEN_BUDGET` | 250000 | Conservative reservations per UTC day. |
| `PHASE2_AI_MAX_INPUT_TOKENS` | 16384 | Per-call input allowance, including vision tokens. |
| `PHASE2_AI_MAX_OUTPUT_TOKENS` | 4096 | Provider output cap. |
| `PHASE2_AI_TIMEOUT_SECONDS` | 90 | Provider deadline. |

Each accepted job reserves the full input+output allowance; unknown usage is
never refunded. Admission also rejects text payloads whose UTF-8 byte size is
over the input allowance. It serializes on the seller row and commits the
reservation, resource and dispatch together; failures roll all three back.
Manual variants, reads and unavailable requests consume no allowance. These are
token safeguards, not an estimate or guarantee of currency charges. Existing
simulation/persona jobs retain their existing budgets and retry rules.

Mehdi's adapters must read the saved `ExecutionBudget`, count the complete prompt
and vision input before calling, enforce output limits/deadlines, and make at
most one provider attempt per reservation. If the provider cannot enforce the
allowance, reject the job. Further paid attempts require fresh admission.
Do not enable production processing until the durable worker implements this.

## Optional report attachments

`POST /simulation-runs` and preview accept optional `image_analysis_ids` (up to
10) and `market_analysis_ids` (up to 5). IDs must be positive and unique.
Only completed, same-seller, same-product analyses can attach. They are copied
into the run's immutable `inputs.optional_analyses` before evaluation; analysis
selection affects the cache fingerprint. Reports expose `optionalAnalyses`.
No attachment changes the seven existing persona score dimensions.

Image attachments contain an opaque image revision, never a storage key or
signed URL. Market attachments retain source/date input snapshots. Old reports
are not rewritten; consumers treat an absent attachment section as empty.
Stage 3 owns advanced aggregations and PDF endpoints.

## Reproducible HTTP examples

Use an authenticated cookie jar; do not commit it. These are local examples;
replace numeric IDs with records created by the same seller.

```bash
curl -c cookies.txt -H 'Origin: http://localhost:3000' -H 'Content-Type: application/json' -d '{"email":"seller@example.com","password":"YOUR_PASSWORD"}' http://localhost:8000/auth/login
curl -b cookies.txt -H 'Origin: http://localhost:3000' -F 'file=@example.png' http://localhost:8000/products/1/images
curl -b cookies.txt -H 'Origin: http://localhost:3000' -H 'Content-Type: application/json' -d '{"competitor_name":"Example Store","product_name":"Bag","observed_at":"2026-11-28","source_url":"https://example.com/bag"}' http://localhost:8000/competitor-evidence
curl -b cookies.txt 'http://localhost:8000/competitor-evidence?q=Bag&limit=10'
curl -b cookies.txt -H 'Origin: http://localhost:3000' -H 'Content-Type: application/json' -d '{"language":"en"}' http://localhost:8000/products/1/images/1/analyses
curl -b cookies.txt -H 'Origin: http://localhost:3000' -H 'Content-Type: application/json' -d '{"competitor_evidence_ids":[1],"language":"en"}' http://localhost:8000/products/1/market-analyses
curl -b cookies.txt -H 'Origin: http://localhost:3000' -H 'Content-Type: application/json' -d '{"source_version_id":1,"platform":"facebook","content":{"headline":"Canvas bag","body":"Example seller caption"}}' http://localhost:8000/posts/1/variants
```

All fixtures in `fixtures/` are marked `example_only:true`; validate/use their
`payload`. They contain no customer observations or live model output.
