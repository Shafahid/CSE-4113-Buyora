import { test } from "node:test";
import assert from "node:assert/strict";
import { createTypeScriptLoader } from "./load-typescript.mjs";

const load = createTypeScriptLoader();
const { initialState, recommendations } = await load("../src/lib/demo-data.ts");
const { validReport, validWorkspace } = await load("../src/lib/persistence.ts");
const { applyAdaptedPersonas, personaInputSignature } = await load("../src/lib/persona-adaptation.ts");

test("a delayed persona job preserves newer edits and unchecked custom profiles", () => {
  const draft = structuredClone(initialState.draft);
  const product = initialState.products.find((p) => p.id === draft.productId);
  const unchecked = { ...draft.personas[0], id: "custom-unchecked", need: "An untouched custom need" };
  draft.availablePersonas = [...draft.personas, unchecked];
  draft.personaAdaptation = { requestId: "request", signature: "pending", mode: "ai", fresh: false };
  const signature = personaInputSignature(draft, product);
  const profiles = draft.personas.map((p) => ({ ...p, need: p.need + " adapted", context: "Saved product context" }));
  const adapted = applyAdaptedPersonas(draft, profiles, signature, product);
  assert.deepEqual(adapted.personas, profiles);
  assert.deepEqual(adapted.availablePersonas.at(-1), unchecked);
  assert.equal(adapted.personaAdaptation, undefined);
  const newer = { ...draft, post: { ...draft.post, body: "A newly edited caption" } };
  assert.equal(applyAdaptedPersonas(newer, profiles, signature, product), newer);
  const newlySaved = { ...draft, post: { ...draft.post, latestVersionId: "new-version" } };
  assert.equal(personaInputSignature(newlySaved, product), signature);
  assert.equal(personaInputSignature(draft, { ...product, image: "a-refreshed-signed-url" }), signature);
  assert.throws(() => applyAdaptedPersonas(draft, [profiles[0], profiles[0]], signature, product), /selected personas/);
});

test("server recommendations take precedence and new report fields are validated", () => {
  const report = structuredClone(initialState.reports[0]);
  report.recommendations = [{ id: "delivery_cost", title: "Confirm charges", detail: "Two buyers asked", priority: "High priority", addition: "[Confirm delivery charges]", frequency: 2, evidence: [report.product.name], persona_ids: [report.reactions[0].persona.id] }];
  const reaction = report.reactions[0];
  reaction.evaluationSource = "fallback";
  reaction.fallbackReason = "provider_unavailable";
  reaction.objections = ["Delivery charge?"];
  reaction.scoreDrivers = [{ dimension: "Trust", reason: "Return policy needs confirmation", evidence: [report.product.name] }];
  report.fallbackCount = 1;
  assert.ok(validReport(report));
  assert.equal(recommendations(report), report.recommendations);
  const bad = structuredClone(report);
  bad.reactions[0].scoreDrivers[0].evidence = null;
  assert.equal(validReport(bad), false);
  const badRecs = structuredClone(report);
  badRecs.recommendations[0].frequency = -1;
  assert.equal(validReport(badRecs), false);
  report.recommendations = [];
  assert.deepEqual(recommendations(report), []);
});

test("account-local drafts reject corrupt adaptation jobs and descriptions", () => {
  const workspace = structuredClone(initialState);
  workspace.draft.personaAdaptation = { requestId: "request", signature: "inputs", mode: "ai", fresh: false, jobId: "job" };
  assert.ok(validWorkspace(workspace));
  workspace.draft.personaAdaptation.jobId = 12;
  assert.equal(validWorkspace(workspace), false);
  delete workspace.draft.personaAdaptation;
  workspace.draft.personas[0].context = {};
  assert.equal(validWorkspace(workspace), false);
});
