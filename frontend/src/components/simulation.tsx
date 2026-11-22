"use client";
import { useEffect, useRef, useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Audience,
  Draft,
  Persona,
  Post,
  initialDraft,
  money,
  personas as templates,
  uid,
} from "@/lib/demo-data";
import { updateDemo, useWorkspace, savePost, startSimulation } from "@/lib/store";
import { simulationApi, finishedRun } from "@/lib/simulation-api";
import { errorMessage } from "@/lib/api-client";
import { postError, simulationError } from "@/lib/workflow";
import { personaChoices, setPersonaSelected } from "@/lib/persona-selection";
import {
  Avatar,
  Badge,
  EmptyState,
  Field,
  Icon,
  Modal,
  Notice,
  PageHeading,
  ProductArt,
  useToast,
} from "./ui";

import { SimulationProgress } from "./simulation-progress";
import { SimulationPreview } from "./simulation-preview";

const steps = ["Product & post", "Your audience", "Buyer personas"];
export function Simulation({ initialRunId }: { initialRunId?: string }) {
  const { data: state, error: storageError } = useWorkspace();
  const { draft } = state;
  const product = state.products.find(
    (p) => p.id === draft.productId && !p.archived,
  );
  const [editing, setEditing] = useState<Persona | null>(null);
  const [error, setError] = useState("");
  const [runId, setRunId] = useState(initialRunId ?? "");
  const [preparing, setPreparing] = useState(false);
  const submitting = useRef(false);
  const [options, setOptions] = useState<{ max_personas: number; profiles: Persona[] } | null>(null);
  const [optionsError, setOptionsError] = useState("");
  const catalog = options?.profiles ?? templates;
  const choices = personaChoices(draft, catalog);
  const maxPersonas = options?.max_personas ?? 12;
  const selectionFull = draft.personas.length >= maxPersonas;
  const router = useRouter();
  const toast = useToast();
  useEffect(() => {
    let active = true;
    simulationApi.options().then((value) => { if (active) setOptions(value); })
      .catch((error) => { if (active) setOptionsError(errorMessage(error)); });
    return () => { active = false; };
  }, []);
  const patch = (value: Partial<Draft>) =>
    updateDemo((s) => ({ ...s, draft: { ...s.draft, ...value } }));
  const postPatch = (value: Partial<Post>) =>
    patch({ post: { ...draft.post, ...value } });
  const audiencePatch = (value: Partial<Audience>) =>
    patch({ audience: { ...draft.audience, ...value } });
  function chooseProduct(id: string) {
    const p = state.products.find((p) => p.id === id);
    const post = state.posts.find((p) => p.productId === id);
    patch({
      productId: id,
      post: post
        ? structuredClone(post)
        : {
            ...initialDraft.post,
            id: uid(),
            productId: id,
            headline: p?.name || "",
            body: p?.description || "",
            versions: [],
          },
    });
  }
  function next() {
    const invalid = draft.step === 0 ? postError(draft, product) : "";
    if (invalid) {
      setError(invalid);
      return;
    }
    setError("");
    patch({ step: Math.min(2, draft.step + 1) });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }
  async function start() {
    if (submitting.current) return;
    const invalid = simulationError(draft, product, maxPersonas);
    if (invalid || !product) {
      setError(invalid);
      return;
    }
    submitting.current = true;
    setPreparing(true); setError("");
    const snapshot = structuredClone(draft);
    try {
      snapshot.post = await savePost(snapshot.post);
      const signature = JSON.stringify({ postVersion: snapshot.post.latestVersionId, audience: snapshot.audience, personas: snapshot.personas, language: snapshot.language, fresh: !!snapshot.fresh });
      const requestId = snapshot.requestSignature === signature && snapshot.runRequestId
        ? snapshot.runRequestId : crypto.randomUUID();
      patch({ post: snapshot.post, requestSignature: signature, runRequestId: requestId });
      const run = await startSimulation({
        request_id: requestId, post_version_id: Number(snapshot.post.latestVersionId),
        audience: snapshot.audience, personas: snapshot.personas,
        language: snapshot.language, fresh: !!snapshot.fresh,
      });
      patch({ activeRunId: run.id, runRequestId: undefined, requestSignature: undefined });
      if (run.cache_hit) toast("Saved simulation reused. No new model requests were made.");
      if (finishedRun(run)) router.push(`/reports/${run.id}`);
      else { setRunId(run.id); router.replace(`/simulate?run=${run.id}`); }
    } catch (error) { setError(errorMessage(error)); }
    finally { submitting.current = false; setPreparing(false); }
  }
  if (runId) return <SimulationProgress id={runId} onBack={() => { setRunId(""); router.replace("/simulate"); }} />;
  return (
    <>
      <PageHeading
        eyebrow="Run simulation"
        title="A second perspective starts here."
        description="Bring your product post. Let different buyers take a look."
      >
        <span className="saved-label">
          <Icon name="check" size={14} />
          {storageError
            ? "Draft kept for this session only"
            : "Draft saved in this browser"}
        </span>
      </PageHeading>
      {optionsError && <Notice tone="warning">Persona options could not load: {optionsError} Reload this page to try again.</Notice>}
      {draft.activeRunId && <Notice>Your last simulation is saved. <Link href={`/simulate?run=${draft.activeRunId}`}>Resume or open its report</Link>.</Notice>}
      <div className="wizard-steps" aria-label="Simulation steps">
        {steps.map((s, i) => (
          <div
            key={s}
            className={`wizard-step ${i === draft.step ? "current" : i < draft.step ? "done" : ""}`}
            aria-current={i === draft.step ? "step" : undefined}
          >
            <span>
              {i < draft.step ? <Icon name="check" size={14} /> : i + 1}
            </span>
            <div>
              <small>Step {i + 1}</small>
              <strong>{s}</strong>
            </div>
            {i !== 2 && <div className="step-connector" />}
          </div>
        ))}
      </div>
      <div className="simulation-layout">
        <section className="panel simulation-form">
          <div className="form-section-heading">
            <span className="small-icon">
              <Icon name={["file", "people", "spark"][draft.step]} size={21} />
            </span>
            <div>
              <h2>
                {
                  [
                    "Tell us about your post",
                    "Who do you have in mind?",
                    "Give each perspective a seat",
                  ][draft.step]
                }
              </h2>
              <p>
                {
                  [
                    "The more context, the more useful the perspective.",
                    "Optional details help shape your buyer personas.",
                    "Select the buyers who should evaluate your post. You can also edit or add a persona.",
                  ][draft.step]
                }
              </p>
            </div>
          </div>
          {draft.step === 0 && (
            <>
              <div className="form-grid">
                <Field label="Choose a product" className="span-2">
                  <select
                    value={product?.id || ""}
                    onChange={(e) => chooseProduct(e.target.value)}
                  >
                    <option value="" disabled>
                      Select a product
                    </option>
                    {state.products
                      .filter((p) => !p.archived)
                      .map((p) => (
                        <option key={p.id} value={p.id}>
                          {p.name} — {money(p.price)}
                        </option>
                      ))}
                  </select>
                </Field>
              </div>
              {!product && (
                <Notice>
                  <Link href="/products" className="text-link">
                    Add or restore a product
                  </Link>{" "}
                  to start a simulation.
                </Notice>
              )}
              {product && (
                <div className="selected-product">
                  <ProductArt product={product} className="product-thumb" />
                  <div>
                    <strong>{product.name}</strong>
                    <span>{product.category}</span>
                  </div>
                  <strong>{money(product.price)}</strong>
                  <Link href="/products" aria-label="Edit products">
                    <Icon name="edit" size={16} />
                  </Link>
                </div>
              )}
              <div className="form-divider" />
              <div className="form-grid">
                <Field label="Headline" className="span-2">
                  <input
                    maxLength={180}
                    value={draft.post.headline}
                    placeholder="The opening line that catches their eye"
                    onChange={(e) => postPatch({ headline: e.target.value })}
                  />
                </Field>
                <Field label="Platform">
                  <select
                    value={draft.post.platform}
                    onChange={(e) => postPatch({ platform: e.target.value })}
                  >
                    {["Facebook", "Instagram", "Facebook Live", "WhatsApp"].map(
                      (p) => (
                        <option key={p}>{p}</option>
                      ),
                    )}
                  </select>
                </Field>
                <Field label="Response language">
                  <select
                    value={draft.language}
                    onChange={(e) =>
                      patch({ language: e.target.value as "en" | "bn" })
                    }
                  >
                    <option value="en">English</option>
                    <option value="bn">বাংলা (Bangla)</option>
                  </select>
                </Field>
                <Field
                  label="Post caption"
                  className="span-2"
                  hint={`${draft.post.body.length} / 5,000 characters. English and Bangla supported.`}
                >
                  <textarea
                    rows={7}
                    maxLength={5000}
                    value={draft.post.body}
                    placeholder="Paste the post your buyers will see…"
                    onChange={(e) => postPatch({ body: e.target.value })}
                  />
                </Field>
                <Field label="Offer (optional)">
                  <input
                    maxLength={250}
                    value={draft.post.offer}
                    onChange={(e) => postPatch({ offer: e.target.value })}
                    placeholder="e.g. Free delivery on 2 items"
                  />
                </Field>
                <Field label="Call to action">
                  <input
                    maxLength={200}
                    value={draft.post.cta}
                    onChange={(e) => postPatch({ cta: e.target.value })}
                    placeholder="e.g. Message us to order"
                  />
                </Field>
                <Field label="Hashtags (optional)" className="span-2">
                  <input
                    maxLength={500}
                    value={draft.post.hashtags}
                    onChange={(e) => postPatch({ hashtags: e.target.value })}
                    placeholder="#ShopLocal #YourBrand"
                  />
                </Field>
              </div>
            </>
          )}
          {draft.step === 1 && (
            <>
              <Notice>
                Start broad if you’re unsure. These details guide the sample
                personas; they don’t describe real customers.
              </Notice>
              <div className="form-grid">
                <Field label="Location">
                  <input
                    value={draft.audience.location}
                    maxLength={200}
                    onChange={(e) =>
                      audiencePatch({ location: e.target.value })
                    }
                    placeholder="e.g. Dhaka, Bangladesh"
                  />
                </Field>
                <Field label="Age range">
                  <select
                    value={draft.audience.age}
                    onChange={(e) => audiencePatch({ age: e.target.value })}
                  >
                    {[
                      "Any age",
                      "18–24",
                      "18–34",
                      "25–34",
                      "25–44",
                      "35–54",
                      "55+",
                    ].map((v) => (
                      <option key={v}>{v}</option>
                    ))}
                  </select>
                </Field>
                <Field label="Interests" className="span-2">
                  <textarea
                    rows={2}
                    maxLength={1000}
                    value={draft.audience.interests}
                    onChange={(e) =>
                      audiencePatch({ interests: e.target.value })
                    }
                    placeholder="What do they care about?"
                  />
                </Field>
                <Field label="Purchasing preference">
                  <select
                    value={draft.audience.preferences}
                    onChange={(e) =>
                      audiencePatch({ preferences: e.target.value })
                    }
                  >
                    {[
                      "No preference",
                      "Cash on delivery",
                      "Online payment",
                      "In-store pickup",
                    ].map((v) => (
                      <option key={v}>{v}</option>
                    ))}
                  </select>
                </Field>
                <Field label="Budget sensitivity">
                  <select
                    value={draft.audience.budget}
                    onChange={(e) => audiencePatch({ budget: e.target.value })}
                  >
                    {[
                      "Low sensitivity",
                      "Medium sensitivity",
                      "High sensitivity",
                    ].map((v) => (
                      <option key={v}>{v}</option>
                    ))}
                  </select>
                </Field>
                <Field
                  label="What do they need from this product?"
                  className="span-2"
                >
                  <textarea
                    maxLength={1000}
                    rows={4}
                    value={draft.audience.needs}
                    onChange={(e) => audiencePatch({ needs: e.target.value })}
                    placeholder="e.g. A practical bag for their daily commute"
                  />
                </Field>
              </div>
              <div className="audience-tip">
                <Icon name="people" size={25} />
                <div>
                  <h3>A mix is more useful than a match.</h3>
                  <p>
                    Include a few cautious buyers alongside your likely fans.
                    The questions they raise are often the most useful.
                  </p>
                </div>
              </div>
            </>
          )}
          {draft.step === 2 && (
            <>
              <div className="row spread persona-toolbar">
                <span className="muted" role="status" aria-live="polite">
                  {draft.personas.length} selected · choose 2–{maxPersonas} personas
                </span>
                <div className="row tight">
                <button
                  className="button secondary small-button"
                  onClick={() => {
                    patch({ availablePersonas: choices, personas: choices.slice(0, maxPersonas) });
                    setError("");
                  }}
                >
                  {choices.length > maxPersonas ? `Select first ${maxPersonas}` : "Select all"}
                </button>
                <button className="button secondary small-button" disabled={!draft.personas.length}
                  onClick={() => { patch({ availablePersonas: choices, personas: [] }); setError(""); }}>
                  Clear selection
                </button>
                </div>
              </div>
              <p className="persona-selection-help" id="persona-selection-help">
                Only checked personas will evaluate your post. Unchecked personas stay available for another run.
                {selectionFull && ` You have reached the ${maxPersonas}-persona limit; uncheck one to choose another.`}
                {draft.personas.length < 2 && " Select at least two personas to continue."}
              </p>
              <div className="persona-select-grid">
                {choices.map((p) => {
                  const selected = draft.personas.some((profile) => profile.id === p.id);
                  const custom = !catalog.some((profile) => profile.id === p.id);
                  return (
                  <article className={`persona-select-card${selected ? " is-selected" : ""}`} key={p.id}>
                    <div className="row spread">
                      <Avatar persona={p} />
                      <div className="row tight">
                        <button
                          className="icon-button"
                          aria-label={`Edit ${p.name}`}
                          onClick={() => setEditing(p)}
                        >
                          <Icon name="edit" size={15} />
                        </button>
                        {custom && <button
                          className="icon-button"
                          aria-label={`Delete custom persona ${p.name}`}
                          onClick={() =>
                            patch({
                              availablePersonas: choices.filter((x) => x.id !== p.id),
                              personas: draft.personas.filter(
                                (x) => x.id !== p.id,
                              ),
                            })
                          }
                        >
                          <Icon name="close" size={15} />
                        </button>}
                      </div>
                    </div>
                    <h3>
                      {p.name}
                      <small>{p.age}</small>
                    </h3>
                    <span className="persona-role">{p.role}</span>
                    <p>{p.need}</p>
                    <Badge>{p.budget}</Badge>
                    <label className="persona-selection-control">
                      <input type="checkbox" checked={selected}
                        aria-label={`Include ${p.name} (${p.role}) in evaluation`}
                        aria-describedby="persona-selection-help"
                        disabled={!selected && selectionFull}
                        onChange={(event) => {
                          patch(setPersonaSelected(draft, p, event.target.checked, maxPersonas));
                          setError("");
                        }} />
                      <span>{selected ? "Selected for evaluation" : "Select for evaluation"}</span>
                    </label>
                  </article>
                ); })}
                {!selectionFull && (
                  <button
                    className="add-persona"
                    onClick={() =>
                      setEditing({
                        id: uid(),
                        name: "",
                        role: "",
                        age: draft.audience.age,
                        location: draft.audience.location,
                        need: "",
                        budget: draft.audience.budget,
                        color: ["blue", "peach", "mint", "lavender"][
                          draft.personas.length % 4
                        ],
                        initials: "?",
                      })
                    }
                  >
                    <Icon name="plus" size={25} />
                    <strong>Add a perspective</strong>
                    <span>Create a custom buyer persona</span>
                  </button>
                )}
              </div>
              <Field label="Simulation result">
                <select value={draft.fresh ? "fresh" : "saved"} onChange={(e) => patch({ fresh: e.target.value === "fresh", runRequestId: undefined, requestSignature: undefined })}>
                  <option value="saved">Use saved results when the inputs match</option>
                  <option value="fresh">Run a fresh simulation — call the model again</option>
                </select>
              </Field>
              <SimulationPreview draft={draft} />
            </>
          )}
          {error && (
            <p className="form-error" role="alert">
              {error}
            </p>
          )}
          <div className="wizard-actions">
            <button
              className="button secondary"
              disabled={draft.step === 0}
              onClick={() => {
                setError("");
                patch({ step: Math.max(0, draft.step - 1) });
              }}
            >
              <Icon name="back" size={15} />
              Back
            </button>
            {draft.step < 2 ? (
              <button className="button primary" onClick={next}>
                Continue <Icon name="arrow" size={16} />
              </button>
            ) : (
              <button
                className="button primary"
                onClick={start}
                disabled={preparing || draft.personas.length < 2 || draft.personas.length > maxPersonas || !product}
              >
                <Icon name="spark" size={16} />
                {preparing ? "Saving and checking results…" : draft.fresh ? "Run fresh simulation" : "Run simulation"}
              </button>
            )}
          </div>
        </section>
        <aside className="simulation-sidebar">
          <section className="panel post-preview">
            <div className="row spread">
              <span className="section-kicker">Your post at a glance</span>
              <Icon name="eye" size={17} />
            </div>
            {product ? (
              <>
                <ProductArt product={product} />
                <div className="row spread">
                  <Badge>{draft.post.platform}</Badge>
                  <strong>{money(product.price)}</strong>
                </div>
                <h3>{draft.post.headline || product.name}</h3>
                <p className="post-preview-caption">
                  {draft.post.body || "Your caption will appear here."}
                </p>
                {draft.post.offer && (
                  <Badge tone="blue">{draft.post.offer}</Badge>
                )}
                <div className="preview-cta">
                  {draft.post.cta || "Add a call to action"}
                  <Icon name="chat" size={16} />
                </div>
              </>
            ) : (
              <EmptyState
                title="Choose your product"
                description="Your post preview will appear here."
              />
            )}
          </section>
          <section className="sidebar-help">
            <span className="small-icon">
              <Icon name="shield" size={18} />
            </span>
            <h3>Your draft stays yours.</h3>
            <p>
              Products and saved post versions are stored in your account.
              Simulation inputs, personas, and results are saved to your account.
              You can reopen a report without calling the model again. No post is published.
            </p>
            <Link href="/history" className="text-link">
              Explore saved reports <Icon name="arrow" size={15} />
            </Link>
          </section>
        </aside>
      </div>
      {editing && (
        <PersonaEditor
          persona={editing}
          onClose={() => setEditing(null)}
          onSave={(p) => {
            const isNew = !choices.some((profile) => profile.id === p.id);
            patch({
              availablePersonas: [...choices.filter((profile) => profile.id !== p.id), p],
              personas: draft.personas.some((x) => x.id === p.id)
                ? draft.personas.map((x) => (x.id === p.id ? p : x))
                : isNew && !selectionFull ? [...draft.personas, p] : draft.personas,
            });
            setEditing(null);
          }}
        />
      )}
    </>
  );
}
function PersonaEditor({
  persona,
  onClose,
  onSave,
}: {
  persona: Persona;
  onClose: () => void;
  onSave: (p: Persona) => void;
}) {
  const [p, setP] = useState(persona);
  const [error, setError] = useState("");
  const change = (key: keyof Persona, value: string) =>
    setP((s) => ({ ...s, [key]: value }));
  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (![p.name, p.role, p.age, p.location, p.need].every((v) => v.trim())) {
      setError("Complete every persona field; spaces alone are not valid.");
      return;
    }
    onSave({
      ...p,
      name: p.name.trim(),
      role: p.role.trim(),
      initials: p.name.trim().slice(0, 1).toUpperCase(),
    });
  };
  return (
    <Modal
      title={
        persona.name ? "Customize this perspective" : "Add a buyer perspective"
      }
      onClose={onClose}
    >
      <form onSubmit={submit}>
        <div className="form-grid">
          <Field label="Name">
            <input
              required
              maxLength={50}
              value={p.name}
              onChange={(e) => change("name", e.target.value)}
            />
          </Field>
          <Field label="Buyer type">
            <input
              required
              maxLength={80}
              value={p.role}
              onChange={(e) => change("role", e.target.value)}
              placeholder="e.g. Quality-conscious parent"
            />
          </Field>
          <Field label="Age range">
            <input
              required
              maxLength={30}
              value={p.age}
              onChange={(e) => change("age", e.target.value)}
            />
          </Field>
          <Field label="Location">
            <input
              required
              maxLength={100}
              value={p.location}
              onChange={(e) => change("location", e.target.value)}
            />
          </Field>
          <Field label="Needs and preferences" className="span-2">
            <textarea
              required
              rows={3}
              maxLength={500}
              value={p.need}
              onChange={(e) => change("need", e.target.value)}
            />
          </Field>
          <Field label="Budget sensitivity" className="span-2">
            <select
              value={p.budget}
              onChange={(e) => change("budget", e.target.value)}
            >
              {[
                "Low sensitivity",
                "Medium sensitivity",
                "High sensitivity",
              ].map((v) => (
                <option key={v}>{v}</option>
              ))}
            </select>
          </Field>
        </div>
        {error && (
          <p className="form-error" role="alert">
            {error}
          </p>
        )}
        <div className="modal-actions">
          <button type="button" className="button secondary" onClick={onClose}>
            Cancel
          </button>
          <button type="submit" className="button primary">
            Save persona
          </button>
        </div>
      </form>
    </Modal>
  );
}
