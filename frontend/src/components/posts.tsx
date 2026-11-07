"use client";
import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import {
  Post,
  dateLabel,
  initialDraft,
  savePostVersion,
  uid,
} from "@/lib/demo-data";
import { updateDemo, useDemo } from "@/lib/store";
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
  useToast,
} from "./ui";

export function Posts() {
  const state = useDemo();
  const router = useRouter();
  const toast = useToast();
  const [editing, setEditing] = useState<Post | null>(null);
  const [history, setHistory] = useState<Post | null>(null);
  const [query, setQuery] = useState("");
  const activeProducts = state.products.filter((p) => !p.archived);
  const list = state.posts.filter((p) =>
    `${p.headline} ${p.body}`.toLowerCase().includes(query.toLowerCase()),
  );
  function save(post: Post) {
    updateDemo((s) => ({
      ...s,
      posts: s.posts.some((p) => p.id === post.id)
        ? s.posts.map((p) => (p.id === post.id ? savePostVersion(p, post) : p))
        : [...s.posts, savePostVersion(undefined, post)],
    }));
    setEditing(null);
    toast("Post saved");
  }
  return (
    <>
      <PageHeading
        eyebrow="Promotional posts"
        title="Good ideas, taking shape."
        description="Draft your next post. Keep every version and explore what changes."
      >
        <button
          className="button primary"
          disabled={!activeProducts.length}
          onClick={() =>
            setEditing({
              ...initialDraft.post,
              id: uid(),
              productId: activeProducts[0]?.id || "",
              headline: "",
              body: "",
              offer: "",
              hashtags: "",
              versions: [],
            })
          }
        >
          <Icon name="plus" size={17} />
          Create post
        </button>
      </PageHeading>
      <div className="list-toolbar">
        <span className="muted">{state.posts.length} promotional posts</span>
        <label className="search-input">
          <Icon name="search" size={17} />
          <input
            aria-label="Search posts"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search your drafts…"
          />
        </label>
      </div>
      {!activeProducts.length && (
        <Notice>
          Add an active product before creating a post.{" "}
          <ButtonLink href="/products" secondary>
            Add product
          </ButtonLink>
        </Notice>
      )}
      {list.length ? (
        <div className="posts-grid">
          {list.map((p) => {
            const product = state.products.find((x) => x.id === p.productId);
            return (
              <article className="panel post-card" key={p.id}>
                <div className="row spread">
                  <Badge tone="blue">{p.platform}</Badge>
                  <Badge>Version {p.versions.length + 1}</Badge>
                </div>
                <h2>{p.headline}</h2>
                <p>{p.body}</p>
                {p.offer && <Badge tone="green">{p.offer}</Badge>}
                <div className="post-product">
                  {product && (
                    <ProductArt product={product} className="product-thumb" />
                  )}
                  <div>
                    <strong>
                      {product?.name || "Product no longer available"}
                    </strong>
                    <small>{p.cta}</small>
                  </div>
                </div>
                <div className="row spread post-actions">
                  <div className="row tight">
                    <button
                      className="icon-button"
                      aria-label={`Edit ${p.headline}`}
                      title="Edit post"
                      onClick={() => setEditing(p)}
                    >
                      <Icon name="edit" size={17} />
                    </button>
                    <button
                      className="icon-button"
                      title="Version history"
                      aria-label={`Version history for ${p.headline}`}
                      onClick={() => setHistory(p)}
                    >
                      <Icon name="history" size={17} />
                    </button>
                  </div>
                  <button
                    className="button secondary small-button"
                    disabled={!product || product.archived}
                    onClick={() => {
                      updateDemo((s) => ({
                        ...s,
                        draft: {
                          ...s.draft,
                          productId: p.productId,
                          post: structuredClone(p),
                          step: 0,
                        },
                      }));
                      router.push("/simulate");
                    }}
                  >
                    Test this post <Icon name="arrow" size={15} />
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      ) : (
        <EmptyState
          title={query ? "No matching drafts" : "Your next post starts here"}
          description={
            query
              ? "Try a different search."
              : "Create a promotional draft and explore buyer perspectives."
          }
        />
      )}
      {editing && (
        <PostEditor
          post={editing}
          onSave={save}
          onClose={() => setEditing(null)}
        />
      )}
      {history && (
        <Modal title="Post version history" onClose={() => setHistory(null)}>
          <Notice>
            Earlier captions are preserved whenever you save a revision.
          </Notice>
          <h3>Current · Version {history.versions.length + 1}</h3>
          <p className="version-body">{history.body}</p>
          {[...history.versions].reverse().map((v, i) => (
            <div className="version-row" key={v.id}>
              <div className="row spread">
                <h3>Version {history.versions.length - i}</h3>
                <span className="muted">{dateLabel(v.createdAt)}</span>
              </div>
              <p>{v.body}</p>
              <button
                className="text-link"
                onClick={() => {
                  setEditing({ ...history, body: v.body });
                  setHistory(null);
                }}
              >
                Use as a new revision <Icon name="arrow" size={14} />
              </button>
            </div>
          ))}
        </Modal>
      )}
    </>
  );
}
function PostEditor({
  post,
  onSave,
  onClose,
}: {
  post: Post;
  onSave: (p: Post) => void;
  onClose: () => void;
}) {
  const { products } = useDemo();
  const [p, setP] = useState(post);
  const [error, setError] = useState("");
  const patch = (value: Partial<Post>) => setP((s) => ({ ...s, ...value }));
  function submit(e: FormEvent) {
    e.preventDefault();
    if (!products.some((product) => product.id === p.productId)) {
      setError("Choose an existing product for this post.");
      return;
    }
    if (!p.headline.trim() || p.body.trim().length < 20) {
      setError(
        "Add a headline and a caption with at least 20 non-padding characters.",
      );
      return;
    }
    onSave({ ...p, headline: p.headline.trim(), body: p.body.trim() });
  }
  return (
    <Modal
      title={post.headline ? "Revise your post" : "Create a promotional post"}
      onClose={onClose}
      wide
    >
      <form onSubmit={submit}>
        <div className="form-grid">
          <Field label="Related product">
            <select
              required
              value={p.productId}
              onChange={(e) => patch({ productId: e.target.value })}
            >
              {products.map((x) => (
                <option key={x.id} value={x.id}>
                  {x.name}
                  {x.archived ? " (archived)" : ""}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Platform">
            <select
              value={p.platform}
              onChange={(e) => patch({ platform: e.target.value })}
            >
              {["Facebook", "Instagram", "Facebook Live", "WhatsApp"].map(
                (v) => (
                  <option key={v}>{v}</option>
                ),
              )}
            </select>
          </Field>
          <Field label="Headline" className="span-2">
            <input
              required
              maxLength={180}
              value={p.headline}
              onChange={(e) => patch({ headline: e.target.value })}
            />
          </Field>
          <Field
            label="Caption"
            className="span-2"
            hint="At least 20 characters. Earlier saved captions are kept as separate versions."
          >
            <textarea
              required
              minLength={20}
              maxLength={5000}
              rows={7}
              value={p.body}
              onChange={(e) => patch({ body: e.target.value })}
            />
          </Field>
          <Field label="Offer">
            <input
              maxLength={250}
              value={p.offer}
              onChange={(e) => patch({ offer: e.target.value })}
            />
          </Field>
          <Field label="Call to action">
            <input
              maxLength={200}
              value={p.cta}
              onChange={(e) => patch({ cta: e.target.value })}
            />
          </Field>
          <Field label="Hashtags" className="span-2">
            <input
              maxLength={500}
              value={p.hashtags}
              onChange={(e) => patch({ hashtags: e.target.value })}
            />
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
          <button className="button primary">
            Save version <Icon name="check" size={15} />
          </button>
        </div>
      </form>
    </Modal>
  );
}
