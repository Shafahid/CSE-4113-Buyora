import type { Reaction } from "./demo-data";

export const ROUND_LENGTH = 12;
export const TOTAL_ROUNDS = 3;
export const FINAL_TICK = ROUND_LENGTH * TOTAL_ROUNDS;
export const reactionStates = [
  "ignored",
  "engaged",
  "objection",
  "drop-off",
  "inboxed",
] as const;
export type Outcome = (typeof reactionStates)[number];
export type ViewerState = Outcome | "unreached" | "viewing";
export type Viewer = {
  id: string;
  reaction: Reaction;
  round: number;
  reachedAt: number;
  resolvedAt: number;
  outcome: Outcome;
  parent: string | null;
  x: number;
  y: number;
};
export type Spread = { viewers: Viewer[]; ticks: number };
export const stateLabels: Record<ViewerState, string> = {
  unreached: "Not reached",
  viewing: "Viewing",
  ignored: "Ignored",
  engaged: "Engaged",
  objection: "Objection",
  "drop-off": "Drop-off",
  inboxed: "Inboxed",
};
export const likelyActions: Record<ViewerState, string> = {
  unreached: "Has not seen the post yet",
  viewing: "Reading the post and considering the offer",
  ignored: "Continues scrolling without interacting",
  engaged: "Reacts to the post or passes it along in this demo",
  objection: "Asks a question before taking the next step",
  "drop-off": "Leaves without messaging the seller",
  inboxed: "Opens a conversation with the seller",
};

function randomFor(seed: string) {
  let value = 2166136261;
  for (const char of seed)
    value = Math.imul(value ^ char.charCodeAt(0), 16777619);
  return () => {
    value += 0x6d2b79f5;
    let t = Math.imul(value ^ (value >>> 15), value | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

// A reproducible local animation model, not predicted reach or buyer behavior.
// Fictional viewers reuse the completed report's persona perspectives. Later
// rounds originate only from viewers whose sample outcome allows propagation.
export function createSpread(reactions: Reaction[]): Spread {
  const completed = reactions.filter((r) => r.status === "complete");
  if (!completed.length) return { viewers: [], ticks: FINAL_TICK };
  const random = randomFor(
    completed.map((r) => `${r.persona.id}:${r.scores.join(",")}`).join("|"),
  );
  const viewers: Viewer[] = [];
  for (let index = 0; index < 60; index++) {
    const reaction = completed[index % completed.length];
    const round = index < 12 ? 1 : index < 32 ? 2 : 3;
    const parents = viewers.filter(
      (v) =>
        v.round === round - 1 &&
        (v.outcome === "engaged" || v.outcome === "inboxed"),
    );
    const parent =
      round === 1 ? null : parents[Math.floor(random() * parents.length)];
    const draw = random() * 100;
    const ignored = Math.max(8, 25 - reaction.scores[0] * 0.13);
    const objection = Math.max(12, 45 - reaction.scores[4] * 0.35);
    const dropOff = Math.max(8, 19 - reaction.scores[5] * 0.08);
    const inboxed = Math.max(10, reaction.scores[6] * 0.3);
    let outcome: Outcome =
      draw < ignored
        ? "ignored"
        : draw < ignored + objection
          ? "objection"
          : draw < ignored + objection + dropOff
            ? "drop-off"
            : draw < ignored + objection + dropOff + inboxed
              ? "inboxed"
              : "engaged";
    // Keep one demonstrative propagation path open in each seeding round.
    if (index === 0 || index === 12) outcome = "engaged";
    const reachedAt = (round - 1) * ROUND_LENGTH + 1 + Math.floor(random() * 6);
    const angle = index * 2.399963;
    const radius = 75 + Math.sqrt(index / 60) * 170;
    viewers.push({
      id: `v-${String(index + 1).padStart(2, "0")}`,
      reaction,
      round,
      reachedAt,
      resolvedAt: reachedAt + 3,
      outcome,
      parent: parent?.id || null,
      x: 360 + Math.cos(angle) * radius * 1.15 + (random() - 0.5) * 25,
      y: 225 + Math.sin(angle) * radius * 0.7 + (random() - 0.5) * 25,
    });
  }
  // Relax the seeded positions into a readable network without a graph library.
  for (let step = 0; step < 100; step++) {
    const forces = viewers.map(() => ({ x: 0, y: 0 }));
    for (let i = 0; i < viewers.length; i++) {
      for (let j = i + 1; j < viewers.length; j++) {
        const dx = viewers[i].x - viewers[j].x;
        const dy = viewers[i].y - viewers[j].y;
        const distance = Math.max(1, Math.hypot(dx, dy));
        const force = Math.min(4, 1500 / (distance * distance));
        forces[i].x += (dx / distance) * force;
        forces[i].y += (dy / distance) * force;
        forces[j].x -= (dx / distance) * force;
        forces[j].y -= (dy / distance) * force;
      }
      const node = viewers[i];
      const parent = viewers.find((v) => v.id === node.parent);
      const dx = (parent?.x ?? 360) - node.x;
      const dy = (parent?.y ?? 225) - node.y;
      const distance = Math.max(1, Math.hypot(dx, dy));
      const spring = (distance - 95) * 0.009;
      forces[i].x += (dx / distance) * spring;
      forces[i].y += (dy / distance) * spring;
      // Keep a little breathing room around the product post.
      const centerDistance = Math.max(
        1,
        Math.hypot(node.x - 360, node.y - 225),
      );
      if (centerDistance < 58) {
        forces[i].x += ((node.x - 360) / centerDistance) * 3;
        forces[i].y += ((node.y - 225) / centerDistance) * 3;
      }
    }
    viewers.forEach((v, i) => {
      v.x = Math.max(45, Math.min(675, v.x + forces[i].x));
      v.y = Math.max(40, Math.min(410, v.y + forces[i].y));
    });
  }
  viewers.forEach((v) => {
    v.x = Math.round(v.x * 100) / 100;
    v.y = Math.round(v.y * 100) / 100;
  });
  return { viewers, ticks: FINAL_TICK };
}

export function viewerState(viewer: Viewer, tick: number): ViewerState {
  if (tick < viewer.reachedAt) return "unreached";
  if (tick < viewer.reachedAt + 1) return "viewing";
  if (tick < viewer.resolvedAt) {
    if (viewer.outcome === "inboxed") return "engaged";
    if (viewer.outcome === "drop-off") return "objection";
    return "viewing";
  }
  return viewer.outcome;
}
export function spreadSummary(spread: Spread, tick: number) {
  const counts: Record<ViewerState, number> = {
    unreached: 0,
    viewing: 0,
    ignored: 0,
    engaged: 0,
    objection: 0,
    "drop-off": 0,
    inboxed: 0,
  };
  spread.viewers.forEach((v) => counts[viewerState(v, tick)]++);
  return {
    counts,
    reached: spread.viewers.length - counts.unreached,
    round: Math.min(TOTAL_ROUNDS, Math.max(1, Math.ceil(tick / ROUND_LENGTH))),
    complete: tick >= spread.ticks,
  };
}
