import { test, afterEach } from "node:test";
import assert from "node:assert/strict";
import { createTypeScriptLoader } from "./load-typescript.mjs";

const load = createTypeScriptLoader();
const { ApiError, request } = await load("../src/lib/api-client.ts");
const adapters = await load("../src/lib/api-adapters.ts");
const { createWorkspaceState, accountStorageKey } = await load("../src/lib/workspace-state.ts");
const data = await load("../src/lib/demo-data.ts");
const originalFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = originalFetch; });

test("validation errors retain actionable field paths and HTTP status", async () => {
  globalThis.fetch = async () => Response.json({ detail: [
    { loc: ["body", "price"], msg: "Decimal input should have no more than 2 decimal places" },
    { loc: ["body", "features", 0], msg: "Input should be a valid string" },
  ] }, { status: 422 });
  await assert.rejects(request("/products"), (error) => {
    assert.ok(error instanceof ApiError);
    assert.equal(error.status, 422);
    assert.match(error.message, /price: Decimal/);
    assert.equal(error.fields["features.0"], "Input should be a valid string");
    return true;
  });
});

test("multipart requests keep the browser-generated content type and credentials", async () => {
  const body = new FormData(); body.append("file", new Blob(["image"]), "photo.png");
  globalThis.fetch = async (_url, options) => {
    assert.equal(options.body, body);
    assert.equal(options.headers.has("Content-Type"), false);
    assert.equal(options.credentials, "include");
    return Response.json({ id: 1 });
  };
  await request("/products/1/images", { method: "POST", body });
});

test("product mapping handles decimal prices, nullable policies, arrays and signed images", () => {
  const product = adapters.productFromApi({
    id: 42, seller_id: 1, name: "Bag", category: "Accessories", price: "120.50",
    features: ["Canvas", "Zipper"], description: null, warranty: null, delivery_info: "Dhaka", return_policy: null,
    status: "archived", currency: "BDT", images: [{ id: 7, sort_order: 0, url: "https://example.com/signed" }],
  });
  assert.equal(product.id, "42"); assert.equal(product.price, 120.5);
  assert.equal(product.description, ""); assert.equal(product.archived, true);
  assert.deepEqual(product.images, [{ id: "7", url: "https://example.com/signed" }]);
  assert.deepEqual(adapters.productToApi(product), {
    name: "Bag", category: "Accessories", price: "120.50", description: null,
    features: ["Canvas", "Zipper"], warranty: null, delivery_info: "Dhaka", return_policy: null,
  });
});

test("post history uses server versions and restores all saved content", () => {
  const first = { id: 10, post_id: 5, version_number: 1, created_at: "2026-11-01T00:00:00Z", headline: "First", body: "First body", offer: null, call_to_action: "Ask", hashtags: ["#bag"], platform: "Facebook" };
  const latest = { ...first, id: 12, version_number: 2, headline: "Revised", body: "Revised body" };
  const post = adapters.postFromApi({ id: 5, product_id: 42, created_at: first.created_at, latest_version: latest }, [latest, first]);
  assert.equal(post.latestVersionId, "12"); assert.equal(post.versionNumber, 2);
  assert.deepEqual(post.versions.map((v) => [v.id, v.versionNumber, v.headline]), [["10", 1, "First"]]);
  assert.equal(adapters.postToApi(post).call_to_action, "Ask");
  assert.deepEqual(adapters.postToApi(post).hashtags, ["#bag"]);
});

test("accounts never inherit each other's records, identity or local previews", () => {
  const records = new Map([["buyora-workspace-v1", JSON.stringify(data.initialState)]]);
  const store = createWorkspaceState(() => ({ getItem: (key) => records.get(key) ?? null, setItem: (key, value) => records.set(key, value) }));
  const first = { id: 1, email: "one@example.com", display_name: "One" };
  store.activate(first);
  assert.equal(store.getSnapshot().data.products.length, 0);
  assert.equal(store.getSnapshot().data.reports.length, 0);
  store.catalog([data.products[0]], []);
  store.updateLocal((s) => ({ ...s, reports: data.initialState.reports, products: data.products, profile: { name: "Fake", email: "fake@example.com" } }));
  const persisted = JSON.parse(records.get(accountStorageKey(1)));
  assert.deepEqual(Object.keys(persisted).sort(), ["draft", "reports", "version"]);
  assert.equal(store.getSnapshot().data.products.length, 1);
  assert.equal(store.getSnapshot().data.profile.name, "One");
  store.clear();
  assert.equal(store.getSnapshot().status, "unauthenticated");
  assert.equal(store.getSnapshot().data.products.length, 0);
  store.activate({ id: 2, email: "two@example.com", display_name: "Two" });
  assert.equal(store.getSnapshot().data.reports.length, 0);
  store.activate(first);
  assert.equal(store.getSnapshot().data.reports.length, data.initialState.reports.length);
  assert.equal(store.getSnapshot().data.products.length, 0);
});

test("corrupt or unavailable local storage does not replace real server data", () => {
  const store = createWorkspaceState(() => ({ getItem: () => "broken", setItem: () => { throw new Error("quota"); } }));
  store.activate({ id: 1, email: "one@example.com", display_name: "One" });
  store.catalog([data.products[0]], []);
  store.updateLocal((s) => ({ ...s, draft: { ...s.draft, step: 2 } }));
  assert.equal(store.getSnapshot().data.products[0].name, data.products[0].name);
  assert.equal(store.getSnapshot().data.draft.step, 2);
  assert.match(store.getSnapshot().error, /could not be saved/);
});

test("an old account's pending mutation cannot populate a newly signed-in workspace", async () => {
  const react = "data:text/javascript," + encodeURIComponent("export const useSyncExternalStore = (_subscribe, snapshot) => snapshot();");
  const store = await createTypeScriptLoader({ react })("../src/lib/store.ts");
  store.setSession({ id: 1, email: "one@example.com", display_name: "One" });
  let respond;
  globalThis.fetch = async () => new Promise((resolve) => { respond = resolve; });
  const pending = store.saveProduct({ ...data.products[0], id: "" });
  store.setSession({ id: 2, email: "two@example.com", display_name: "Two" });
  respond(Response.json({ id: 1, seller_id: 1, name: "Old account", category: "Accessories", price: "10.00", status: "active", currency: "BDT", features: [] }));
  await assert.rejects(pending, (error) => error.status === 401);
  assert.deepEqual(store.useDemo().products, []);
  assert.equal(store.useDemo().profile.name, "Two");
  store.clearSession();
});
