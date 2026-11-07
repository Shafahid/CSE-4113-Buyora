"use client";
import Link from "next/link";
import { useState } from "react";
import { Report, dateLabel, dimensions, overall } from "@/lib/demo-data";
import { download, updateDemo, useDemo } from "@/lib/store";
import { comparisonSelection } from "@/lib/workflow";
import {
  Badge,
  ButtonLink,
  EmptyState,
  Field,
  Icon,
  Modal,
  Notice,
  PageHeading,
  ProductArt,
  ScoreRing,
  useToast,
} from "./ui";

export function History() {
  const { reports } = useDemo();
  const [query, setQuery] = useState("");
  const [platform, setPlatform] = useState("All platforms");
  const [sort, setSort] = useState("Newest first");
  const [remove, setRemove] = useState<Report | null>(null);
  const toast = useToast();
  const list = reports
    .filter(
      (r) =>
        `${r.title} ${r.post.headline}`
          .toLowerCase()
          .includes(query.toLowerCase()) &&
        (platform === "All platforms" || r.post.platform === platform),
    )
    .sort((a, b) =>
      sort === "Best score"
        ? overall(b) - overall(a)
        : sort === "Oldest first"
          ? a.createdAt.localeCompare(b.createdAt)
          : b.createdAt.localeCompare(a.createdAt),
    );
  return (
    <>
      <PageHeading
        eyebrow="Simulation history"
        title="Every perspective, in one place."
        description="Revisit your reports, follow your progress, and keep learning."
      >
        <ButtonLink href="/compare" secondary>
          <Icon name="compare" size={16} />
          Compare reports
        </ButtonLink>
        <ButtonLink href="/simulate">
          <Icon name="plus" size={16} />
          New simulation
        </ButtonLink>
      </PageHeading>
      <section className="panel">
        <div className="history-toolbar">
          <label className="search-input">
            <Icon name="search" size={17} />
            <input
              aria-label="Search reports"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search simulations…"
            />
          </label>
          <div className="row">
            <select
              aria-label="Filter by platform"
              value={platform}
              onChange={(e) => setPlatform(e.target.value)}
            >
              {[
                "All platforms",
                "Facebook",
                "Instagram",
                "Facebook Live",
                "WhatsApp",
              ].map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
            <select
              aria-label="Sort reports"
              value={sort}
              onChange={(e) => setSort(e.target.value)}
            >
              {["Newest first", "Oldest first", "Best score"].map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </div>
        </div>
        {list.length ? (
          <div className="table-scroll">
            <table className="history-table">
              <thead>
                <tr>
                  <th>Product & post</th>
                  <th>Date</th>
                  <th>Personas</th>
                  <th>Overall fit</th>
                  <th>Status</th>
                  <th>
                    <span className="sr-only">Actions</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {list.map((r) => (
                  <tr key={r.id}>
                    <td>
                      <Link
                        href={`/reports/${r.id}`}
                        className="history-product"
                      >
                        <ProductArt
                          product={r.product}
                          className="product-thumb"
                        />
                        <span>
                          <strong>{r.title}</strong>
                          <small>
                            {r.post.platform} ·{" "}
                            {r.language === "bn" ? "Bangla" : "English"}
                          </small>
                        </span>
                      </Link>
                    </td>
                    <td>{dateLabel(r.createdAt)}</td>
                    <td>
                      <span className="row tight">
                        <Icon name="people" size={15} />
                        {r.reactions.length}
                      </span>
                    </td>
                    <td>
                      <strong className="table-score">{overall(r)}</strong>
                      <span className="muted">/100</span>
                    </td>
                    <td>
                      <Badge
                        tone={
                          r.reactions.some((x) => x.status === "failed")
                            ? "amber"
                            : "green"
                        }
                      >
                        {r.reactions.some((x) => x.status === "failed")
                          ? "Partial results"
                          : "Completed"}
                      </Badge>
                    </td>
                    <td>
                      <div className="row tight">
                        <Link
                          href={`/reports/${r.id}`}
                          className="button secondary small-button"
                        >
                          View report <Icon name="arrow" size={14} />
                        </Link>
                        <button
                          className="icon-button danger-text"
                          aria-label={`Delete report for ${r.title}`}
                          onClick={() => setRemove(r)}
                        >
                          <Icon name="trash" size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title={
              query || platform !== "All platforms"
                ? "No matching simulations"
                : "A fresh start for your next post"
            }
            description="Run a simulation or adjust your search to explore buyer perspectives."
          >
            <ButtonLink href="/simulate">Run a simulation</ButtonLink>
          </EmptyState>
        )}
        <div className="table-footer">
          <span>
            {list.length} of {reports.length} simulations
          </span>
          <span>Saved in this browser</span>
        </div>
      </section>
      {remove && (
        <Modal title="Remove this report?" onClose={() => setRemove(null)}>
          <p>
            The simulation for “{remove.title}” will be removed from this
            browser. Products and promotional posts are kept.
          </p>
          <div className="modal-actions">
            <button
              className="button secondary"
              onClick={() => setRemove(null)}
            >
              Keep report
            </button>
            <button
              className="button danger"
              onClick={() => {
                updateDemo((s) => ({
                  ...s,
                  reports: s.reports.filter((r) => r.id !== remove.id),
                }));
                setRemove(null);
                toast("Report removed");
              }}
            >
              Remove report
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}
export function Compare() {
  const state = useDemo();
  const [leftId, setLeft] = useState("");
  const [rightId, setRight] = useState("");
  const { reports, left, right } = comparisonSelection(
    state.reports,
    leftId,
    rightId,
  );
  const same = left?.id === right?.id;
  function exportComparison() {
    if (left && right)
      download(
        "buyora-comparison.json",
        JSON.stringify(
          {
            disclosure: "Illustrative demo scores, not real customer feedback.",
            left,
            right,
            differences: dimensions.map((dimension, i) => ({
              dimension,
              left: overall(left, i),
              right: overall(right, i),
              change: overall(right, i) - overall(left, i),
            })),
          },
          null,
          2,
        ),
      );
  }
  return (
    <>
      <PageHeading
        eyebrow="Compare reports"
        title="See what a change can do."
        description="Place two simulations side by side. Look for clearer signals, not certainty."
      >
        <button
          className="button secondary"
          disabled={!left || !right || same}
          onClick={exportComparison}
        >
          <Icon name="download" size={16} />
          Export comparison
        </button>
      </PageHeading>
      {reports.length < 2 ? (
        <EmptyState
          title="Two perspectives to compare"
          description="Complete at least two simulations to see how their scores and concerns differ."
        >
          <ButtonLink href="/simulate">Run a simulation</ButtonLink>
        </EmptyState>
      ) : (
        <>
          <div className="comparison-selects">
            <Field label="First simulation">
              <select
                value={left?.id || ""}
                onChange={(e) => setLeft(e.target.value)}
              >
                {reports.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.title} — {dateLabel(r.createdAt)} · {r.id.slice(0, 8)}
                  </option>
                ))}
              </select>
            </Field>
            <span className="compare-divider">
              <Icon name="compare" size={23} />
            </span>
            <Field label="Second simulation">
              <select
                value={right?.id || ""}
                onChange={(e) => setRight(e.target.value)}
              >
                {reports.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.title} — {dateLabel(r.createdAt)} · {r.id.slice(0, 8)}
                  </option>
                ))}
              </select>
            </Field>
          </div>
          {same ? (
            <Notice tone="warning">
              Choose two different simulations to compare their results.
            </Notice>
          ) : (
            left &&
            right && (
              <>
                <Notice>
                  For a useful before-and-after comparison, use the same product
                  and personas. Changes in products or audience can also change
                  the scores.
                </Notice>
                <div className="comparison-headers">
                  {[left, right].map((r, i) => (
                    <section className="panel comparison-card" key={r.id}>
                      <div>
                        <Badge tone={i === 1 ? "blue" : "neutral"}>
                          {i === 0 ? "First simulation" : "Second simulation"}
                        </Badge>
                        <h2>{r.title}</h2>
                        <p>
                          {r.post.platform} · {r.reactions.length} personas
                        </p>
                        <Link href={`/reports/${r.id}`} className="text-link">
                          Open full report <Icon name="arrow" size={14} />
                        </Link>
                      </div>
                      <ScoreRing score={overall(r)} />
                    </section>
                  ))}
                </div>
                <section className="panel comparison-table">
                  <div className="panel-heading">
                    <div>
                      <h2>A closer look at the scores</h2>
                      <p>
                        Sample averages across completed persona evaluations.
                      </p>
                    </div>
                  </div>
                  <table>
                    <thead>
                      <tr>
                        <th>Dimension</th>
                        <th>First</th>
                        <th>Second</th>
                        <th>Change</th>
                      </tr>
                    </thead>
                    <tbody>
                      {dimensions.map((d, i) => {
                        const diff = overall(right, i) - overall(left, i);
                        return (
                          <tr key={d}>
                            <td>{d}</td>
                            <td>
                              {overall(left, i)}
                              <span className="muted">/100</span>
                            </td>
                            <td>
                              {overall(right, i)}
                              <span className="muted">/100</span>
                            </td>
                            <td>
                              <Badge
                                tone={
                                  diff > 0
                                    ? "green"
                                    : diff < 0
                                      ? "amber"
                                      : "neutral"
                                }
                              >
                                {diff > 0 ? "+" : ""}
                                {diff} points
                              </Badge>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </section>
                <div className="comparison-headers">
                  {[left, right].map((r) => (
                    <section className="panel comparison-caption" key={r.id}>
                      <h3>{r.post.headline}</h3>
                      <p>{r.post.body}</p>
                    </section>
                  ))}
                </div>
              </>
            )
          )}
        </>
      )}
    </>
  );
}
