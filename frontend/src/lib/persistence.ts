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
    v.price > 0 &&
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
    ])
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
    strings(v, ["comment", "reason", "positive", "question"])
  );
}
function report(v: unknown): boolean {
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
    identifiedList(v.reports, report) &&
    strings(v.profile, ["name", "email"]) &&
    typeof v.signedIn === "boolean" &&
    typeof v.draft.productId === "string" &&
    post(v.draft.post) &&
    audience(v.draft.audience) &&
    identifiedList(v.draft.personas, persona) &&
    language(v.draft.language) &&
    typeof v.draft.failOne === "boolean" &&
    [0, 1, 2].includes(Number(v.draft.step)) &&
    typeof v.draft.step === "number"
  );
}
