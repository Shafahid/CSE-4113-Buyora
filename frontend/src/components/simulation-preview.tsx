"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import type { Draft } from "@/lib/demo-data";
import type { ApiSchemas } from "@/lib/api-schema";
import { postToApi } from "@/lib/api-adapters";
import { ApiError } from "@/lib/api-client";
import { simulationApi } from "@/lib/simulation-api";
import { Notice } from "./ui";

export function SimulationPreview({ draft }: { draft: Draft }) {
  const [result, setResult] = useState<{ key: string; preview?: ApiSchemas["PreviewResponse"]; error?: boolean } | null>(null);
  const [retry, setRetry] = useState(0);
  const key = JSON.stringify({ product_id: Number(draft.productId), post_version_id: Number(draft.post.latestVersionId),
    post: postToApi(draft.post), audience: draft.audience, language: draft.language, personas: draft.personas });
  const eligible = !!draft.post.latestVersionId && draft.personas.length >= 2;
  useEffect(() => {
    if (!eligible) return;
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        const preview = await simulationApi.preview({ ...JSON.parse(key), request_id: crypto.randomUUID() }, controller.signal);
        if (!controller.signal.aborted) setResult({ key, preview });
      } catch (error) {
        if (!controller.signal.aborted) setResult(error instanceof ApiError && error.status === 404
          ? { key, preview: { match: false } } : { key, error: true });
      }
    }, 450);
    return () => { clearTimeout(timer); controller.abort(); };
  }, [key, eligible, retry]);
  const current = result?.key === key ? result : null;
  if (draft.personas.length < 2) return <Notice>Select at least two buyer personas to check for saved results.</Notice>;
  if (!eligible) return <Notice>This post will be saved before checking for matching results. A new assessment makes model requests.</Notice>;
  if (!current) return <Notice><span role="status">Checking your saved simulations…</span></Notice>;
  if (current.error) return <Notice tone="warning">We couldn’t check saved results. The server will check again when you start. <button className="text-link" onClick={() => setRetry((value) => value + 1)}>Check again</button></Notice>;
  const preview = current.preview;
  if (!preview?.match) return <Notice>No saved simulation matches these inputs. Starting will create a new assessment and make model requests.</Notice>;
  const finished = ["completed", "partially_failed", "failed"].includes(preview.status ?? "");
  return <Notice>
    <strong>A matching simulation is saved.</strong> {preview.completed} of {preview.total} perspectives completed
    {preview.created_at ? ` · ${new Date(preview.created_at).toLocaleDateString()}` : ""}.
    {draft.fresh ? " You selected a fresh simulation, so starting will make new model requests and keep this report. "
      : " Starting will reuse this run without new model requests. "}
    <Link href={finished ? `/reports/${preview.run_id}` : `/simulate?run=${preview.run_id}`}>{finished ? "Open saved report" : "Resume saved run"}</Link>
  </Notice>;
}
