import { test } from "node:test";
import assert from "node:assert/strict";
import { createTypeScriptLoader } from "./load-typescript.mjs";

const load = createTypeScriptLoader();
const { personaChoices, setPersonaSelected } = await load("../src/lib/persona-selection.ts");
const { initialDraft, initialState, personas, products } = await load("../src/lib/demo-data.ts");
const { validWorkspace } = await load("../src/lib/persistence.ts");
const { simulationError } = await load("../src/lib/workflow.ts");
const { createWorkspaceState } = await load("../src/lib/workspace-state.ts");

test("the picker includes every catalog persona while the draft contains only checked profiles", () => {
  let draft = structuredClone(initialDraft);
  assert.equal(personaChoices(draft, personas).length, personas.length);
  assert.equal(draft.personas.length, 6);
  draft = setPersonaSelected(draft, personas[1], false, 12);
  draft = setPersonaSelected(draft, personas[7], true, 12);
  draft = setPersonaSelected(draft, personas[7], true, 12);
  assert.equal(draft.personas.length, 6);
  assert.equal(draft.personas.some((p) => p.id === personas[1].id), false);
  assert.equal(draft.personas.filter((p) => p.id === personas[7].id).length, 1);
  assert.equal(personaChoices(draft, personas).length, personas.length);
});

test("deselecting an edited custom persona preserves it across account-local draft reloads", () => {
  const custom = { ...personas[0], id: "custom", name: "Custom buyer", need: "Verified materials and repair options" };
  let draft = setPersonaSelected(structuredClone(initialDraft), custom, true, 12);
  draft = setPersonaSelected(draft, custom, false, 12);
  const records = new Map();
  const storage = () => ({ getItem: (key) => records.get(key) ?? null, setItem: (key, value) => records.set(key, value) });
  const user = { id: 1, email: "seller@example.com", display_name: "Seller" };
  const store = createWorkspaceState(storage);
  store.activate(user);
  store.updateLocal((state) => ({ ...state, draft }));
  const restored = createWorkspaceState(storage);
  restored.activate(user);
  const reloaded = restored.getSnapshot().data.draft;
  assert.equal(reloaded.personas.some((p) => p.id === custom.id), false);
  const saved = personaChoices(reloaded, personas).find((p) => p.id === custom.id);
  assert.deepEqual(saved, custom);
  assert.deepEqual(setPersonaSelected(reloaded, saved, true, 12).personas.at(-1), custom);
});

test("the configured limit applies to checked profiles and a user can replace one at the limit", () => {
  let draft = structuredClone(initialDraft);
  assert.throws(() => setPersonaSelected(draft, personas[7], true, 6), /up to 6/);
  draft = setPersonaSelected(draft, personas[0], false, 6);
  draft = setPersonaSelected(draft, personas[7], true, 6);
  assert.equal(draft.personas.length, 6);
  assert.equal(simulationError(draft, products[0], 6), "");
  draft = { ...draft, availablePersonas: personaChoices(draft, personas), personas: [] };
  assert.match(simulationError(draft, products[0], 6), /Choose between 2 and 6/);
});

test("old drafts load without a persona pool and corrupt saved pools are rejected", () => {
  assert.equal(validWorkspace(initialState), true);
  const state = structuredClone(initialState);
  state.draft.availablePersonas = [{ ...personas[0], need: null }];
  assert.equal(validWorkspace(state), false);
  state.draft.availablePersonas = [personas[0], personas[0]];
  assert.equal(validWorkspace(state), false);
});
