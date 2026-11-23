import type { DemoState } from "./demo-data";

type RecordValue = Record<string, unknown>;
const object = (v: unknown): v is RecordValue =>
  !!v && typeof v === "object" && !Array.isArray(v);
const strings = (v: RecordValue, keys: string[]) =>
  keys.every((k) => typeof v[k] === "string");
const list = (v: unknown, check: (item: unknown) => boolean) =>
  Array.isArray(v) && v.every(check);
const identifiedList = (v: unknown, check: (item: unknown) => boolean) =>
  Array.isArray(v) &&
  v.every(
    (item) =>
      check(item) &&
      object(item) &&
      typeof item.id === "string" &&
      item.id.trim(),
  ) &&
  new Set(v.map((item) => item.id)).size === v.length;
const score = (v: unknown) =>
  typeof v === "number" && Number.isFinite(v) && v >= 0 && v <= 100;
const date = (v: unknown) =>
  typeof v === "string" && Number.isFinite(Date.parse(v));
const language = (v: unknown) => v === "en" || v === "bn";
const stringList = (v: unknown) => list(v, (x) => typeof x === "string");
const count = (v: unknown) => typeof v === "number" && Number.isInteger(v) && v >= 0;
function product(v: unknown): boolean {
  return (
    object(v) &&
    strings(v, [
      "id",
      "name",
      "category",
      "description",
      "features",
      "warranty",
      "delivery",
      "returns",
      "image",
      "art",
    ]) &&
    typeof v.price === "number" &&
    Number.isFinite(v.price) &&
    v.price >= 0 &&
    typeof v.archived === "boolean"
  );
}
function post(v: unknown): boolean {
  return (
    object(v) &&
    strings(v, [
      "id",
      "productId",
      "headline",
      "body",
      "offer",
      "cta",
      "hashtags",
      "platform",
    ]) &&
    list(
      v.versions,
      (x) => object(x) && strings(x, ["id", "body"]) && date(x.createdAt),
    )
  );
}
function persona(v: unknown): boolean {
  return (
    object(v) &&
    strings(v, [
      "id",
      "name",
      "role",
      "age",
      "location",
      "need",
      "budget",
      "color",
      "initials",
    ]) &&
    (v.context === undefined || typeof v.context === "string") &&
    (v.description_language === undefined || language(v.description_language))
  );
}
function audience(v: unknown): boolean {
  return (
    object(v) &&
    strings(v, [
      "location",
      "age",
      "interests",
      "preferences",
      "budget",
      "needs",
    ])
  );
}
function reaction(v: unknown): boolean {
  return (
    object(v) &&
    persona(v.persona) &&
    Array.isArray(v.scores) &&
    v.scores.length === 7 &&
    v.scores.every(score) &&
    score(v.score) &&
    typeof v.status === "string" &&
    ["complete", "failed"].includes(v.status) &&
    ["Interested", "Has questions", "Unconvinced"].includes(
      typeof v.sentiment === "string" ? v.sentiment : "",
    ) &&
    strings(v, ["comment", "reason", "positive", "question"]) &&
    (v.evaluationSource === undefined || ["ai", "fallback"].includes(String(v.evaluationSource))) &&
    (v.fallbackReason === undefined || v.fallbackReason === null || typeof v.fallbackReason === "string") &&
    (v.evidence === undefined || stringList(v.evidence)) &&
    (v.objections === undefined || stringList(v.objections)) &&
    (v.scoreDrivers === undefined || list(v.scoreDrivers, (x) => object(x) && strings(x, ["dimension", "reason"]) && stringList(x.evidence)))
  );
}
export function validReport(v: unknown): boolean {
  return (
    object(v) &&
    strings(v, ["id", "title", "revised"]) &&
    date(v.createdAt) &&
    product(v.product) &&
    post(v.post) &&
    audience(v.audience) &&
    language(v.language) &&
    list(v.applied, (x) => typeof x === "string") &&
    list(v.reactions, reaction) &&
    (v.recommendations === undefined || identifiedList(v.recommendations, (x) => object(x) && strings(x, ["id", "title", "detail", "priority", "addition"]) && (x.evidence === undefined || stringList(x.evidence)) && (x.persona_ids === undefined || stringList(x.persona_ids)) && (x.frequency === undefined || count(x.frequency)))) &&
    (v.objectionGroups === undefined || list(v.objectionGroups, (x) => object(x) && strings(x, ["topic"]) && count(x.frequency) && stringList(x.persona_ids) && stringList(x.questions) && stringList(x.evidence))) &&
    (v.trustSignals === undefined || (object(v.trustSignals) && Object.values(v.trustSignals).every((x) => object(x) && typeof x.supplied === "boolean" && typeof x.visible === "boolean" && typeof x.negative === "boolean" && ["post", "product", null].includes(x.source as string | null) && stringList(x.evidence)))) &&
    (v.fallbackCount === undefined || count(v.fallbackCount)) &&
    (v.usage === undefined || (object(v.usage) && ["modelCalls", "inputTokens", "outputTokens", "latencyMs"].every((key) => count(v.usage && (v.usage as RecordValue)[key])))) &&
    Array.isArray(v.reactions) &&
    new Set(v.reactions.map((r) => r.persona.id)).size === v.reactions.length
  );
}
// Validate the entire persisted shape before rendering; stale or truncated data
// must not crash a deeply nested report, form, or comparison screen.
export function validWorkspace(v: unknown): v is DemoState {
  if (!object(v) || v.version !== 1 || !object(v.draft) || !object(v.profile))
    return false;
  return (
    identifiedList(v.products, product) &&
    identifiedList(v.posts, post) &&
    identifiedList(v.reports, validReport) &&
    strings(v.profile, ["name", "email"]) &&
    typeof v.signedIn === "boolean" &&
    typeof v.draft.productId === "string" &&
    post(v.draft.post) &&
    audience(v.draft.audience) &&
    identifiedList(v.draft.personas, persona) &&
    (v.draft.availablePersonas === undefined || identifiedList(v.draft.availablePersonas, persona)) &&
    (v.draft.personaAdaptation === undefined || (object(v.draft.personaAdaptation) && strings(v.draft.personaAdaptation, ["requestId", "signature", "mode"]) && ["context", "ai"].includes(String(v.draft.personaAdaptation.mode)) && typeof v.draft.personaAdaptation.fresh === "boolean" && (v.draft.personaAdaptation.jobId === undefined || typeof v.draft.personaAdaptation.jobId === "string"))) &&
    language(v.draft.language) &&
    typeof v.draft.failOne === "boolean" &&
    [0, 1, 2].includes(Number(v.draft.step)) &&
    typeof v.draft.step === "number"
  );
}
