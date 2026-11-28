"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { refreshSimulationProgress, useWorkspace } from "@/lib/store";
import { ApiError, errorMessage } from "@/lib/api-client";
import { progressCounts } from "@/lib/report-insights";
import { finishedRun } from "@/lib/simulation-api";
import { Avatar, Badge, Notice } from "./ui";
import styles from "./simulation-progress.module.css";

export const evaluationErrors: Record<string, string> = {
  retry_limit: "This perspective reached its retry limit. Start a fresh simulation if you want another assessment.",
  provider_auth: "The evaluation service needs attention. Contact your workspace owner before trying again.",
  provider_configuration: "The evaluation service needs attention. Contact your workspace owner before trying again.",
  configuration_changed: "The evaluation service changed. Start a fresh simulation to use the updated service.",
  rate_limited: "The model's request limit was reached. You can retry this perspective.",
  provider_unavailable: "The model could not respond. Your other results are saved.",
  invalid_output: "The model returned an incomplete assessment. You can retry it.",
  output_truncated: "The assessment stopped before it was complete. Your workspace owner needs to adjust the evaluation service before you try again.",
  interrupted: "Processing was interrupted. Retry this perspective to continue.",
  model_call_budget: "This run reached its model-call safeguard. Completed perspectives are saved.",
  token_budget: "This run reached its token safeguard. Completed perspectives are saved.",
};

const stageLabels: Record<string, string> = {
  queued: "Queued for a worker",
  evaluating: "Evaluating buyer perspectives",
  report_ready: "Report ready",
  report_ready_partial: "Partial report ready",
  failed: "Processing finished without usable results",
};

export function SimulationProgress({ id, onBack }: { id: string; onBack?: () => void }) {
  const { runs } = useWorkspace();
  const run = runs.find((item) => item.id === id);
  const [error, setError] = useState("");
  const [clock, setClock] = useState(() => Date.now());
  const [pollKey, setPollKey] = useState(0);
  const [stopped, setStopped] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<number | null>(null);
  const router = useRouter();
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    async function poll() {
      try {
        const latest = await refreshSimulationProgress(id, controller.signal);
        if (controller.signal.aborted) return;
        setError("");
        setLastUpdated(Date.now());
        setStopped(false);
        if (finishedRun(latest)) {
          router.replace(`/reports/${id}`);
          return;
        }
      } catch (error) {
        if (controller.signal.aborted) return;
        setError(errorMessage(error));
        if (error instanceof ApiError && [401, 403, 404].includes(error.status ?? 0)) {
          setStopped(true);
          return;
        }
      }
      timer = setTimeout(poll, 1500);
    }
    void poll();
    const elapsed = setInterval(() => setClock(Date.now()), 1000);
    return () => { controller.abort(); clearTimeout(timer); clearInterval(elapsed); };
  }, [id, router, pollKey]);
  const total = run?.total ?? 0;
  const completed = run?.completed ?? 0;
  const failed = run?.failed ?? 0;
  const { processingPercent: progress, coveragePercent } = progressCounts({ total, completed, failed });
  const elapsed = run ? Math.max(0, Math.floor((clock - Date.parse(run.started_at ?? run.updated_at)) / 1000)) : 0;
  const processing = run?.evaluations.filter((item) => item.status === "running").length ?? 0;
  const summary = !run ? "Loading your saved simulation…" : run.status === "queued"
    ? "Your simulation is queued. Your buyers will start evaluating shortly."
    : `${completed} of ${total} perspectives completed${failed ? `, ${failed} need a retry` : ""}. ${processing} evaluating now.`;
  return (
    <section className={`panel ${styles.progress}`} aria-labelledby="processing-title">
      <div className={styles.heading}>
        <div>
          <h1 id="processing-title">Your buyers are taking a look.</h1>
          <p role="status" aria-live="polite">{summary}</p>
        </div>
        <span className={styles.elapsed} aria-live="off">{Math.floor(elapsed / 60)}m {elapsed % 60}s elapsed</span>
      </div>
      <div className={styles.meter} role="progressbar" aria-label="Processing progress, including unsuccessful evaluations"
        aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}>
        <span style={{ width: `${progress}%` }} />
      </div>
      <div className={styles.caption}><span>Processing progress</span><strong>{progress}% processed</strong></div>
      {run && <div className={styles.caption}><span>Job stage</span><strong>{stageLabels[run.stage] ?? run.stage} · {run.expected_personas} expected</strong></div>}
      <div className={styles.caption}><span>{completed} of {total} usable perspectives · {failed} need attention</span><strong>{coveragePercent}% coverage</strong></div>
      <p className={styles.update} aria-live="off">{lastUpdated ? `Last checked ${Math.max(0, Math.floor((clock - lastUpdated) / 1000))}s ago` : "Connecting to your saved run…"}</p>
      {error && <Notice tone="warning">Progress updates paused: {error} {stopped ? "Automatic updates stopped. Your saved results are kept." : "Reconnecting automatically; your saved results are kept."} <button className="text-link" onClick={() => setPollKey((key) => key + 1)}>Check again</button></Notice>}
      {run?.status === "queued" && elapsed > 15 && <Notice tone="warning">This is taking longer than usual. You can leave this page and resume from Simulation history. If the wait continues, contact your workspace owner.</Notice>}
      <div className={styles.people}>
        {run?.evaluations.map((item) => (
          <article className={styles.person} key={item.id}>
            <Avatar persona={item.profile} />
            <div className={styles.identity}>
              <div className={styles.name}><h2>{item.profile.name}</h2><Badge tone={item.status === "completed" ? "green" : item.status === "failed" ? "amber" : "blue"}>
                {item.output?.evaluation_source === "fallback" ? "Rule-based fallback" : item.status === "running" ? "Evaluating" : item.status === "completed" ? "Completed" : item.status === "failed" ? "Needs retry" : "Queued"}
              </Badge></div>
              <p>{item.profile.role} · {item.profile.need}</p>
              {item.status === "running" && <p className={styles.activity}><span className={styles.dot} />Reading your post and weighing this buyer’s concerns{item.attempts > 1 ? ` · attempt ${item.attempts}` : ""}…</p>}
              {item.output && <blockquote>“{item.output.comment}”</blockquote>}
              {item.status === "failed" && <p>{evaluationErrors[item.error_code ?? ""] ?? "This evaluation could not finish. Retry it from the report."}</p>}
            </div>
          </article>
        ))}
      </div>
      <div className={styles.footer}>
        <p>Each completed perspective is saved to your account. You can leave this page while processing continues. These are fictional buyer reactions, not actual customer feedback.</p>
        <div className="row">
          {onBack && <button className="button secondary" onClick={onBack}>Back to setup</button>}
          <Link className="button secondary" href="/history">View simulation history</Link>
        </div>
      </div>
    </section>
  );
}
