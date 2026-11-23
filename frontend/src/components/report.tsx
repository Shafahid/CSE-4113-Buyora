"use client";
import Link from "next/link";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import {
  dateLabel,
  dimensions,
  evaluate,
  overall,
  recommendations,
  Reaction,
  Report,
} from "@/lib/demo-data";
import { download, updateDemo, useWorkspace, savePost, retrySimulation, retryFailedSimulation, saveReportChanges, generateReportRevision } from "@/lib/store";
import { reportInsights } from "@/lib/report-insights";
import { finishedRun } from "@/lib/simulation-api";
import { SimulationProgress, evaluationErrors } from "./simulation-progress";
import { errorMessage } from "@/lib/api-client";
import {
  Avatar,
  Badge,
  ButtonLink,
  EmptyState,
  Icon,
  Modal,
  Notice,
  PageHeading,
  ProductArt,
  ScoreRing,
  useToast,
} from "./ui";
import { ReactionMap } from "./reaction-map";
import { PrintReport } from "./print-report";

const tabs = [
  "Overview",
  "Audience insights",
  "Spread simulation",
  "Buyer comments",
  "Improve your post",
];
export function ReportView({
  id,
  initialTab = 0,
}: {
  id: string;
  initialTab?: number;
}) {
  const { data: state, runs } = useWorkspace();
  const run = runs.find((item) => item.id === id);
  const report = state.reports.find((r) => r.id === id);
  const [tab, setTab] = useState(initialTab);
  const [detail, setDetail] = useState<Reaction | null>(null);
  const [commentFilter, setCommentFilter] = useState("All reactions");
  const [selected, setSelected] = useState<string[] | null>(null);
  const [retrying, setRetrying] = useState("");
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);
  const generatingRef = useRef(false);
  const [saveError, setSaveError] = useState("");
  const retryRequest = useRef<string | null>(null);
  const retryPending = useRef(false);
  const router = useRouter();
  const toast = useToast();
  if (run && !finishedRun(run)) return <SimulationProgress id={id} />;
  if (!report)
    return (
      <>
        <PageHeading
          eyebrow="Simulation report"
          title="This report isn’t in this workspace."
        />
        <EmptyState
          title="Let’s find another perspective"
          description="The report may have been removed or belong to another account. Older demo reports are available only in the browser where they were created."
        >
          <ButtonLink href="/history">View simulation history</ButtonLink>
        </EmptyState>
      </>
    );
  const r = report;
  const recs = recommendations(r);
  const checked =
    selected || (r.applied.length ? r.applied : recs.map((x) => x.id));
  const complete = r.reactions.filter((x) => x.status === "complete");
  const fallbackCount = complete.filter((x) => x.evaluationSource === "fallback").length;
  const failed = r.reactions.filter((x) => x.status === "failed");
  const ranking = [...complete].sort((a, b) => b.score - a.score);
  const insights = reportInsights(r);
  const retryable = run?.evaluations.filter((item) => item.status === "failed" && item.can_retry) ?? [];
  const patch = (values: Partial<Report>) =>
    updateDemo((s) => ({
      ...s,
      reports: s.reports.map((x) => (x.id === r.id ? { ...x, ...values } : x)),
    }));
  const rerun = (body?: string) => {
    updateDemo((s) => ({
      ...s,
      draft: {
        ...s.draft,
        productId: r.product.id,
        post: { ...r.post, ...(body ? { body } : {}) },
        audience: r.audience,
        personas: r.reactions.map((x) => x.persona),
        language: r.language,
        step: 0,
        fresh: true,
        activeRunId: undefined,
        runRequestId: undefined,
        requestSignature: undefined,
      },
    }));
    router.push("/simulate");
  };
  async function retry(reaction: Reaction) {
    if (retryPending.current) return;
    retryPending.current = true;
    setRetrying(reaction.persona.id);
    if (r.source === "server" && reaction.evaluationId) {
      try { await retrySimulation(r.id, reaction.evaluationId); }
      catch (error) { toast(errorMessage(error)); }
      finally { setRetrying(""); retryPending.current = false; }
      return;
    }
    await new Promise((resolve) => setTimeout(resolve, 650));
    updateDemo((s) => ({
      ...s,
      reports: s.reports.map((x) =>
        x.id === r.id
          ? {
              ...x,
              reactions: x.reactions.map((v, i) =>
                v.persona.id === reaction.persona.id
                  ? evaluate(v.persona, x.product, x.post, x.language, i)
                  : v,
              ),
            }
          : x,
      ),
    }));
    setRetrying("");
    retryPending.current = false;
    toast("Persona evaluation completed; previous results preserved");
  }
  async function retryMissing() {
    if (retryPending.current) return;
    retryPending.current = true;
    setRetrying("all");
    retryRequest.current ??= crypto.randomUUID();
    try {
      await retryFailedSimulation(r.id, retryRequest.current);
      retryRequest.current = null;
      toast("Missing perspectives queued. Completed results are preserved.");
    } catch (error) { toast(errorMessage(error)); }
    finally { setRetrying(""); retryPending.current = false; }
  }
  async function generate() {
    if (r.source === "server") {
      if (generatingRef.current) return;
      generatingRef.current = true; setGenerating(true); setSaveError("");
      try { await generateReportRevision(r.id, checked); toast("Caption draft created from the saved report facts"); }
      catch (error) { setSaveError(errorMessage(error)); }
      finally { generatingRef.current = false; setGenerating(false); }
      return;
    }
    const additions = recs
      .filter((x) => checked.includes(x.id))
      .map((x) => x.addition);
    const bangla = r.language === "bn";
    const body = [
      r.post.body,
      additions.length
        ? `${bangla ? "আরও তথ্য" : "A few useful details"}:\n${additions.map((x) => `• ${x}`).join("\n")}`
        : "",
      r.post.offer ? `${bangla ? "অফার" : "Offer"}: ${r.post.offer}` : "",
      r.post.cta,
      r.post.hashtags,
    ]
      .filter(Boolean)
      .join("\n\n");
    patch({ revised: body, applied: checked });
    toast(
      "Revised caption created. Review bracketed details before publishing.",
    );
  }
  async function saveRevision() {
    setSaving(true); setSaveError("");
    try {
      const existing = state.posts.find((post) => post.id === r.post.id);
      if (!existing) throw new Error("The original post is no longer available. Create a new post from the Products screen.");
      if (r.source === "server") await saveReportChanges(r.id, r.revised, checked);
      await savePost({ ...existing, body: r.revised });
      toast("Revised caption saved as a separate post version");
    } catch (error) { setSaveError(errorMessage(error)); }
    finally { setSaving(false); }
  }
  const comments = complete.filter(
    (x) => commentFilter === "All reactions" || x.sentiment === commentFilter,
  );
  return (
    <div className="report-page">
      <PageHeading
        eyebrow="Simulation report"
        title={r.title}
        description={`${r.post.platform} post · ${dateLabel(r.createdAt)} · ${r.reactions.length} buyer personas`}
      >
        <button
          className="button secondary"
          onClick={() =>
            download(
              `buyora-report-${r.id}.json`,
              JSON.stringify(
                {
                  ...r,
                  disclosure:
                    "Fictional buyer perspectives. These are simulated reactions, not actual customer feedback or guaranteed predictions.",
                },
                null,
                2,
              ),
            )
          }
        >
          <Icon name="download" size={16} />
          Export report
        </button>
        <button className="button secondary" onClick={() => window.print()}>
          <Icon name="file" size={16} />
          Print / Save PDF
        </button>
        <button className="button primary" onClick={() => rerun()}>
          <Icon name="refresh" size={16} />
          Run fresh simulation
        </button>
      </PageHeading>
      <Notice>
        {r.language === "bn"
          ? "এটি নমুনা সিমুলেশন। প্রতিক্রিয়া, স্কোর ও পরামর্শ আসল ক্রেতার মতামত বা নিশ্চিত পূর্বাভাস নয়।"
          : r.source === "server"
            ? "Saved simulated perspectives. These are fictional buyer assessments, not actual customer feedback or guaranteed sales predictions."
            : "A simulated perspective, not a prediction. These are illustrative demo scores and fictional buyer reactions, not actual customer feedback."}
      </Notice>
      {fallbackCount > 0 && <Notice tone="warning">{fallbackCount} of {complete.length} completed perspectives use a rule-based fallback because AI evaluation was unavailable or a spending limit was reached. Their scores are included in this assessment and marked below.</Notice>}
      <section className="report-coverage panel" aria-label="Assessment coverage">
        <div>
          <strong>{complete.length} of {r.reactions.length} perspectives completed</strong>
          <p>{failed.length ? `${failed.length} missing. Completed results are saved and excluded failures do not lower scores.` : "All selected personas are included in this assessment."}</p>
          {failed.length > retryable.length && r.source === "server" && <p>Some missing perspectives need your workspace owner’s help or a fresh simulation. See Audience insights for each next step.</p>}
        </div>
        {retryable.length > 0 && <button className="button primary" disabled={!!retrying} onClick={retryMissing}>
          {retrying === "all" ? "Queueing missing perspectives…" : `Retry missing perspectives (${retryable.length})`}
        </button>}
      </section>
      <div className="report-tabs" role="tablist" aria-label="Report sections">
        {tabs.map((t, i) => (
          <button
            id={`report-tab-${i}`}
            role="tab"
            aria-selected={tab === i}
            aria-controls={`report-panel-${i}`}
            tabIndex={tab === i ? 0 : -1}
            onKeyDown={(e) => {
              if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
                e.preventDefault();
                const next =
                  (tab + (e.key === "ArrowRight" ? 1 : -1) + tabs.length) %
                  tabs.length;
                setTab(next);
                document.getElementById(`report-tab-${next}`)?.focus();
              }
            }}
            className={tab === i ? "active" : ""}
            key={t}
            onClick={() => setTab(i)}
          >
            {t}
            {i === 4 && <span>{recs.length}</span>}
          </button>
        ))}
      </div>
      <div
        role="tabpanel"
        id={`report-panel-${tab}`}
        aria-labelledby={`report-tab-${tab}`}
        tabIndex={0}
        className="report-tab-panel"
      >
        {tab === 0 && (
          <>
            <section className="verdict-panel">
              <div>
                <Badge tone="blue">
                  <Icon name="spark" size={13} />
                  The bigger picture
                </Badge>
                <h2>
                  {insights.title}
                </h2>
                <p>
                  {insights.explanation}
                </p>
                {insights.weakest && insights.concern && <div className="report-main-concern">
                  <strong>Start with {insights.weakest.label.toLowerCase()} · {insights.weakest.score}/100</strong>
                  <p>{insights.concern.persona.name} asks: “{insights.concern.question}”</p>
                  <button className="text-link" onClick={() => setDetail(insights.concern)}>See this buyer’s reasoning <Icon name="arrow" size={15} /></button>
                </div>}
                <button className="text-link" onClick={() => setTab(4)}>
                  See what you can improve <Icon name="arrow" size={16} />
                </button>
              </div>
              {insights.score !== null ? <ScoreRing score={insights.score} large /> : <span className="unavailable-score">Score unavailable</span>}
            </section>
            <div className="stats-grid report-stats">
              {[
                {
                  label: "Interest",
                  value: overall(r, 0),
                  icon: "heart",
                  sub: "How appealing the post appears",
                },
                {
                  label: "Trust",
                  value: overall(r, 4),
                  icon: "shield",
                  sub: "How reassuring the details feel",
                },
                {
                  label: "Clarity",
                  value: overall(r, 5),
                  icon: "eye",
                  sub: "How easy the offer is to understand",
                },
                {
                  label: "Purchase intent",
                  value: overall(r, 6),
                  icon: "box",
                  sub: "Illustrative willingness to buy",
                },
              ].map((s) => (
                <article className="stat-card" key={s.label}>
                  <div className="row spread">
                    <span>{s.label}</span>
                    <Icon name={s.icon} size={18} />
                  </div>
                  <div className="stat-value">
                    {complete.length ? s.value : "—"}
                    {complete.length > 0 && <small>/100</small>}
                  </div>
                  <div className="tiny-bar">
                    <span style={{ width: `${s.value}%` }} />
                  </div>
                  <p>{s.sub}</p>
                </article>
              ))}
            </div>
            <div className="report-overview-grid">
              <section className="panel">
                <div className="panel-heading">
                  <div>
                    <h2>Who connects with your post?</h2>
                    <p>Ranked by the average of seven sample scores.</p>
                  </div>
                  <button className="text-link" onClick={() => setTab(1)}>
                    All personas <Icon name="arrow" size={14} />
                  </button>
                </div>
                <div className="ranking-list">
                  {!ranking.length && <p className="report-empty-ranking">No completed perspectives yet. Review the missing evaluations in Audience insights.</p>}
                  {ranking.slice(0, 4).map((x, i) => (
                    <button
                      key={x.persona.id}
                      className="ranking-row"
                      onClick={() => setDetail(x)}
                    >
                      <span className="rank-number">{i + 1}</span>
                      <Avatar persona={x.persona} small />
                      <span className="rank-name">
                        <strong>{x.persona.role}</strong>
                        <small>
                          {x.persona.name} · {x.persona.location}
                        </small>
                      </span>
                      <span className="ranking-bar">
                        <i style={{ width: `${x.score}%` }} />
                      </span>
                      <strong>{x.score}</strong>
                      <Icon name="chevron" size={14} />
                    </button>
                  ))}
                </div>
              </section>
              <section className="panel concern-panel">
                <div className="panel-heading">
                  <div>
                    <h2>Checks before you publish</h2>
                    <p>Suggestions based on the saved caption and product details.</p>
                  </div>
                  <Icon name="chat" size={20} />
                </div>
                {recs.slice(0, 3).map((x, i) => (
                  <div className="concern-row" key={x.id}>
                    <span>{i + 1}</span>
                    <div>
                      <h3>{x.title}</h3>
                      <p>{x.detail}</p>
                    </div>
                  </div>
                ))}
                <button className="text-link" onClick={() => setTab(4)}>
                  Build your improvement checklist{" "}
                  <Icon name="arrow" size={15} />
                </button>
              </section>
            </div>
            <section className="panel original-post">
              <div>
                <Badge>{r.post.platform} · Original post</Badge>
                <h3>{r.post.headline}</h3>
                <p>{r.post.body}</p>
              </div>
              <ProductArt product={r.product} />
            </section>
          </>
        )}
        {tab === 1 && (
          <>
            <div className="section-title-row">
              <div>
                <h2>Different priorities. Different reactions.</h2>
                <p>
                  Every persona reviews the same product and post on a
                  consistent 0–100 scale.
                </p>
              </div>
              <Badge>
                {complete.length} / {r.reactions.length} completed
              </Badge>
            </div>
            <div className="audience-grid">
              {[...r.reactions]
                .sort((a, b) => b.score - a.score)
                .map((x) => (
                  <article className="panel audience-card" key={x.persona.id}>
                    <div className="row spread">
                      <div className="row">
                        <Avatar persona={x.persona} />
                        <div>
                          <h3>{x.persona.name}</h3>
                          <span className="muted">{x.persona.role}</span>
                        </div>
                      </div>
                      <Badge
                        tone={
                          x.status === "failed"
                            ? "red"
                            : x.sentiment === "Interested"
                              ? "green"
                              : "amber"
                        }
                      >
                        {x.status === "failed" ? "Incomplete" : x.sentiment}
                      </Badge>
                    </div>
                    <p className="persona-need">{x.persona.need}</p>
                    {x.evaluationSource === "fallback" && <Notice tone="warning">Rule-based fallback · {evaluationErrors[x.fallbackReason ?? ""] ?? "AI evaluation was unavailable or limited."}
                      {run?.evaluations.find((item) => item.id === x.evaluationId)?.can_retry && <div><button className="text-link" disabled={!!retrying} onClick={() => retry(x)}>Retry with AI (uses the model)</button></div>}
                    </Notice>}
                    {x.status === "complete" ? (
                      <>
                        <div className="score-bars">
                          {dimensions.map((d, i) => (
                            <div key={d}>
                              <span>{d}</span>
                              <div>
                                <i style={{ width: `${x.scores[i]}%` }} />
                              </div>
                              <strong>{x.scores[i]}</strong>
                            </div>
                          ))}
                        </div>
                        <blockquote>“{x.comment}”</blockquote>
                        <div className="row spread">
                          <span className="muted">
                            Overall fit{" "}
                            <strong className="accent-text">
                              {x.score}/100
                            </strong>
                          </span>
                          <button
                            className="text-link"
                            onClick={() => setDetail(x)}
                          >
                            Why this reaction? <Icon name="arrow" size={14} />
                          </button>
                        </div>
                      </>
                    ) : (
                      <div className="failed-evaluation">
                        <Icon name="refresh" size={25} />
                        <h3>This perspective needs another moment.</h3>
                        <p>
                          {r.source === "server" ? evaluationErrors[x.errorCode ?? ""] ?? "This assessment could not finish. Completed perspectives are saved." : "The demo intentionally interrupted this evaluation. Completed evaluations will stay as they are."}
                        </p>
                        {r.source === "server" && !run?.evaluations.find((item) => item.id === x.evaluationId)?.can_retry
                          ? <p>{x.errorCode === "configuration_changed" ? "Use Run fresh simulation above to evaluate with the updated service." : "If service settings have been fixed, start a fresh simulation. Completed results remain in this report."}</p>
                          :
                        <button
                          className="button secondary"
                          disabled={!!retrying}
                          onClick={() => retry(x)}
                        >
                          {retrying === x.persona.id
                            ? "Retrying…"
                            : "Retry evaluation"}
                        </button>}
                      </div>
                    )}
                  </article>
                ))}
            </div>
            <Notice>
              Overall fit is the arithmetic mean of interest, relevance, value,
              price fit, trust, clarity, and purchase intent. {r.source === "server" ? "Scores use the saved input and versioned rubric. Rule-based fallback assessments are labeled; failed evaluations are excluded." : "Placeholder scores are generated from caption completeness and sample persona preferences."}
            </Notice>
          </>
        )}
        {tab === 2 && (
          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>Watch buyer reactions spread</h2>
                <p>
                  An illustrative animation based on completed persona scores. Its 60 viewers are fictional extensions of those personas, not 60 independent AI evaluations or a forecast of reach.
                  Play three rounds, select a viewer, or drag the canvas to explore.
                </p>
              </div>
            </div>
            {complete.length ? <ReactionMap key={r.id} reactions={r.reactions} /> : <p>Complete at least one perspective to explore the spread illustration.</p>}
          </section>
        )}
        {tab === 3 && (
          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>What might buyers ask?</h2>
                <p>
                  {r.language === "bn"
                    ? "কাল্পনিক ক্রেতাদের নমুনা মন্তব্য।"
                    : "A fictional comment stream. Useful questions to prepare for."}
                </p>
              </div>
              <label className="filter-select">
                <span className="sr-only">Filter reactions</span>
                <select
                  value={commentFilter}
                  onChange={(e) => setCommentFilter(e.target.value)}
                >
                  {[
                    "All reactions",
                    "Interested",
                    "Has questions",
                    "Unconvinced",
                  ].map((v) => (
                    <option key={v}>{v}</option>
                  ))}
                </select>
              </label>
            </div>
            {comments.length ? (
              <div className="comment-stream">
                {comments.map((x, i) => (
                  <article className="comment-row" key={x.persona.id}>
                    <span className="comment-time">
                      00:{String((i + 1) * 7).padStart(2, "0")}
                    </span>
                    <Avatar persona={x.persona} small />
                    <div>
                      <h3>
                        {x.persona.role} <span>{x.persona.name}</span>
                      </h3>
                      <p lang={r.language}>{x.comment}</p>
                    </div>
                    <Badge
                      tone={x.sentiment === "Interested" ? "green" : "amber"}
                    >
                      {x.sentiment}
                    </Badge>
                  </article>
                ))}
              </div>
            ) : (
              <EmptyState
                title="No reactions in this group"
                description="Choose another filter to see more buyer perspectives."
              />
            )}
          </section>
        )}
        {tab === 4 && (
          <div className="improvement-grid">
            <section className="panel checklist-panel">
              <div className="panel-heading">
                <div>
                  <h2>Small fixes, clearer decisions.</h2>
                  <p>Choose the suggestions to include in your revision.</p>
                </div>
              </div>
              {!!r.objectionGroups?.length && <details className="report-ai-details"><summary>Recurring concerns across completed buyers</summary><ul>{r.objectionGroups.map((group) => <li key={group.topic}><strong>{group.frequency} {group.frequency === 1 ? "perspective" : "perspectives"}</strong>: <span lang={r.language}>{group.questions[0]}</span></li>)}</ul></details>}
              {r.trustSignals && <details className="report-ai-details"><summary>Information detected in the saved inputs</summary><dl className="details-list">{Object.entries(r.trustSignals).map(([key, signal]) => <div key={key}><dt>{key.replaceAll("_", " ")}</dt><dd>{!signal.supplied ? "Not supplied" : signal.visible ? "Mentioned in the post" : "Product details only"}{signal.negative && " · negative policy stated"}{signal.evidence.length > 0 && <p className="quiet-note">{signal.evidence.join(" · ")}</p>}</dd></div>)}</dl><p className="quiet-note">Detection identifies supplied text; it does not independently verify seller claims.</p></details>}
              {recs.map((rec) => (
                <label key={rec.id} className="recommendation-check">
                  <input
                    type="checkbox"
                    checked={checked.includes(rec.id)}
                    onChange={(e) =>
                      setSelected(
                        e.target.checked
                          ? [...checked, rec.id]
                          : checked.filter((x) => x !== rec.id),
                      )
                    }
                  />
                  <div>
                    <Badge
                      tone={rec.priority === "High priority" ? "amber" : "blue"}
                    >
                      {rec.priority}
                    </Badge>
                    <h3>{rec.title}</h3>
                    <p>{rec.detail}</p>
                    {!!rec.evidence?.length && <p className="quiet-note">Saved evidence: {rec.evidence.map((quote) => `“${quote}”`).join(" · ")}</p>}
                  </div>
                </label>
              ))}
              <button
                className="button primary"
                onClick={generate}
                disabled={!checked.length || generating}
              >
                <Icon name="spark" size={16} />
                {generating ? "Creating saved caption…" : "Create revised caption"}
              </button>
              <p className="quiet-note">
                Built from your supplied product details. Review every claim before publishing. Your original post stays unchanged.
              </p>
            </section>
            <section className="panel revised-panel">
              <div className="panel-heading">
                <div>
                  <h2>A clearer version of your post</h2>
                  <p>Review and edit every detail before using it.</p>
                </div>
                <Badge tone="blue">New revision</Badge>
              </div>
              {r.revised ? (
                <>
                  <label className="field">
                    <span className="sr-only">Revised caption</span>
                    <textarea
                      rows={16}
                      maxLength={8000}
                      value={r.revised}
                      onChange={(e) => patch({ revised: e.target.value })}
                      lang={r.language}
                    />
                  </label>
                  <Notice>
                    Replace any [bracketed information] with verified details.
                    Confirm all delivery, policy, and payment claims.
                  </Notice>
                  <div className="revision-actions">
                    {r.source === "server" && <button className="button secondary" disabled={saving} onClick={async () => {
                      setSaving(true); setSaveError("");
                      try { await saveReportChanges(r.id, r.revised, checked); toast("Caption draft saved to your report"); }
                      catch (error) { setSaveError(errorMessage(error)); }
                      finally { setSaving(false); }
                    }}>Save caption draft</button>}
                    <button
                      className="button secondary"
                      onClick={async () => {
                        try {
                          await navigator.clipboard.writeText(r.revised);
                          toast("Revised caption copied");
                        } catch {
                          toast(
                            "Clipboard unavailable. Select and copy the caption manually.",
                          );
                        }
                      }}
                    >
                      <Icon name="copy" size={15} />
                      Copy caption
                    </button>
                    <button className="button secondary" disabled={saving} onClick={saveRevision}>
                      <Icon name="file" size={15} />
                      {saving ? "Saving…" : "Save as post version"}
                    </button>
                    <button
                      className="button primary"
                      onClick={() => rerun(r.revised)}
                    >
                      Test this revision <Icon name="arrow" size={15} />
                    </button>
                  </div>
                  {saveError && <p className="form-error" role="alert">{saveError}</p>}
                </>
              ) : (
                <EmptyState
                  title="A fresh draft, built from your choices"
                  description="Select recommendations, then create a revised caption. The original stays in your report."
                />
              )}
            </section>
          </div>
        )}
      </div>
      <div className="report-bottom">
        <Link href="/history" className="text-link">
          <Icon name="back" size={15} />
          Back to history
        </Link>
        <Link href="/compare" className="text-link">
          <Icon name="compare" size={16} />
          Compare with another simulation
        </Link>
      </div>
      <PrintReport report={r} />
      {detail && (
        <Modal
          title={`${detail.persona.name}’s perspective`}
          onClose={() => setDetail(null)}
        >
          <div className="row">
            <Avatar persona={detail.persona} />
            <div>
              <h3>{detail.persona.role}</h3>
              <p>
                {detail.persona.age} · {detail.persona.location}
              </p>
            </div>
          </div>
          <blockquote className="detail-quote" lang={r.language}>
            “{detail.comment}”
          </blockquote>
          {detail.evaluationSource === "fallback" && <Notice tone="warning">This is a rule-based fallback assessment, not an AI verdict.</Notice>}
          {!!detail.scoreDrivers?.length && <div><h4>How the seven scores were assessed</h4><dl className="details-list">{detail.scoreDrivers.map((driver, index) => <div key={driver.dimension}><dt>{driver.dimension} · {detail.scores[index]}/100</dt><dd lang={r.language}>{driver.reason}{driver.evidence.length > 0 && <p className="quiet-note">{driver.evidence.map((quote) => `“${quote}”`).join(" · ")}</p>}</dd></div>)}</dl></div>}
          {!!detail.objections?.length && <div><h4>Buyer concerns</h4><ul lang={r.language}>{detail.objections.map((text, index) => <li key={index}>{text}</li>)}</ul></div>}
          <dl className="details-list">
            <div>
              <dt>Why this reaction?</dt>
              <dd>{detail.reason}</dd>
            </div>
            <div>
              <dt>What works</dt>
              <dd>{detail.positive}</dd>
            </div>
            <div>
              <dt>What they still need to know</dt>
              <dd>{detail.question}</dd>
            </div>
          </dl>
          {!!detail.evidence?.length && <div><h4>Evidence from the saved input</h4><ul>{detail.evidence.map((quote, index) => <li key={index}>“{quote}”</li>)}</ul></div>}
          <Notice>
            This explanation describes a sample persona response, not a real
            buyer.
          </Notice>
        </Modal>
      )}
    </div>
  );
}
