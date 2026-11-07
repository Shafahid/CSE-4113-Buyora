"use client";
import Link from "next/link";
import { useDemo } from "@/lib/store";
import { dateLabel, overall, recommendations } from "@/lib/demo-data";
import { CountUp, useCountUpProgress } from "./count-up";
import {
  Avatar,
  Badge,
  ButtonLink,
  EmptyState,
  Icon,
  PageHeading,
  ProductArt,
  ScoreRing,
} from "./ui";

export function Dashboard() {
  const countProgress = useCountUpProgress();
  const { profile, reports, products } = useDemo();
  const latest = reports[0];
  const average = reports.length
    ? Math.round(
        reports.reduce((s, r) => s + overall(r, 4), 0) / reports.length,
      )
    : 0;
  return (
    <>
      <PageHeading
        eyebrow="Overview"
        title={`Welcome, ${profile.name.split(" ")[0]}.`}
        description="A fresh perspective on your products, posts, and potential buyers."
      >
        <ButtonLink href="/simulate">
          <Icon name="plus" size={17} />
          New simulation
        </ButtonLink>
      </PageHeading>
      <section className="welcome-panel">
        <div>
          <Badge tone="blue">
            <Icon name="spark" size={13} />
            Your pre-publish companion
          </Badge>
          <h2>
            <b>Good posts start with</b>
            <br />
            <b>understanding people.</b>
          </h2>
          <p>Bring your next idea. See what different buyers might notice.</p>
          <ButtonLink href="/simulate">
            Explore buyer reactions <Icon name="arrow" size={16} />
          </ButtonLink>
        </div>
        <div className="welcome-orbit">
          <div className="orbit-circle one" />
          <div className="orbit-circle two" />
          <div className="welcome-center">
            <span className="small-brand-mark" />
          </div>
          {(latest?.reactions || []).slice(0, 4).map((r, i) => (
            <div key={r.persona.id} className={`orbit-avatar orbit-${i}`}>
              <Avatar persona={r.persona} />
            </div>
          ))}
          <div className="orbit-tag">
            {/* <span className="status-dot" /> A different point of view */}
          </div>
        </div>
      </section>
      <div className="stats-grid">
        {[
          {
            label: "Total simulations",
            value: reports.length,
            padStart: 2,
            icon: "chart",
            sub: "Saved in your workspace",
          },
          {
            label: "Average trust",
            value: average,
            unit: "/100",
            icon: "shield",
            sub: "Across completed reactions",
          },
          {
            label: "Buyer perspectives",
            value: reports.reduce(
              (s, r) =>
                s + r.reactions.filter((x) => x.status === "complete").length,
              0,
            ),
            icon: "people",
            sub: "Simulated, never real feedback",
          },
          {
            label: "Your products",
            value: products.filter((p) => !p.archived).length,
            padStart: 2,
            icon: "box",
            sub: "Ready for a fresh perspective",
          },
        ].map((s) => (
          <article className="stat-card" key={s.label}>
            <div className="row spread">
              <span>{s.label}</span>
              <Icon name={s.icon} size={18} />
            </div>
            <div className="stat-value">
              <CountUp
                value={s.value}
                progress={countProgress}
                padStart={s.padStart}
              />
              <small>{s.unit}</small>
            </div>
            <p>{s.sub}</p>
          </article>
        ))}
      </div>
      <div className="dashboard-grid">
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Recent simulations</h2>
              <p>Pick up where you left off.</p>
            </div>
            <Link className="text-link" href="/history">
              View all <Icon name="arrow" size={15} />
            </Link>
          </div>
          {reports.length ? (
            <div className="recent-list">
              {reports.slice(0, 4).map((r) => (
                <Link
                  href={`/reports/${r.id}`}
                  className="recent-row"
                  key={r.id}
                >
                  <ProductArt product={r.product} className="product-thumb" />
                  <div className="recent-title">
                    <h3>{r.title}</h3>
                    <span>
                      {r.post.platform} · {dateLabel(r.createdAt)}
                    </span>
                  </div>
                  <Badge tone={overall(r) >= 75 ? "green" : "amber"}>
                    {overall(r) >= 75
                      ? "Promising interest"
                      : "Room to improve"}
                  </Badge>
                  <div className="recent-score">
                    <strong>
                      <CountUp value={overall(r)} progress={countProgress} />
                    </strong>
                    <small>/100</small>
                  </div>
                  <Icon name="chevron" size={16} />
                </Link>
              ))}
            </div>
          ) : (
            <EmptyState
              title="Your first perspective awaits"
              description="Run a simulation to start your report collection."
            >
              <ButtonLink href="/simulate">Run a simulation</ButtonLink>
            </EmptyState>
          )}
        </section>
        <section className="panel insight-panel">
          <div className="row spread">
            <span className="section-kicker">From your latest report</span>
            <Icon name="spark" size={18} />
          </div>
          {latest ? (
            <>
              <ScoreRing score={overall(latest)} progress={countProgress} />
              <h3>Virality Score</h3>
              <p>
                {recommendations(latest)[0]?.detail ||
                  "Review how each buyer responds to your post."}
              </p>
              <Link className="text-link" href={`/reports/${latest.id}`}>
                Explore recommendations <Icon name="arrow" size={15} />
              </Link>
            </>
          ) : (
            <>
              <h3>
                Small changes.
                <br />
                Clearer posts.
              </h3>
              <p>Your latest report insights will appear here.</p>
            </>
          )}
        </section>
      </div>
      <div className="workspace-demo-note">
        <Icon name="info" size={17} />
        <p>
          You’re exploring a demo workspace. Products and reports are saved in
          this browser. All scores and reactions are illustrative placeholders.
        </p>
      </div>
    </>
  );
}
