"use client";

import { useEffect, useState } from "react";
import { useReducedMotion } from "@/lib/browser-preferences";

// One clock per overview keeps all values and the score arc in sync. Values
// stay live when local workspace data hydrates or changes during the animation.
export function useCountUpProgress(duration = 1300) {
  const reducedMotion = useReducedMotion();
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    if (reducedMotion) return;
    let frame: number;
    const started = performance.now();
    const animate = (now: number) => {
      const elapsed = Math.min(1, (now - started) / Math.max(1, duration));
      setProgress(1 - Math.pow(1 - elapsed, 3));
      if (elapsed < 1) frame = requestAnimationFrame(animate);
    };
    frame = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frame);
  }, [duration, reducedMotion]);

  return reducedMotion ? 1 : progress;
}

export function CountUp({
  value,
  progress = 1,
  padStart = 0,
}: {
  value: number;
  progress?: number;
  padStart?: number;
}) {
  const final = String(value).padStart(padStart, "0");
  const displayed = String(
    Math.round(value * Math.min(1, Math.max(0, progress))),
  ).padStart(padStart, "0");
  return (
    <span
      style={{
        display: "inline-block",
        minWidth: `${final.length}ch`,
        fontVariantNumeric: "tabular-nums",
      }}
    >
      <span aria-hidden="true">{displayed}</span>
      <span className="sr-only">{final}</span>
    </span>
  );
}
