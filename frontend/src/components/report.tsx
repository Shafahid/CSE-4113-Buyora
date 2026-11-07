"use client";
import Link from "next/link";
import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  dateLabel,
  dimensions,
  evaluate,
  overall,
  recommendations,
  Reaction,
  Report,
  savePostVersion,
} from "@/lib/demo-data";
import { download, updateDemo, useDemo } from "@/lib/store";
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
  const state = useDemo();
  const report = state.reports.find((r) => r.id === id);
  const [tab, setTab] = useState(initialTab);
  const [detail, setDetail] = useState<Reaction | null>(null);
  const [commentFilter, setCommentFilter] = useState("All reactions");
  const [selected, setSelected] = useState<string[] | null>(null);
  const [retrying, setRetrying] = useState("");
  const router = useRouter();
  const toast = useToast();
  if (!report)
    return (
      <>
        <PageHeading
          eyebrow="Simulation report"
          title="This report isn’t in this workspace."
        />
        <EmptyState
          title="Let’s find another perspective"
          description="The report may have been removed, or it was saved in a different browser."
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
  const failed = r.reactions.filter((x) => x.status === "failed");
  const ranking = [...complete].sort((a, b) => b.score - a.score);
  const interest = overall(r, 0);
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
      },
    }));
    router.push("/simulate");
  };
  async function retry(reaction: Reaction) {
    setRetrying(reaction.persona.id);
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
    toast("Persona evaluation completed; previous results preserved");
  }
  function generate() {
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
  function saveRevision() {
    updateDemo((s) => {
      const existing = s.posts.find((x) => x.id === r.post.id);
      const post = savePostVersion(existing || r.post, {
        ...r.post,
        body: r.revised,
      });
      return {
        ...s,
        posts: existing
          ? s.posts.map((x) => (x.id === post.id ? post : x))
          : [...s.posts, post],
      };
    });
    toast("Revised caption saved as a separate post version");
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
                    "Illustrative frontend demo. These are simulated reactions, not actual customer feedback or guaranteed predictions.",
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
          Print
        </button>
        <button className="button primary" onClick={() => rerun()}>
          <Icon name="refresh" size={16} />
          Run again
        </button>
      </PageHeading>
      <Notice>
        {r.language === "bn"
          ? "এটি নমুনা সিমুলেশন। প্রতিক্রিয়া, স্কোর ও পরামর্শ আসল ক্রেতার মতামত বা নিশ্চিত পূর্বাভাস নয়।"
          : "A simulated perspective, not a prediction. These are illustrative demo scores and fictional buyer reactions, not actual customer feedback."}
      </Notice>
      {failed.length > 0 && (
        <Notice tone="warning">
          {failed.length} persona evaluation didn’t finish. Completed results
          are saved. Retry the missing perspective from Audience insights.
        </Notice>
      )}
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
                  {interest >= 75
                    ? "Your post sparks interest."
                    : "Your post has room to grow."}
                  <br />
                  <span>
                    {overall(r, 4) < 65
                      ? "A little reassurance can go a long way."
                      : "Give buyers a clear next step."}
                  </span>
                </h2>
                <p>
                  {complete.length} perspectives explored. {recs.length}{" "}
                  practical improvements to consider.
                  <br />
                  {ranking[0]
                    ? `Your strongest sample match: ${ranking[0].persona.role.toLowerCase()}.`
                    : "Complete an evaluation to see audience rankings."}
                </p>
                <button className="text-link" onClick={() => setTab(4)}>
                  See what you can improve <Icon name="arrow" size={16} />
                </button>
              </div>
              <ScoreRing score={overall(r)} large />
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
                    {s.value}
                    <small>/100</small>
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
                    <h2>A little more clarity on…</h2>
                    <p>Questions your post could answer.</p>
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
                          The demo intentionally interrupted this evaluation.
                          Completed evaluations will stay as they are.
                        </p>
                        <button
                          className="button secondary"
                          disabled={!!retrying}
                          onClick={() => retry(x)}
                        >
                          {retrying === x.persona.id
                            ? "Retrying…"
                            : "Retry evaluation"}
                        </button>
                      </div>
                    )}
                  </article>
                ))}
            </div>
            <Notice>
              Overall fit is the arithmetic mean of interest, relevance, value,
              price fit, trust, clarity, and purchase intent. Placeholder scores
              are generated from caption completeness and sample persona
              preferences.
            </Notice>
          </>
        )}
        {tab === 2 && (
          <section className="panel">
            <div className="panel-heading">
              <div>
                <h2>Watch buyer reactions spread</h2>
                <p>
                  Play three rounds of fictional buyer activity. Select a viewer
                  to inspect their reaction, or drag the canvas to explore.
                </p>
              </div>
            </div>
            <ReactionMap key={r.id} reactions={r.reactions} />
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
                  </div>
                </label>
              ))}
              <button
                className="button primary"
                onClick={generate}
                disabled={!checked.length}
              >
                <Icon name="spark" size={16} />
                Create revised caption
              </button>
              <p className="quiet-note">
                Template-based demo. Your original post stays unchanged.
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
                    <button className="button secondary" onClick={saveRevision}>
                      <Icon name="file" size={15} />
                      Save as post version
                    </button>
                    <button
                      className="button primary"
                      onClick={() => rerun(r.revised)}
                    >
                      Test this revision <Icon name="arrow" size={15} />
                    </button>
                  </div>
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
          <Notice>
            This explanation describes a sample persona response, not a real
            buyer.
          </Notice>
        </Modal>
      )}
    </div>
  );
}
function PrintReport({ report: r }: { report: Report }) {
  return (
    <article className="print-report">
      <h1>Buyora · Simulation report</h1>
      <h2>{r.title}</h2>
      <p>
        {dateLabel(r.createdAt)} · {r.post.platform}
      </p>
      <p>
        Illustrative demo. Scores and fictional reactions are not actual
        customer feedback or guaranteed predictions.
      </p>
      <h3>Original caption</h3>
      <p>{r.post.body}</p>
      <h3>Summary · {overall(r)}/100</h3>
      <table>
        <thead>
          <tr>
            <th>Persona</th>
            {dimensions.map((d) => (
              <th key={d}>{d}</th>
            ))}
            <th>Overall</th>
          </tr>
        </thead>
        <tbody>
          {r.reactions.map((x) => (
            <tr key={x.persona.id}>
              <td>{x.persona.role}</td>
              {x.scores.map((s, i) => (
                <td key={i}>{x.status === "complete" ? s : "Incomplete"}</td>
              ))}
              <td>{x.status === "complete" ? x.score : "Incomplete"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <h3>Buyer reactions</h3>
      {r.reactions
        .filter((x) => x.status === "complete")
        .map((x) => (
          <div key={x.persona.id}>
            <h4>{x.persona.role}</h4>
            <p>{x.comment}</p>
            <p>{x.reason}</p>
          </div>
        ))}
      <h3>Recommendations</h3>
      <ul>
        {recommendations(r).map((x) => (
          <li key={x.id}>
            <strong>{x.title}:</strong> {x.detail}
          </li>
        ))}
      </ul>
      {r.revised && (
        <>
          <h3>Revised caption</h3>
          <p style={{ whiteSpace: "pre-wrap" }}>{r.revised}</p>
        </>
      )}
    </article>
  );
}
