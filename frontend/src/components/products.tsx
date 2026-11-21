"use client";
import { useState, type FormEvent } from "react";
import { useRouter } from "next/navigation";
import { Product, money, uid, initialDraft } from "@/lib/demo-data";
import { useDemo, updateDemo, saveProduct, duplicateProduct, archiveProduct, deleteProduct, uploadProductImage, removeProductImage, refreshProduct } from "@/lib/store";
import { errorMessage } from "@/lib/api-client";
import {
  Badge,
  EmptyState,
  Field,
  Icon,
  Modal,
  PageHeading,
  ProductArt,
  useToast,
} from "./ui";

const empty: Product = {
  id: "",
  name: "",
  price: 0,
  category: "Fashion & accessories",
  description: "",
  features: "",
  warranty: "",
  delivery: "",
  returns: "",
  image: "",
  art: "tote",
  archived: false,
};
export function Products() {
  const { products, posts } = useDemo();
  const router = useRouter();
  const toast = useToast();
  const [query, setQuery] = useState("");
  const [archived, setArchived] = useState(false);
  const [editing, setEditing] = useState<Product | null>(null);
  const [viewing, setViewing] = useState<Product | null>(null);
  const [deleting, setDeleting] = useState<Product | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  async function action(work: () => Promise<void>, message: string) {
    setBusy(true); setError("");
    try { await work(); toast(message); }
    catch (error) { setError(errorMessage(error)); }
    finally { setBusy(false); }
  }
  const list = products.filter(
    (p) =>
      p.archived === archived &&
      `${p.name} ${p.category}`.toLowerCase().includes(query.toLowerCase()),
  );
  function run(p: Product) {
    const post = posts.find((x) => x.productId === p.id) || {
      ...initialDraft.post,
      id: uid(),
      productId: p.id,
      headline: p.name,
      body: p.description,
      versions: [],
    };
    updateDemo((s) => ({
      ...s,
      draft: { ...s.draft, productId: p.id, post, step: 0 },
    }));
    router.push("/simulate");
  }
  return (
    <>
      <PageHeading
        eyebrow="Products"
        title="The things you bring to life."
        description="Keep your product details in one place. Give every simulation the full picture."
      >
        <button
          className="button primary"
          disabled={busy}
          onClick={() => setEditing({ ...empty })}
        >
          <Icon name="plus" size={17} />
          Add product
        </button>
      </PageHeading>
      {error && <p className="form-error" role="alert">{error}</p>}
      {busy && <p role="status">Saving changes…</p>}
      <div className="list-toolbar">
        <div className="segmented">
          <button
            className={!archived ? "selected" : ""}
            onClick={() => setArchived(false)}
          >
            Active <span>{products.filter((p) => !p.archived).length}</span>
          </button>
          <button
            className={archived ? "selected" : ""}
            onClick={() => setArchived(true)}
          >
            Archived <span>{products.filter((p) => p.archived).length}</span>
          </button>
        </div>
        <label className="search-input">
          <Icon name="search" size={17} />
          <input
            aria-label="Search products"
            placeholder="Search products…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
      </div>
      {list.length ? (
        <div className="product-grid">
          {list.map((p) => (
            <article className="product-card" key={p.id}>
              <button
                className="product-art-button"
                onClick={() => setViewing(p)}
                aria-label={`View ${p.name}`}
              >
                <ProductArt product={p} />
              </button>
              <div className="product-card-body">
                <div className="row spread">
                  <Badge>{p.category}</Badge>
                  <strong>{money(p.price)}</strong>
                </div>
                <button
                  className="product-title-button"
                  onClick={() => setViewing(p)}
                >
                  <h2>{p.name}</h2>
                </button>
                <p>{p.description}</p>
                <div className="product-card-actions">
                  <button
                    className="button secondary small-button"
                    onClick={() => run(p)}
                    disabled={p.archived}
                  >
                    <Icon name="spark" size={15} />
                    Simulate
                  </button>
                  <div className="row tight">
                    <button
                      className="icon-button"
                      aria-label={`Edit ${p.name}`}
                      title="Edit product"
                      disabled={busy}
                      onClick={() => setEditing(p)}
                    >
                      <Icon name="edit" size={16} />
                    </button>
                    <button
                      className="icon-button"
                      aria-label={`Duplicate ${p.name}`}
                      title="Duplicate product"
                      disabled={busy}
                      onClick={() => void action(() => duplicateProduct(p.id), "Product duplicated without photos")}
                    >
                      <Icon name="copy" size={16} />
                    </button>
                    <button
                      className="icon-button"
                      aria-label={`${p.archived ? "Restore" : "Archive"} ${p.name}`}
                      title={p.archived ? "Restore product" : "Archive product"}
                      disabled={busy}
                      onClick={() => void action(() => archiveProduct(p.id, !p.archived), p.archived ? "Product restored" : "Product archived")}
                    >
                      <Icon name={p.archived ? "refresh" : "box"} size={16} />
                    </button>
                    <button
                      className="icon-button danger-text"
                      aria-label={`Delete ${p.name}`}
                      title="Delete product"
                      disabled={busy}
                      onClick={() => setDeleting(p)}
                    >
                      <Icon name="trash" size={16} />
                    </button>
                  </div>
                </div>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <EmptyState
          title={
            query
              ? "No products found"
              : archived
                ? "No archived products"
                : "Make room for your first product"
          }
          description={
            query
              ? "Try another name or category."
              : "Add product details to start exploring buyer perspectives."
          }
        >
          {!archived && !query && (
            <button
              className="button primary"
              onClick={() => setEditing({ ...empty })}
            >
              Add product
            </button>
          )}
        </EmptyState>
      )}
      <p className="quiet-note">
        <Icon name="info" size={15} /> Product illustrations are placeholders.
        Upload your own product photo when editing.
      </p>
      {editing && (
        <ProductEditor
          product={editing}
          onClose={() => setEditing(null)}
          onSave={() => {
            setEditing(null);
            toast("Product saved");
          }}
        />
      )}
      {viewing && (
        <Modal title={viewing.name} onClose={() => setViewing(null)}>
          <ProductArt product={viewing} />
          <div className="detail-price">
            {money(viewing.price)} <Badge>{viewing.category}</Badge>
          </div>
          <p>{viewing.description}</p>
          <dl className="details-list">
            {[
              ["Features", viewing.features],
              ["Warranty", viewing.warranty],
              ["Delivery", viewing.delivery],
              ["Returns", viewing.returns],
            ].map(([label, value]) => (
              <div key={label}>
                <dt>{label}</dt>
                <dd>{value || "Not provided"}</dd>
              </div>
            ))}
          </dl>
          <div className="modal-actions">
            <button
              className="button secondary"
              onClick={() => {
                setEditing(viewing);
                setViewing(null);
              }}
            >
              Edit product
            </button>
            <button
              className="button primary"
              disabled={viewing.archived}
              onClick={() => run(viewing)}
            >
              Run simulation <Icon name="arrow" size={15} />
            </button>
          </div>
        </Modal>
      )}
      {deleting && (
        <Modal title="Delete this product?" onClose={() => { if (!busy) setDeleting(null); }}>
          <p>
            “{deleting.name}” and its promotional drafts will be removed. Saved
            reports keep their original product snapshot.
          </p>
          {error && <p className="form-error" role="alert">{error}</p>}
          <div className="modal-actions">
            <button
              className="button secondary"
              disabled={busy}
              onClick={() => setDeleting(null)}
            >
              Keep product
            </button>
            <button
              className="button danger"
              disabled={busy}
              onClick={() => void action(async () => { await deleteProduct(deleting.id); setDeleting(null); }, "Product deleted")}
            >
              Delete product
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}
export function ProductEditor({
  product,
  onClose,
  onSave,
}: {
  product: Product;
  onClose: () => void;
  onSave: () => void;
}) {
  const [p, setP] = useState(product);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [removeIds, setRemoveIds] = useState<string[]>([]);
  const change = (key: keyof Product, value: string | number) =>
    setP((s) => ({ ...s, [key]: value }));
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (
      !p.name.trim() ||
      !p.description.trim() ||
      !Number.isFinite(p.price) ||
      p.price <= 0
    ) {
      setError(
        "Add a product name, description, and a price greater than zero.",
      );
      return;
    }
    setPending(true); setError("");
    let detailsSaved = false;
    try {
      const saved = await saveProduct({ ...p, name: p.name.trim() });
      detailsSaved = true;
      setP(saved);
      if (file) {
        await uploadProductImage(saved.id, file);
        setFile(null);
      }
      for (const imageId of removeIds) {
        await removeProductImage(saved.id, imageId);
        setRemoveIds((ids) => ids.filter((id) => id !== imageId));
      }
      setP(await refreshProduct(saved.id));
      onSave();
    } catch (error) {
      setError(`${detailsSaved ? "Product details are saved. Photo changes may be incomplete. " : ""}${errorMessage(error)}`);
    } finally { setPending(false); }
  };
  return (
    <Modal
      title={product.name ? "Edit product" : "Add a product"}
      onClose={() => { if (!pending) onClose(); }}
      wide
    >
      <form onSubmit={submit}>
        <fieldset disabled={pending} style={{ border: 0, padding: 0, margin: 0, minWidth: 0 }}>
        <div className="editor-grid">
          <div>
            <ProductArt product={p} />
            {Boolean(p.images?.length) && (
              <div className="row tight" style={{ flexWrap: "wrap" }}>
                {p.images?.filter((image) => !removeIds.includes(image.id)).map((image, index) => (
                  <button type="button" className="icon-button" key={image.id}
                    aria-label={`Preview saved photo ${index + 1}`} onClick={() => change("image", image.url)}>
                    <ProductArt product={{ ...p, image: image.url }} className="product-thumb" />
                  </button>
                ))}
              </div>
            )}
            <label className="upload-button">
              <Icon name="upload" size={16} />
              Add product photo
              <input
                type="file"
                accept="image/png,image/jpeg,image/webp"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (!file) return;
                  if (
                    !["image/png", "image/jpeg", "image/webp"].includes(
                      file.type,
                    ) ||
                    file.size > 5 * 1024 * 1024
                  ) {
                    setError(
                      "Choose a PNG, JPG, or WebP image up to 5 MB.",
                    );
                    return;
                  }
                  const reader = new FileReader();
                  reader.onload = () => {
                    setFile(file);
                    change("image", String(reader.result));
                    setError("");
                  };
                  reader.onerror = () =>
                    setError("The image could not be read. Try another file.");
                  reader.readAsDataURL(file);
                }}
              />
            </label>
            <small className="muted">PNG, JPG, WebP · up to 5 MB. Photos are saved after product details.</small>
            {file && <p className="muted">Selected photo: {file.name}</p>}
            {p.image && (
              <button
                type="button"
                className="text-link"
                onClick={() => {
                  if (file) { setFile(null); change("image", p.images?.find((image) => !removeIds.includes(image.id))?.url ?? ""); }
                  else {
                    const image = p.images?.find((image) => image.url === p.image);
                    if (image) {
                      setRemoveIds((ids) => [...ids, image.id]);
                      change("image", p.images?.find((item) => item.id !== image.id && !removeIds.includes(item.id))?.url ?? "");
                    }
                  }
                }}
              >
                Remove photo
              </button>
            )}
          </div>
          <div className="form-grid">
            <Field label="Product name">
              <input
                required
                maxLength={100}
                value={p.name}
                onChange={(e) => change("name", e.target.value)}
                placeholder="e.g. Nila everyday tote"
              />
            </Field>
            <Field label="Price (BDT)">
              <input
                required
                type="number"
                min="1"
                max="10000000"
                step=".01"
                value={p.price || ""}
                onChange={(e) => change("price", Number(e.target.value))}
                placeholder="890"
              />
            </Field>
            <Field label="Category">
              <select
                value={p.category}
                onChange={(e) => change("category", e.target.value)}
              >
                {[
                  "Fashion & accessories",
                  "Clothing",
                  "Electronics",
                  "Beauty & care",
                  "Home & living",
                  "Food & beverage",
                  "Other",
                ].map((c) => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </Field>
            <Field label="Description" className="span-2">
              <textarea
                required
                rows={3}
                maxLength={2000}
                value={p.description}
                onChange={(e) => change("description", e.target.value)}
                placeholder="What is it, and who is it for?"
              />
            </Field>
            <Field label="Features" className="span-2">
              <textarea
                rows={2}
                maxLength={1000}
                value={p.features}
                onChange={(e) => change("features", e.target.value)}
              />
            </Field>
            <Field label="Warranty">
              <input
                maxLength={500}
                value={p.warranty}
                onChange={(e) => change("warranty", e.target.value)}
                placeholder="e.g. 30-day stitching warranty"
              />
            </Field>
            <Field label="Delivery details">
              <input
                maxLength={500}
                value={p.delivery}
                onChange={(e) => change("delivery", e.target.value)}
                placeholder="Coverage, time, and charge"
              />
            </Field>
            <Field label="Return / exchange policy" className="span-2">
              <input
                maxLength={500}
                value={p.returns}
                onChange={(e) => change("returns", e.target.value)}
                placeholder="When can a buyer return or exchange?"
              />
            </Field>
          </div>
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
          <button className="button primary" type="submit">
            {pending ? "Saving…" : "Save product"} <Icon name="check" size={16} />
          </button>
        </div>
        </fieldset>
      </form>
    </Modal>
  );
}
