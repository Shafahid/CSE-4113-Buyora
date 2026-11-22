import { test } from "node:test";
import assert from "node:assert/strict";
import { createTypeScriptLoader } from "./load-typescript.mjs";

const load = createTypeScriptLoader();
const { reportInsights, progressCounts } = await load("../src/lib/report-insights.ts");
const { initialState } = await load("../src/lib/demo-data.ts");

test("no completed perspectives means unavailable scores, not zero buyer interest", () => {
  const report = structuredClone(initialState.reports[0]);
  report.reactions.forEach((reaction) => { reaction.status = "failed"; });
  const result = reportInsights(report);
  assert.equal(result.score, null);
  assert.equal(result.weakest, null);
  assert.equal(result.concern, null);
  assert.equal(result.completed, 0);
});

test("partial summaries exclude failures and cite a completed buyer's actual question", () => {
  const report = structuredClone(initialState.reports[0]);
  report.reactions.forEach((reaction, index) => { reaction.status = index ? "failed" : "complete"; });
  report.reactions[0].scores = [80, 80, 80, 80, 10, 80, 80];
  report.reactions[0].score = 70;
  const result = reportInsights(report);
  assert.equal(result.score, 70);
  assert.equal(result.weakest.label, "Trust");
  assert.equal(result.concern.question, report.reactions[0].question);
  assert.match(result.explanation, /Missing perspectives could change/);
});

test("processing can reach 100 percent while usable coverage is only 25 percent", () => {
  assert.deepEqual(progressCounts({ total: 8, completed: 2, failed: 6 }), {
    processed: 8, processingPercent: 100, coveragePercent: 25,
  });
  assert.equal(progressCounts({ total: 0, completed: 0, failed: 0 }).processingPercent, 0);
});
