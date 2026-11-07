import { test } from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import ts from "typescript";

// Use the project's installed compiler, with no runner or test dependencies.
async function loadTypeScript(path) {
  const source = await readFile(new URL(path, import.meta.url), "utf8");
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ESNext,
      target: ts.ScriptTarget.ES2022,
    },
  });
  return import(
    `data:text/javascript;base64,${Buffer.from(outputText).toString("base64")}`
  );
}
const data = await loadTypeScript("../src/lib/demo-data.ts");
const { validWorkspace } = await loadTypeScript("../src/lib/persistence.ts");
const spreadModel = await loadTypeScript("../src/lib/spread-simulation.ts");
const { createPersistentStore } = await loadTypeScript(
  "../src/lib/persistent-store.ts",
);
const { postError, simulationError, comparisonSelection } =
  await loadTypeScript("../src/lib/workflow.ts");
const { advancePlayback, playbackDelay } = await loadTypeScript(
  "../src/lib/spread-playback.ts",
);

test("storage error-only changes are observable and session data survives quota failures", () => {
  let raw = null;
  let writesFail = false;
  const adapter = {
    getItem: () => raw,
    setItem: (_key, value) => {
      if (writesFail) throw new Error("quota");
      raw = value;
    },
  };
  const store = createPersistentStore(
    data.initialState,
    validWorkspace,
    () => adapter,
    "test",
  );
  const before = store.getSnapshot();
  assert.equal(before.error, "");
  let notifications = 0;
  const unsubscribe = store.subscribe(() => notifications++);
  writesFail = true;
  store.update((current) => current);
  const errorOnly = store.getSnapshot();
  assert.notEqual(errorOnly, before);
  assert.equal(errorOnly.data, before.data);
  assert.match(errorOnly.error, /full or unavailable/);
  assert.equal(notifications, 1);
  store.update((current) => ({
    ...current,
    profile: { ...current.profile, name: "Kept in memory" },
  }));
  assert.equal(store.getSnapshot().data.profile.name, "Kept in memory");
  writesFail = false;
  store.update((current) => current);
  assert.equal(store.getSnapshot().error, "");
  assert.equal(JSON.parse(raw).profile.name, "Kept in memory");
  assert.equal(
    store.getSnapshot(),
    store.getSnapshot(),
    "Snapshots must be cached for React",
  );
  unsubscribe();
});

test("storage recovers from malformed JSON and clear events without stale warnings", () => {
  let raw = "{broken";
  const adapter = {
    getItem: () => raw,
    setItem: (_key, value) => {
      raw = value;
    },
  };
  const store = createPersistentStore(
    data.initialState,
    validWorkspace,
    () => adapter,
    "test",
  );
  assert.match(store.getSnapshot().error, /could not be read/);
  const saved = structuredClone(data.initialState);
  saved.profile.name = "From another tab";
  raw = JSON.stringify(saved);
  store.reload();
  assert.equal(store.getSnapshot().data.profile.name, "From another tab");
  assert.equal(store.getSnapshot().error, "");
  raw = null;
  store.reload();
  assert.equal(store.getSnapshot().data, data.initialState);
  assert.equal(store.getSnapshot().error, "");
});

test("server snapshots never access browser storage and denied storage stays usable", () => {
  let reads = 0;
  const store = createPersistentStore(
    data.initialState,
    validWorkspace,
    () => {
      reads++;
      throw new Error("denied");
    },
    "test",
  );
  assert.equal(store.getServerSnapshot().data, data.initialState);
  assert.equal(reads, 0);
  assert.match(store.getSnapshot().error, /unavailable/);
  store.update((current) => ({ ...current, signedIn: true }));
  assert.equal(store.getSnapshot().data.signedIn, true);
});

test("a restored final-step draft still validates its post, active product, and personas", () => {
  const valid = structuredClone(data.initialDraft);
  valid.step = 2;
  assert.equal(simulationError(valid, data.products[0]), "");
  assert.match(
    simulationError(
      { ...valid, post: { ...valid.post, headline: "  " } },
      data.products[0],
    ),
    /headline/,
  );
  assert.match(
    simulationError(
      { ...valid, post: { ...valid.post, body: "  short  " } },
      data.products[0],
    ),
    /20/,
  );
  assert.match(
    simulationError(valid, { ...data.products[0], archived: true }),
    /active product/,
  );
  assert.match(simulationError(valid, undefined), /active product/);
  assert.match(
    postError(
      { ...valid, post: { ...valid.post, productId: "other" } },
      data.products[0],
    ),
    /different product/,
  );
  const blankPersona = structuredClone(valid);
  blankPersona.personas[0].name = "   ";
  assert.match(simulationError(blankPersona, data.products[0]), /Complete/);
  assert.match(
    simulationError(
      { ...valid, personas: [valid.personas[0], valid.personas[0]] },
      data.products[0],
    ),
    /identity/,
  );
});

test("comparison recovers deleted selections and excludes incomplete reports", () => {
  const reports = structuredClone(data.initialState.reports);
  reports[2].reactions[0].status = "failed";
  const selection = comparisonSelection(
    reports,
    "deleted-report",
    reports[0].id,
  );
  assert.equal(selection.reports.length, 2);
  assert.equal(selection.left.id, reports[1].id);
  assert.equal(selection.right.id, reports[0].id);
  const empty = comparisonSelection([], "deleted", "also-deleted");
  assert.equal(empty.left, undefined);
  assert.equal(empty.right, undefined);
});

test("landing playback loops after exactly a two-second hold while report playback stops", () => {
  const finalTick = spreadModel.FINAL_TICK;
  let animation = { tick: 0, playing: true, speed: 1 };
  for (let i = 0; i < finalTick; i++)
    animation = advancePlayback(animation, finalTick, true);
  assert.equal(animation.tick, finalTick);
  assert.equal(animation.playing, true);
  assert.equal(playbackDelay(animation, finalTick, true), 2000);
  animation = advancePlayback(animation, finalTick, true);
  assert.equal(animation.tick, 0);
  assert.equal(animation.playing, true);
  const paused = { ...animation, playing: false };
  assert.equal(advancePlayback(paused, finalTick, true), paused);
  const report = advancePlayback(
    { tick: finalTick - 1, playing: true, speed: 2 },
    finalTick,
    false,
  );
  assert.equal(report.tick, finalTick);
  assert.equal(report.playing, false);
  assert.equal(
    playbackDelay({ tick: 1, playing: true, speed: 2 }, finalTick, false),
    140,
  );
});

test("duplicate persisted identities and non-string reaction statuses are rejected", () => {
  const duplicate = structuredClone(data.initialState);
  duplicate.products.push({ ...duplicate.products[0] });
  assert.equal(validWorkspace(duplicate), false);
  const badStatus = structuredClone(data.initialState);
  badStatus.reports[0].reactions[0].status = ["complete"];
  assert.equal(validWorkspace(badStatus), false);
  const duplicateReaction = structuredClone(data.initialState);
  duplicateReaction.reports[0].reactions[1].persona.id =
    duplicateReaction.reports[0].reactions[0].persona.id;
  assert.equal(validWorkspace(duplicateReaction), false);
});

test("spread playback reaches 60 viewers in three causal rounds and finishes with consistent counts", () => {
  const spread = spreadModel.createSpread(
    data.initialState.reports[0].reactions,
  );
  assert.equal(spread.viewers.length, 60);
  assert.equal(new Set(spread.viewers.map((v) => v.id)).size, 60);
  assert.deepEqual([...new Set(spread.viewers.map((v) => v.round))], [1, 2, 3]);
  let previousReach = 0;
  for (let tick = 0; tick <= spread.ticks; tick++) {
    const summary = spreadModel.spreadSummary(spread, tick);
    assert.equal(
      Object.values(summary.counts).reduce((a, b) => a + b, 0),
      60,
    );
    assert.ok(summary.reached >= previousReach);
    assert.equal(summary.complete, tick === spread.ticks);
    previousReach = summary.reached;
  }
  const start = spreadModel.spreadSummary(spread, 0);
  const end = spreadModel.spreadSummary(spread, spread.ticks);
  assert.equal(start.reached, 0);
  assert.equal(end.reached, 60);
  assert.equal(end.counts.unreached + end.counts.viewing, 0);
  assert.equal(
    spreadModel.reactionStates.reduce(
      (sum, state) => sum + end.counts[state],
      0,
    ),
    60,
  );
  for (const viewer of spread.viewers) {
    assert.ok(Number.isFinite(viewer.x) && viewer.x >= 45 && viewer.x <= 675);
    assert.ok(Number.isFinite(viewer.y) && viewer.y >= 40 && viewer.y <= 410);
    assert.equal(
      spreadModel.viewerState(viewer, viewer.reachedAt - 1),
      "unreached",
    );
    assert.equal(spreadModel.viewerState(viewer, viewer.reachedAt), "viewing");
    assert.equal(
      spreadModel.viewerState(viewer, viewer.resolvedAt),
      viewer.outcome,
    );
    if (viewer.round > 1) {
      const parent = spread.viewers.find((v) => v.id === viewer.parent);
      assert.ok(parent, "Later-round viewers need a propagation source");
      assert.equal(parent.round, viewer.round - 1);
      assert.ok(parent.resolvedAt < viewer.reachedAt);
      assert.ok(["engaged", "inboxed"].includes(parent.outcome));
    } else assert.equal(viewer.parent, null);
  }
});

test("replaying and scrubbing the graph reproduces the same events without changing reports", () => {
  const reactions = structuredClone(data.initialState.reports[0].reactions);
  const before = structuredClone(reactions);
  const first = spreadModel.createSpread(reactions);
  const replay = spreadModel.createSpread(reactions);
  assert.deepEqual(first, replay);
  const midRun = spreadModel.spreadSummary(first, 17);
  spreadModel.spreadSummary(first, spreadModel.FINAL_TICK);
  assert.deepEqual(spreadModel.spreadSummary(first, 17), midRun);
  assert.deepEqual(reactions, before);
});

test("failed personas do not produce invented graph reactions and empty results stay empty", () => {
  const reactions = structuredClone(data.initialState.reports[0].reactions);
  reactions[0].status = "failed";
  const spread = spreadModel.createSpread(reactions);
  assert.equal(spread.viewers.length, 60);
  assert.ok(
    spread.viewers.every(
      (v) => v.reaction.persona.id !== reactions[0].persona.id,
    ),
  );
  assert.equal(spreadModel.createSpread([]).viewers.length, 0);
  assert.equal(
    spreadModel.createSpread(reactions.map((r) => ({ ...r, status: "failed" })))
      .viewers.length,
    0,
  );
});

test("all stored sample results use seven finite scores on the same scale", () => {
  assert.equal(validWorkspace(data.initialState), true);
  for (const report of data.initialState.reports) {
    for (const reaction of report.reactions) {
      assert.equal(reaction.scores.length, data.dimensions.length);
      assert.ok(
        reaction.scores.every((n) => Number.isFinite(n) && n >= 0 && n <= 100),
      );
      assert.equal(
        reaction.score,
        Math.round(reaction.scores.reduce((a, b) => a + b, 0) / 7),
      );
    }
  }
});

test("a saved report keeps its original inputs when the draft is edited later", () => {
  const draft = structuredClone(data.initialDraft);
  const product = structuredClone(data.products[0]);
  const report = data.makeReport(
    draft,
    product,
    "snapshot-test",
    "2026-11-07T06:00:00Z",
  );
  const originalCaption = report.post.body;
  const originalName = report.reactions[0].persona.name;
  draft.post.body = "Changed after the simulation";
  draft.personas[0].name = "A different name";
  draft.audience.location = "A different city";
  product.name = "A renamed product";
  assert.equal(report.post.body, originalCaption);
  assert.equal(report.reactions[0].persona.name, originalName);
  assert.equal(report.audience.location, "Dhaka, Bangladesh");
  assert.equal(report.product.name, "Nila everyday tote");
});

test("failed evaluations are excluded from averages and can be retried independently", () => {
  const report = data.makeReport(
    { ...data.initialDraft, failOne: true },
    data.products[0],
    "retry-test",
    "2026-11-07T06:00:00Z",
  );
  const previous = structuredClone(report.reactions.slice(0, -1));
  const failedIndex = report.reactions.findIndex((r) => r.status === "failed");
  assert.equal(failedIndex, report.reactions.length - 1);
  const completedAverage = Math.round(
    previous.reduce((sum, r) => sum + r.score, 0) / previous.length,
  );
  assert.equal(data.overall(report), completedAverage);
  const failed = report.reactions[failedIndex];
  report.reactions[failedIndex] = data.evaluate(
    failed.persona,
    report.product,
    report.post,
    report.language,
    failedIndex,
  );
  assert.ok(report.reactions.every((r) => r.status === "complete"));
  assert.deepEqual(report.reactions.slice(0, -1), previous);
  assert.equal(data.overall({ ...report, reactions: [] }), 0);
});

test("testing successive revisions preserves every earlier caption without duplicate no-op versions", () => {
  const original = structuredClone(data.posts[0]);
  const v2 = data.savePostVersion(original, {
    ...original,
    body: "Second caption, with delivery details.",
  });
  const v3 = data.savePostVersion(v2, {
    ...original,
    body: "Third caption, with the exchange policy.",
  });
  assert.deepEqual(
    v3.versions.map((v) => v.body),
    [original.body, v2.body],
  );
  const unchanged = data.savePostVersion(v3, structuredClone(v3));
  assert.equal(unchanged.versions.length, 2);
  assert.equal(original.versions.length, 0);
});

test("recommendations use existing policies and request verification instead of inventing payment claims", () => {
  const report = data.initialState.reports[0];
  const recs = data.recommendations(report);
  assert.equal(
    recs.find((r) => r.id === "delivery").addition,
    report.product.delivery,
  );
  assert.equal(
    recs.find((r) => r.id === "returns").addition,
    report.product.returns,
  );
  assert.match(
    recs.find((r) => r.id === "payment").addition,
    /\[.*verified.*\]/,
  );
  assert.match(recs.find((r) => r.id === "proof").addition, /\[/);
});

test("Bangla selection produces Bangla buyer comments", () => {
  const report = data.makeReport(
    { ...data.initialDraft, language: "bn" },
    data.products[0],
    "bangla-test",
    "2026-11-07T06:00:00Z",
  );
  assert.ok(report.reactions.every((r) => /[\u0980-\u09ff]/u.test(r.comment)));
});

test("invalid or stale persisted data cannot reach nested report or wizard components", () => {
  for (const change of [
    (s) => {
      s.version = 2;
    },
    (s) => {
      s.draft.step = 99;
    },
    (s) => {
      s.reports[0].reactions[0].scores = [75];
    },
    (s) => {
      s.reports[0].reactions[0].scores[0] = NaN;
    },
    (s) => {
      delete s.posts[0].versions;
    },
    (s) => {
      s.products[0].price = -1;
    },
    (s) => {
      s.reports[0].createdAt = "not a date";
    },
    (s) => {
      s.draft.personas = [null];
    },
  ]) {
    const malformed = structuredClone(data.initialState);
    change(malformed);
    assert.equal(validWorkspace(malformed), false);
  }
  for (const malformed of [null, [], {}, "broken"])
    assert.equal(validWorkspace(malformed), false);
  assert.equal(
    validWorkspace(JSON.parse(JSON.stringify(data.initialState))),
    true,
  );
});
