"use client";
import { useEffect, useRef, useState } from "react";
import type { Draft, Product } from "@/lib/demo-data";
import { ApiError, errorMessage } from "@/lib/api-client";
import { applyAdaptedPersonas, personaInputSignature } from "@/lib/persona-adaptation";
import { refreshPersonaAdaptation, requestPersonaAdaptation, savePost, updateDemo } from "@/lib/store";
import { Notice } from "./ui";

export function PersonaAdaptation({ draft, product, maxPersonas, onBusy }: { draft: Draft; product?: Product; maxPersonas: number; onBusy: (busy: boolean) => void }) {
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [fresh, setFresh] = useState(false);
  const [saving, setSaving] = useState(false);
  const [pollKey, setPollKey] = useState(0);
  const savingRef = useRef(false);
  const signature = personaInputSignature(draft, product);
  const pending = draft.personaAdaptation;
  const active = pending?.signature === signature;
  useEffect(() => {
    onBusy(!!active || saving);
    return () => onBusy(false);
  }, [active, saving, onBusy]);
  useEffect(() => {
    if (!pending || pending.signature !== signature) return;
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout>;
    const controller = new AbortController();
    async function work() {
      try {
        let result;
        if (pending!.jobId) {
          result = await refreshPersonaAdaptation(pending!.jobId, controller.signal);
        } else {
          const snapshot = structuredClone(draft);
          result = await requestPersonaAdaptation({
            request_id: pending!.requestId, post_version_id: Number(snapshot.post.latestVersionId),
            audience: snapshot.audience, language: snapshot.language, personas: snapshot.personas,
            mode: pending!.mode, fresh: pending!.fresh,
          });
          if (cancelled) return;
        }
        if (cancelled) return;
        if (["completed", "fallback"].includes(result.status)) {
          updateDemo((state) => ({ ...state, draft: applyAdaptedPersonas(state.draft, result.profiles, signature, state.products.find((p) => p.id === state.draft.productId)) }));
          setError("");
          setMessage(result.source === "fallback" ? "AI variants were unavailable. Contextual templates were applied; your custom priorities were preserved." : result.cache_hit ? "Saved persona variants applied. No new model request was made." : result.source === "context" ? "Selected profiles now include your product and audience context. Catalog descriptions follow your chosen language; custom text is preserved." : "AI variants applied to your selected buyers. Review their priorities before running.");
        } else {
          setMessage("Generating buyer variants. This job is saved; you can return to this draft while it processes.");
          setError("");
          if (!pending!.jobId) {
            updateDemo((state) => state.draft.personaAdaptation?.requestId === pending!.requestId ? { ...state, draft: { ...state.draft, personaAdaptation: { ...pending!, jobId: result.id } } } : state);
          } else timer = setTimeout(work, 1500);
        }
      } catch (error) {
        if (cancelled) return;
        if (error instanceof ApiError && [400, 401, 403, 404, 409, 422].includes(error.status ?? 0)) {
          setError(`${errorMessage(error)} Update the draft or stop waiting before trying again.`);
          return;
        }
        setError(`${errorMessage(error)} Your request is saved; checking again…`);
        timer = setTimeout(work, 5000);
      }
    }
    void work();
    return () => { cancelled = true; controller.abort(); clearTimeout(timer); };
    // Capture the draft that belongs to this operation; input edits cancel it.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pending?.requestId, pending?.jobId, signature, pollKey]);

  async function start(mode: "context" | "ai") {
    if (savingRef.current) return;
    savingRef.current = true; setSaving(true);
    setError(""); setMessage(mode === "ai" ? "Saving your post and queuing persona generation…" : "Adapting your selected profiles…");
    try {
      const saved = await savePost(structuredClone(draft.post));
      updateDemo((state) => {
        const currentProduct = state.products.find((p) => p.id === state.draft.productId);
        if (personaInputSignature(state.draft, currentProduct) !== signature) return state;
        const next = { ...state.draft, post: saved };
        return { ...state, draft: { ...next, personaAdaptation: { requestId: crypto.randomUUID(), signature: personaInputSignature(next, currentProduct), mode, fresh: mode === "ai" && fresh } } };
      });
    } catch (error) { setMessage(""); setError(errorMessage(error)); }
    finally { savingRef.current = false; setSaving(false); }
  }
  const invalid = saving || !product || draft.personas.length < 2 || draft.personas.length > maxPersonas;
  return <div className="persona-adaptation">
    <h3>Tailor the selected buyers</h3>
    <p className="muted">Use product and audience context, or generate distinct AI variants. You can edit the results before evaluation.</p>
    <div className="row wrap">
      <button className="button secondary small-button" disabled={invalid || active} onClick={() => start("context")}>Adapt / translate templates</button>
      <button className="button secondary small-button" disabled={invalid || active} onClick={() => start("ai")}>{active ? "Processing selected profiles…" : "Generate AI variants"}</button>
    </div>
    <label className="row persona-fresh"><input type="checkbox" checked={fresh} disabled={!!active} onChange={(e) => setFresh(e.target.checked)} /> Generate fresh variants instead of reusing saved matches</label>
    {(error || message) && <div role="status" aria-live="polite"><Notice tone={error ? "warning" : undefined}>{error || message}</Notice></div>}
    {error && active && <button className="text-link" onClick={() => setPollKey((key) => key + 1)}>Check again</button>}
    {pending && !active && <p className="quiet-note">Inputs changed. The earlier job will not overwrite your edits.</p>}
    {active && <button className="text-button" onClick={() => { updateDemo((state) => ({ ...state, draft: { ...state.draft, personaAdaptation: undefined } })); setMessage("Stopped waiting. Any queued job remains saved on the server."); }}>Stop waiting</button>}
  </div>;
}
