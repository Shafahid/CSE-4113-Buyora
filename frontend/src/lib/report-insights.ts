import { dimensions, overall, type Report } from "./demo-data";

// Derive the overview from completed, saved assessments. Reopening a report
// never requests another model verdict, and older reports use the same rules.
export function reportInsights(report: Report) {
  const complete = report.reactions.filter((reaction) => reaction.status === "complete");
  const total = report.reactions.length;
  const failed = total - complete.length;
  if (!complete.length) return {
    completed: 0, total, failed, score: null, weakest: null, concern: null,
    title: "Your assessment is not ready yet.",
    explanation: "No buyer perspective finished. Scores and recommendations about buyer response are unavailable until an evaluation completes.",
  };
  const averages = dimensions.map((_, index) => overall(report, index));
  const weakestIndex = averages.indexOf(Math.min(...averages));
  const concern = [...complete].sort((a, b) => a.scores[weakestIndex] - b.scores[weakestIndex])[0];
  return {
    completed: complete.length, total, failed, score: overall(report),
    weakest: { label: dimensions[weakestIndex], score: averages[weakestIndex] },
    concern,
    title: failed ? "A first look, with perspectives still missing."
      : overall(report, 0) >= 75 ? "Your post sparks interest." : "Your post has room to grow.",
    explanation: failed
      ? `Based on ${complete.length} of ${total} selected personas. Missing perspectives could change the conclusion.`
      : `Based on all ${total} selected personas. Review their questions before deciding what to change.`,
  };
}

export function progressCounts(run: { total: number; completed: number; failed: number }) {
  return {
    processed: run.completed + run.failed,
    processingPercent: run.total ? Math.round((run.completed + run.failed) / run.total * 100) : 0,
    coveragePercent: run.total ? Math.round(run.completed / run.total * 100) : 0,
  };
}
