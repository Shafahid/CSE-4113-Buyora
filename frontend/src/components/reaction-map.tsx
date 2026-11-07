"use client";

import {
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  type PointerEvent,
} from "react";
import { Reaction, initialState } from "@/lib/demo-data";
import {
  createSpread,
  FINAL_TICK,
  likelyActions,
  reactionStates,
  spreadSummary,
  stateLabels,
  viewerState,
  type ViewerState,
} from "@/lib/spread-simulation";
import { Avatar, Badge, EmptyState, Icon } from "./ui";
import styles from "./reaction-map.module.css";
import { advancePlayback, playbackDelay } from "@/lib/spread-playback";
import { usePageVisible, useReducedMotion } from "@/lib/browser-preferences";

export function ReactionMap({
  reactions = initialState.reports[0].reactions,
  compact = false,
}: {
  reactions?: Reaction[];
  compact?: boolean;
}) {
  const spread = useMemo(() => createSpread(reactions), [reactions]);
  const [playback, setPlayback] = useState({
    tick: 0,
    playing: compact,
    speed: 1,
  });
  const [selectedId, setSelectedId] = useState("v-01");
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [filter, setFilter] = useState<ViewerState | null>(null);
  const [view, setView] = useState({ zoom: 1, x: 0, y: 0 });
  const [dragging, setDragging] = useState(false);
  const drag = useRef<{
    clientX: number;
    clientY: number;
    x: number;
    y: number;
  } | null>(null);
  const svg = useRef<SVGSVGElement>(null);
  const unique = useId().replaceAll(":", "");
  const reducedMotion = useReducedMotion();
  const pageVisible = usePageVisible();
  const [motionEnabled, setMotionEnabled] = useState(false);
  const { tick, speed } = playback;
  const autoplayAllowed = !reducedMotion || motionEnabled;
  const playing =
    playback.playing && pageVisible && (!compact || autoplayAllowed);
  const summary = spreadSummary(spread, tick);
  const selected =
    spread.viewers.find((v) => v.id === selectedId) || spread.viewers[0];
  const spotlight = spread.viewers.find(
    (v) => v.id === (hoveredId || selectedId),
  );
  const currentState = selected ? viewerState(selected, tick) : "unreached";
  const events = spread.viewers
    .flatMap((v) => [
      {
        viewer: v,
        at: v.reachedAt,
        message: "sees the post",
        state: "viewing" as ViewerState,
      },
      {
        viewer: v,
        at: v.resolvedAt,
        message: stateLabels[v.outcome].toLowerCase(),
        state: v.outcome as ViewerState,
      },
    ])
    .filter((e) => e.at <= tick)
    .sort((a, b) => b.at - a.at || a.viewer.id.localeCompare(b.viewer.id))
    .slice(0, 3);

  useEffect(() => {
    if (!playing) return;
    const timer = setTimeout(
      () => setPlayback((p) => advancePlayback(p, FINAL_TICK, compact)),
      playbackDelay({ tick, playing, speed }, FINAL_TICK, compact),
    );
    return () => clearTimeout(timer);
  }, [playing, tick, speed, compact]);

  function playPause() {
    setPlayback((p) => ({
      ...p,
      tick: p.tick >= FINAL_TICK ? 0 : p.tick,
      playing: !p.playing,
    }));
  }
  function replay() {
    setPlayback((p) => ({ ...p, tick: 0, playing: true }));
  }
  function changeZoom(amount: number) {
    setView((v) => ({
      ...v,
      zoom: Math.max(
        0.6,
        Math.min(2.4, Math.round((v.zoom + amount) * 10) / 10),
      ),
    }));
  }
  function startPan(e: PointerEvent<SVGSVGElement>) {
    if (
      e.button !== 0 ||
      (e.target instanceof Element && e.target.closest("[data-viewer]"))
    )
      return;
    drag.current = {
      clientX: e.clientX,
      clientY: e.clientY,
      x: view.x,
      y: view.y,
    };
    e.currentTarget.setPointerCapture(e.pointerId);
    setDragging(true);
  }
  function pan(e: PointerEvent<SVGSVGElement>) {
    if (!drag.current) return;
    const ratio = 720 / e.currentTarget.getBoundingClientRect().width;
    const start = drag.current;
    setView((v) => ({
      ...v,
      x: Math.max(
        -600,
        Math.min(600, start.x + (e.clientX - start.clientX) * ratio),
      ),
      y: Math.max(
        -400,
        Math.min(400, start.y + (e.clientY - start.clientY) * ratio),
      ),
    }));
  }
  function endPan(e: PointerEvent<SVGSVGElement>) {
    drag.current = null;
    setDragging(false);
    if (e.currentTarget.hasPointerCapture(e.pointerId))
      e.currentTarget.releasePointerCapture(e.pointerId);
  }
  function focusViewer(index: number) {
    const viewer =
      spread.viewers[(index + spread.viewers.length) % spread.viewers.length];
    setSelectedId(viewer.id);
    svg.current
      ?.querySelector<SVGGElement>(`[data-viewer="${viewer.id}"]`)
      ?.focus();
  }

  if (!selected)
    return (
      <EmptyState
        title="No completed perspectives to simulate"
        description="Retry a persona evaluation in Audience insights, then return to the spread simulation."
      />
    );
  const comment =
    currentState === "unreached"
      ? "This viewer has not seen the post yet. Play the simulation or move the timeline forward."
      : currentState === "viewing"
        ? "This viewer is reading the post. Their sample reaction will appear as the simulation advances."
        : currentState === "ignored"
          ? "This post doesn’t feel relevant enough to stop scrolling."
          : currentState === "drop-off"
            ? "I still have a few questions. I’ll leave this for now."
            : currentState === "inboxed"
              ? "I’d like to know more. I’ll message the seller."
              : selected.reaction.comment;
  const reason =
    currentState === "unreached" || currentState === "viewing"
      ? "A reaction is only shown after this fictional viewer encounters the post."
      : currentState === "ignored"
        ? "This illustrative viewer continues scrolling. Not every person who encounters a post will engage."
        : currentState === "drop-off"
          ? "Unanswered details create hesitation in this example. The viewer leaves before starting a conversation."
          : selected.reaction.reason;

  return (
    <section
      className={`${styles.shell} ${compact ? styles.compact : ""} ${playing ? styles.running : ""}`}
      aria-label="Buyer spread simulation"
    >
      <div className={styles.layout}>
        <div className={styles.main}>
          <div className={styles.toolbar}>
            <div
              className={styles.zoomControls}
              role="group"
              aria-label="Graph view controls"
            >
              <button
                aria-label="Zoom out"
                disabled={view.zoom <= 0.6}
                onClick={() => changeZoom(-0.2)}
              >
                −
              </button>
              <span>{Math.round(view.zoom * 100)}%</span>
              <button
                aria-label="Zoom in"
                disabled={view.zoom >= 2.4}
                onClick={() => changeZoom(0.2)}
              >
                +
              </button>
              <button
                className={styles.resetView}
                onClick={() => setView({ zoom: 1, x: 0, y: 0 })}
              >
                Reset view
              </button>
            </div>
            <Badge tone="blue">{spread.viewers.length} fictional viewers</Badge>
          </div>
          <div className={styles.stage}>
            <svg
              ref={svg}
              viewBox="0 0 720 460"
              role="group"
              aria-label="Interactive spread graph. Use arrow keys to select viewers; drag the background to pan."
              className={dragging ? styles.dragging : ""}
              onPointerDown={startPan}
              onPointerMove={pan}
              onPointerUp={endPan}
              onPointerCancel={endPan}
            >
              <defs>
                <radialGradient id={`spread-glow-${unique}`}>
                  <stop stopColor="var(--accent-bg)" stopOpacity=".8" />
                  <stop offset="1" stopColor="var(--surface)" stopOpacity="0" />
                </radialGradient>
                <marker
                  id={`spread-arrow-${unique}`}
                  viewBox="0 0 10 10"
                  refX="14"
                  refY="5"
                  markerWidth="5"
                  markerHeight="5"
                  orient="auto-start-reverse"
                >
                  <path
                    d="M0 1 9 5 0 9"
                    fill="none"
                    stroke="var(--accent)"
                    strokeWidth="1.4"
                  />
                </marker>
              </defs>
              <rect width="720" height="460" fill="transparent" />
              <g
                transform={`translate(${360 + view.x} ${225 + view.y}) scale(${view.zoom}) translate(-360 -225)`}
              >
                <ellipse
                  cx="360"
                  cy="225"
                  rx="300"
                  ry="200"
                  fill={`url(#spread-glow-${unique})`}
                  pointerEvents="none"
                />
                {spread.viewers.map((v) => {
                  const parent = spread.viewers.find((p) => p.id === v.parent);
                  const reached = tick >= v.reachedAt;
                  const transmitting = reached && tick < v.reachedAt + 2;
                  return (
                    <path
                      key={`edge-${v.id}`}
                      d={`M${parent?.x ?? 360} ${parent?.y ?? 225} L${v.x} ${v.y}`}
                      className={`${styles.edge} ${reached ? styles.reached : ""} ${transmitting ? styles.transmitting : ""} ${selected.id === v.id ? styles.selectedEdge : ""}`}
                      markerEnd={
                        reached ? `url(#spread-arrow-${unique})` : undefined
                      }
                    />
                  );
                })}
                <g className={styles.source} pointerEvents="none">
                  <circle
                    cx="360"
                    cy="225"
                    r="32"
                    className={styles.sourceHalo}
                  />
                  <circle cx="360" cy="225" r="23" />
                  <path
                    d="M350 224h20m-20 5h13m-13-10h20"
                    fill="none"
                    stroke="var(--button-text)"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                  />
                  <rect x="321" y="259" width="78" height="19" rx="5" />
                  <text x="360" y="272" textAnchor="middle">
                    Your post
                  </text>
                </g>
                {spread.viewers.map((v, index) => {
                  const state = viewerState(v, tick);
                  const isSelected = selected.id === v.id;
                  const dimmed = filter && filter !== state;
                  return (
                    <g
                      key={v.id}
                      data-viewer={v.id}
                      data-state={state}
                      className={`${styles.viewer} ${isSelected ? styles.selected : ""} ${dimmed ? styles.dimmed : ""}`}
                      role="button"
                      tabIndex={isSelected ? 0 : -1}
                      aria-label={`${v.id}, ${v.reaction.persona.role}, ${stateLabels[state]}, round ${v.round}`}
                      aria-pressed={isSelected}
                      onClick={() => setSelectedId(v.id)}
                      onFocus={() => setSelectedId(v.id)}
                      onPointerEnter={() => setHoveredId(v.id)}
                      onPointerLeave={() => setHoveredId(null)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          setSelectedId(v.id);
                        } else if (
                          [
                            "ArrowRight",
                            "ArrowDown",
                            "ArrowLeft",
                            "ArrowUp",
                          ].includes(e.key)
                        ) {
                          e.preventDefault();
                          focusViewer(
                            index +
                              (["ArrowRight", "ArrowDown"].includes(e.key)
                                ? 1
                                : -1),
                          );
                        } else if (e.key === "+" || e.key === "=") {
                          e.preventDefault();
                          changeZoom(0.2);
                        } else if (e.key === "-") {
                          e.preventDefault();
                          changeZoom(-0.2);
                        } else if (e.key === "Home") {
                          e.preventDefault();
                          setView({ zoom: 1, x: 0, y: 0 });
                        }
                      }}
                    >
                      <title>
                        {`${v.id} · ${v.reaction.persona.role} · ${stateLabels[state]}`}
                      </title>
                      <circle
                        className={styles.hitArea}
                        cx={v.x}
                        cy={v.y}
                        r="14"
                      />
                      {state === "viewing" && (
                        <circle
                          className={styles.exposurePulse}
                          cx={v.x}
                          cy={v.y}
                          r="13"
                        />
                      )}
                      <circle
                        className={styles.selectionHalo}
                        cx={v.x}
                        cy={v.y}
                        r="13"
                      />
                      <circle
                        className={styles.dot}
                        cx={v.x}
                        cy={v.y}
                        r={isSelected ? 8 : 6.5}
                      />
                      {state === "inboxed" && (
                        <path
                          d={`m${v.x - 3} ${v.y} 2 2 4-4`}
                          fill="none"
                          stroke="var(--surface)"
                          strokeWidth="1.4"
                          strokeLinecap="round"
                        />
                      )}
                    </g>
                  );
                })}
                {spotlight &&
                  (() => {
                    const role = spotlight.reaction.persona.role;
                    const label =
                      role.length > 30 ? `${role.slice(0, 29)}…` : role;
                    const width = Math.min(240, 30 + label.length * 7.15);
                    const x =
                      spotlight.x > 440
                        ? spotlight.x - width - 17
                        : spotlight.x + 17;
                    return (
                      <g className={styles.nodeLabel} pointerEvents="none">
                        <rect
                          x={x}
                          y={spotlight.y - 13}
                          width={width}
                          height="26"
                          rx="6"
                        />
                        <text x={x + 10} y={spotlight.y + 4}>
                          {label}
                        </text>
                      </g>
                    );
                  })()}
              </g>
            </svg>
            <div className={styles.stageFooter}>
              <span className={styles.dragHint}>
                Drag to pan · + / − to zoom
              </span>
              <span
                className={`${styles.reachBadge} ${summary.complete ? styles.complete : ""}`}
              >
                {summary.complete
                  ? "Simulation complete"
                  : tick === 0
                    ? "Ready to simulate"
                    : playing
                      ? "Simulation running"
                      : "Simulation paused"}{" "}
                · {summary.reached}/{spread.viewers.length} reached
              </span>
            </div>
          </div>
          {compact ? (
            <div className={styles.autoPlayback}>
              <span>
                {!autoplayAllowed
                  ? "Reduced motion enabled"
                  : !playing
                    ? "Animation paused"
                    : summary.complete
                      ? "Next simulation in 2 seconds"
                      : `Auto-playing · Round ${summary.round} / 3`}
              </span>
              <button
                onClick={() => {
                  if (!autoplayAllowed) {
                    setMotionEnabled(true);
                    setPlayback((p) => ({ ...p, playing: true }));
                  } else setPlayback((p) => ({ ...p, playing: !p.playing }));
                }}
              >
                {!autoplayAllowed
                  ? "Enable animation"
                  : playback.playing
                    ? "Pause animation"
                    : "Resume animation"}
              </button>
            </div>
          ) : (
            <div className={styles.playback}>
              <div className={styles.playbackTop}>
                <div className={styles.playButtons}>
                  <button
                    className={styles.playButton}
                    onClick={playPause}
                    aria-label={
                      playing
                        ? "Pause spread simulation"
                        : summary.complete
                          ? "Replay spread simulation"
                          : tick === 0
                            ? "Play spread simulation"
                            : "Resume spread simulation"
                    }
                  >
                    {playing ? (
                      <span className={styles.pauseIcon} aria-hidden="true">
                        Ⅱ
                      </span>
                    ) : (
                      <Icon
                        name={summary.complete ? "refresh" : "play"}
                        size={14}
                      />
                    )}
                    {playing
                      ? "Pause"
                      : summary.complete
                        ? "Replay"
                        : tick === 0
                          ? "Play simulation"
                          : "Resume"}
                  </button>
                  <button
                    className={styles.smallButton}
                    onClick={replay}
                    disabled={tick === 0}
                    aria-label="Restart spread simulation"
                  >
                    <Icon name="refresh" size={14} />
                  </button>
                  <button
                    className={styles.smallButton}
                    disabled={summary.complete}
                    onClick={() =>
                      setPlayback((p) => ({
                        ...p,
                        tick: Math.min(FINAL_TICK, p.tick + 1),
                        playing: false,
                      }))
                    }
                    aria-label="Advance simulation one step"
                  >
                    <Icon name="chevron" size={15} />
                  </button>
                </div>
                <span
                  className={styles.roundLabel}
                  role="status"
                  aria-live="polite"
                >
                  {tick === 0
                    ? "3 rounds to explore"
                    : `Round ${summary.round} / 3 · ${summary.complete ? "Complete" : playing ? "Playing" : "Paused"}`}
                </span>
                <label className={styles.speed}>
                  <span className="sr-only">Simulation playback speed</span>
                  <select
                    aria-label="Simulation playback speed"
                    value={speed}
                    onChange={(e) =>
                      setPlayback((p) => ({
                        ...p,
                        speed: Number(e.target.value),
                      }))
                    }
                  >
                    <option value={0.5}>0.5×</option>
                    <option value={1}>1×</option>
                    <option value={2}>2×</option>
                  </select>
                </label>
              </div>
              <label className={styles.timeline}>
                <span className="sr-only">Simulation timeline</span>
                <input
                  type="range"
                  min="0"
                  max={FINAL_TICK}
                  step="1"
                  value={tick}
                  aria-label="Simulation timeline"
                  aria-valuetext={`Step ${tick} of ${FINAL_TICK}, ${summary.reached} viewers reached`}
                  onChange={(e) =>
                    setPlayback((p) => ({
                      ...p,
                      tick: Number(e.target.value),
                      playing: false,
                    }))
                  }
                />
                <span className={styles.roundTicks}>
                  <span>Start</span>
                  <span>Round 1</span>
                  <span>Round 2</span>
                  <span>Round 3</span>
                </span>
              </label>
            </div>
          )}
        </div>
        {!compact && (
          <aside
            className={styles.inspector}
            aria-label="Selected viewer inspector"
          >
            <div className="section-kicker">Persona inspector</div>
            <div className={styles.inspectorProfile}>
              <Avatar persona={selected.reaction.persona} />
              <div>
                <h3>{selected.reaction.persona.role}</h3>
                <p>{selected.reaction.persona.name}’s sample perspective</p>
              </div>
            </div>
            <dl className={styles.inspectorFacts}>
              <div>
                <dt>Viewer ID</dt>
                <dd>
                  {selected.id} <span>· Round {selected.round}</span>
                </dd>
              </div>
              <div>
                <dt>Reaction type</dt>
                <dd>
                  <span className={styles.stateBadge} data-state={currentState}>
                    <i />
                    {stateLabels[currentState]}
                  </span>
                </dd>
              </div>
              <div>
                <dt>Comment</dt>
                <dd
                  className={styles.comment}
                  lang={
                    currentState === "engaged" || currentState === "objection"
                      ? undefined
                      : "en"
                  }
                >
                  “{comment}”
                </dd>
              </div>
              <div>
                <dt>Why this reaction?</dt>
                <dd>{reason}</dd>
              </div>
              <div>
                <dt>Likely action in this demo</dt>
                <dd className={styles.action}>{likelyActions[currentState]}</dd>
              </div>
            </dl>
            <div className={styles.viewerNavigation}>
              <button
                aria-label="Inspect previous viewer"
                onClick={() =>
                  setSelectedId(
                    spread.viewers[(spread.viewers.indexOf(selected) + 59) % 60]
                      .id,
                  )
                }
              >
                <Icon name="back" size={14} />
                Previous
              </button>
              <button
                aria-label="Inspect next viewer"
                onClick={() =>
                  setSelectedId(
                    spread.viewers[(spread.viewers.indexOf(selected) + 1) % 60]
                      .id,
                  )
                }
              >
                Next
                <Icon name="arrow" size={14} />
              </button>
            </div>
          </aside>
        )}
      </div>
      <div
        className={styles.legend}
        role="group"
        aria-label="Highlight viewers by reaction"
      >
        <button
          className={!filter ? styles.activeFilter : ""}
          aria-pressed={!filter}
          onClick={() => setFilter(null)}
        >
          All viewers <strong>{spread.viewers.length}</strong>
        </button>
        {reactionStates.map((state) => (
          <button
            key={state}
            className={filter === state ? styles.activeFilter : ""}
            data-state={state}
            aria-pressed={filter === state}
            onClick={() => setFilter(filter === state ? null : state)}
          >
            <i />
            {stateLabels[state]}
            <strong>{summary.counts[state]}</strong>
          </button>
        ))}
        <span className={styles.waitingCount}>
          {summary.counts.unreached} not reached · {summary.counts.viewing}{" "}
          viewing
        </span>
      </div>
      {!compact && (
        <div className={styles.activity}>
          <span className={styles.activityTitle}>
            <Icon name="history" size={14} />
            Simulation activity
          </span>
          {events.length ? (
            events.map((event) => (
              <button
                key={`${event.viewer.id}-${event.at}`}
                onClick={() => setSelectedId(event.viewer.id)}
              >
                <i data-state={event.state} />
                <strong>{event.viewer.id}</strong>
                <span>
                  {event.viewer.reaction.persona.role} · {event.message}
                </span>
              </button>
            ))
          ) : (
            <p>
              Press play to watch the post move through three rounds of
              fictional buyer reactions.
            </p>
          )}
        </div>
      )}
      <p className={styles.disclosure}>
        <Icon name="info" size={12} />
        Illustrative spread using{" "}
        {reactions.filter((r) => r.status === "complete").length} completed
        persona perspectives. Viewers, connections, and actions are simulated;
        they do not predict real reach or sales.
      </p>
    </section>
  );
}
