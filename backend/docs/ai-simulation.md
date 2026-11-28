# Mehedi's AI simulation implementation

## Accepted scope and ownership

Stage 2 provides **30 curated personas**, retaining the original 11 IDs and
adding 19 buying-priority perspectives. Quick 5, Standard 10, Deep 20 and Extended
30 modes use this catalog. Selected profiles alone are evaluated. Custom profiles
remain supported within `SIMULATION_MAX_PERSONAS` (default 30, minimum selection
2). No claim of representative population sampling is made. Optional image,
market and platform adapters are documented in
[Stage 2 AI outputs](../../docs/phase2/AI_OUTPUTS.md).

The A1–A4 services are in `persona_engine.py`, `persona_diversity.py`,
`trust_scoring.py`, `llm.py` and `report_insights.py`. `persona_jobs.py` and the
execution routes provide the integration contract for the frontend and worker.

## Personas and languages

Context mode attaches product name, platform, audience needs and location to
each selected profile. Unedited catalog roles and priorities are available in
English and Bangla. Edited/custom priorities are preserved; translating those
requires AI mode. AI variants receive the complete saved product/post/audience
snapshot and must retain all selected IDs and distinct priorities. Existing
names, ages, locations, budget sensitivity and identity styling survive adaptation.
Age and location must not be used to infer buying behavior.

Diversity validation compares normalized needs, not names or identity fields.
It rejects exact matches, token Jaccard similarity >= 0.88 or sequence similarity
>= 0.94. This is a near-text-duplicate safeguard, not a semantic-equivalence
guarantee across languages. Custom English text and a Bangla translation can
still describe the same concern; users should review generated variants.

Evaluation output must contain Bangla characters in each main reaction field
when `language: "bn"` is requested. This checks script presence, not fluency.
Fixed Banglish fixtures cover price, delivery charges, COD and return concerns.

## Provider and evaluation contract

LiteLLM is the replaceable provider adapter; LangGraph dispatches evaluations
with bounded concurrency. Configure `TOKEN_BD_API_URL`, `TOKEN_BD_API_KEY`,
`TOKEN_BD_MODEL` and optionally `LLM_PROVIDER` on the backend only. Tests mock the
provider and never use paid API calls. The immutable run snapshot includes the
provider identity, prompt and rubric versions, profiles and execution policy.

The model returns seven integer scores (0–100), comment, reason, positive,
question, evidence, objections and one explanation for each score in canonical
order. Evidence quotes must be exact substrings of supplied input. This rejects
invented citations; it does not independently verify seller claims or guarantee
that every free-text model statement is factual. Product/post text is treated as
untrusted data in prompts. Responses with malformed JSON, unsupported evidence,
missing score explanations, invalid scores or the wrong script are rejected.

Version constants:

- Personas: `contextual-personas-v2`
- Prompt: `buyer-evaluator-v2.3`
- Rules: `buyer-perspectives-v2`

Change the relevant version whenever behavior changes. Old saved reports retain
their existing snapshot and labels; new versions produce new cache fingerprints.

## Seven score dimensions

| Dimension | Meaning |
| --- | --- |
| Interest | Whether supplied product details and demonstrations attract this fictional buyer |
| Relevance | Fit with the buyer's stated needs |
| Value | Whether described benefits and the supplied price establish value |
| Price fit | Price and delivery-cost clarity against stated budget sensitivity |
| Trust | Supplied payment, delivery, returns, contact and product-evidence information |
| Clarity | Whether the saved post makes key information and the next step explicit |
| Purchase intent | A fictional readiness assessment constrained by unresolved priorities |

AI scores are judgments under the versioned prompt. Fallback scores below are
deterministic information-completeness assessments. Neither is a calibrated
probability of buying, a sales forecast, or real customer feedback.

Trust signals identify mentions of price, delivery, delivery charges, returns,
warranty, payment, details, ordering, contact and product demonstrations/reviews.
Each records `supplied`, `visible`, `negative`, `source` and verbatim `evidence`.
Structured product facts are distinct from information visible in the post.
Questions and phrases such as “coming soon” do not count as confirmed caption
details. Explicit negative policies remain negative; a mention of “No returns”
does not become a return benefit. Detection uses bounded keyword patterns, so
ambiguous wording, mixed positive/negative clauses and unsupported synonyms can
require manual review. No price is inferred from an arbitrary number alone.

## Deterministic fallback formulas

Let `P` be the number of supplied signals (maximum 10), `V` the number visible
in the post, and each signal indicator be 1 when supplied and 0 otherwise.

- Interest = 45 + 15 × details + 10 × proof.
- Relevance = 60 if details are supplied, otherwise 40.
- Value = 45 + 15 × details + 10 × price.
- Price fit = 45 + 15 × price + 10 × delivery-cost; subtract 10 when budget
  sensitivity is high and delivery cost is missing.
- Trust = min(85, 35 + 8 × supplied count among delivery, returns, payment,
  contact and proof).
- Clarity = min(90, 35 + 6 × V + 3 × P).
- Purchase intent = min(75, rounded mean of trust/price-fit/clarity minus 8 per
  missing or negative persona priority). A COD buyer with a negative payment
  policy is capped at 30. All final scores are clamped to 0–100.

Persona priorities: budget → price/delivery-cost; bargain → price/details;
COD → payment/delivery; skeptic → returns/details; office → delivery/ordering;
gift → delivery/details; impulse → ordering/price; repeat → details/returns;
trend → details/proof; Gen Z → proof/ordering; traditional → contact/ordering.
Custom IDs use details/price/delivery. The fallback uses declared budget
sensitivity, with no demographic inference, random seed or persona-position bonus.

Each score includes an explanation identifying relevant gaps or supplied claims.
Fallback verdicts explicitly record `evaluation_source: "fallback"`, the failure
code and rules version. `prompt_version` is null for fallback. The UI and PDF
label these results and disclose that they enter completed-result averages.

## Aggregation, recommendations and revision

A persona's overall score is the arithmetic mean of seven dimensions, rounded
half-up. Frontend report means use completed persona scores; failed evaluations
are excluded, and no completed result means “Unavailable”. Sentiment follows
overall-score thresholds: >=76 Interested, 60–75 Has questions, below60
Unconvinced. These are presentation labels, not independently trained sentiment.
No additional backend virality or boost-readiness prediction is implemented.
The 60-viewer spread graph remains a fictional local illustration, distinct from
evaluated personas and predicted reach.

Recurring objections are grouped by detected topic; frequency is the number of
distinct completed personas, not repeated mentions. Failed rows are excluded.
Topic groups normalize duplicate questions; unmatched questions use normalized
text. Recommendations combine missing visible information with those concerns.
Two or more buyers asking a topic makes it high priority; price, delivery-cost
and payment gaps are also high priority. Other topics are medium priority.

Caption revision uses only selected recommendation IDs from the saved report.
Structured product facts can be copied; unknown terms become bracketed
verification placeholders. It never invents a discount, warranty, stock count or
delivery promise. Existing seller-written claims remain in the original body and
must still be checked. No additional LLM request is made for recommendations or
revision. Editing a draft is allowed; publishing remains the seller's decision.

## Durable jobs, cache, retry and safeguards

`POST /persona-adaptations` accepts the same run inputs plus `mode: "context"`
or `"ai"`. Example (use real owned version and full catalog/profile objects):

```typescript
const options = await simulationApi.options();
const job = await simulationApi.adapt({
  request_id: crypto.randomUUID(),
  post_version_id: 42, // An owned, saved post version.
  language: "bn",
  audience: { location: "Dhaka", needs: "Daily commuting" },
  personas: options.profiles.slice(0, 2),
  mode: "ai",
  fresh: false,
});
```

The typed frontend client lives in `frontend/src/lib/simulation-api.ts`.
Context mode returns immediately. AI mode returns a saved job ID; poll
`GET /persona-adaptations/{id}` until completed/fallback. The same request UUID
is idempotent; changed inputs with that UUID return 409. Matching inputs reuse
saved/queued jobs unless `fresh: true`. Fresh generation is a deliberate new
request. Failed/interrupted generation produces contextual profiles marked as
fallback; a new request with fresh=true explicitly retries the provider.

Simulation results have equivalent seller-scoped snapshot caching. Merely opening
a report never calls the model. Automatic retries use bounded backoff; there are
at most six attempts per perspective across manual retries. Unknown in-flight
outcomes after a worker crash are not automatically reissued. Explicit single
retry can replace a completed fallback with AI; bulk “retry missing” preserves
all completed verdicts including fallbacks.

`LLM_FALLBACK_ENABLED=true` enables rule-based recovery. Setting false preserves
partial failures instead. Per-run `SIMULATION_MAX_MODEL_CALLS=66` limits dispatch
attempts; `SIMULATION_TOKEN_BUDGET=200000` conservatively reserves input bytes/3
plus output allowance and overhead under a run lock before dispatch. The estimate
includes the actual provider prompt, schema and evidence choices. When the provider
reports both input and output usage, that actual total replaces the reservation
for the attempt. In-flight calls and calls with unknown or partial usage retain
their conservative allowance. Retried attempts are accounted for separately.
Current and saved policy limits are both honored (the stricter value wins). These are
token/attempt guards, not a currency-based invoice limit. Usage records actual
reported input/output tokens and summed provider latency; `modelCalls` counts
dispatch attempts, which may fail before a provider bills them. Adaptation uses
one bounded provider call and its own token reservation, not a shared account
spending ledger. Production concurrency uses PostgreSQL row locks.

Evaluator prompt `buyer-evaluator-v2.2` supplies short verbatim evidence choices
and asks for concise explanations. Quotes keep their source language, including
when the requested explanation language differs. Validation accepts differences
in whitespace and restores the source excerpt; invented, translated or combined
claims remain invalid. Automatic retries receive the failed validation check as
targeted guidance, within the existing call, token and attempt limits. The prompt
version changes the cache fingerprint for new requests; opening a saved report
does not regenerate it.

Migration 0010 adds the durable persona-adaptation table. The verification script
supports safe inspection or explicit application from revision 0009; no customer
rows are changed. Frontend pending job IDs/request UUIDs are saved in the
account-local draft. Edits invalidate the pending result, preventing stale output
from replacing a newer draft. Session guards prevent cross-account publication.

## Verification and handoff

From `backend/`:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\ruff.exe check .
.\.venv\Scripts\ruff.exe format --check .
.\.venv\Scripts\python.exe scripts/verify_ai_migration.py
.\.venv\Scripts\python.exe scripts/export_frontend_contract.py
```

From `frontend/`: `npm test`, `npm run test:integration`, `npm run lint`,
`npx tsc --noEmit` and `npm run build`. Integration tests start isolated SQLite
and fake providers without reading `.env`. The live schema verifier is separate
and reads backend settings. Unit/API checks cover 2, 5, 10, 20 and 30 selected
profiles, repeatability, multilingual signals, evidence grounding, malformed
responses, provider classifications, fallback, reservations, cached/fresh jobs,
ownership, interruption and caption revision from immutable inputs.
