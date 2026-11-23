import { test, afterEach } from "node:test";
import assert from "node:assert/strict";
import { createTypeScriptLoader } from "./load-typescript.mjs";

const { simulationApi } = await createTypeScriptLoader()(
  "../src/lib/simulation-api.ts",
);
const originalFetch = globalThis.fetch;
afterEach(() => {
  globalThis.fetch = originalFetch;
});

test("report APIs encode filters, comparison IDs and owned deletion", async () => {
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url: new URL(url), options });
    if (options.method === "DELETE") return new Response(null, { status: 204 });
    if (url.endsWith("/reports/compare")) {
      return Response.json({ reports: [], dimensions: [], persona_count_difference: 0, overall_score_difference: 0 });
    }
    if (url.includes("/reports?")) {
      return Response.json({ items: [], total: 0, offset: 0, limit: 20 });
    }
    return Response.json({ id: "first", report: {} });
  };

  await simulationApi.reports({
    q: "canvas bag",
    mode: "standard",
    status: "completed",
    order: "oldest",
    limit: 20,
  });
  await simulationApi.report("first");
  await simulationApi.compareReports("first", "second");
  await simulationApi.removeReport("second");

  assert.equal(calls[0].url.pathname, "/reports");
  assert.equal(calls[0].url.searchParams.get("q"), "canvas bag");
  assert.equal(calls[0].url.searchParams.get("mode"), "standard");
  assert.equal(calls[0].url.searchParams.get("status"), "completed");
  assert.equal(calls[0].url.searchParams.get("order"), "oldest");
  assert.equal(calls[0].url.searchParams.get("limit"), "20");
  assert.equal(calls[1].url.pathname, "/reports/first");
  assert.deepEqual(JSON.parse(calls[2].options.body), {
    report_ids: ["first", "second"],
  });
  assert.equal(calls[3].options.method, "DELETE");
  assert.equal(calls[3].url.pathname, "/reports/second");
  assert.ok(calls.every((call) => call.options.credentials === "include"));
});
