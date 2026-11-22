"use client";

import { useSyncExternalStore } from "react";
import { type DemoState, type Product, type Post, initialDraft } from "./demo-data";
import { createWorkspaceState, accountStorageKey } from "./workspace-state";
import { currentUser, type AuthUser } from "./auth-api";
import { ApiError, errorMessage } from "./api-client";
import { catalogApi } from "./catalog-api";
import { productFromApi, productToApi, postFromApi, postToApi } from "./api-adapters";
import { simulationApi, finishedRun } from "./simulation-api";
import type { ApiSchemas } from "./api-schema";

const store = createWorkspaceState(() => localStorage);
let epoch = 0;
let loadingVersion = 0;
let catalogRevision = 0;
export function clearSession() { epoch++; loadingVersion++; store.clear(); }
export function setSession(user: AuthUser) { epoch++; loadingVersion++; store.activate(user); }
function accountGuard() {
  const started = epoch;
  if (store.getAccountId() === null) throw new ApiError("Please sign in again.", 401);
  return () => {
    if (epoch !== started) throw new ApiError("Your session changed. Please reload before continuing.", 401);
  };
}
export async function loadWorkspace() {
  const version = ++loadingVersion;
  try {
    const user = await currentUser();
    if (version !== loadingVersion) return;
    if (store.getAccountId() !== user.id || store.getSnapshot().status !== "ready") { epoch++; store.activate(user); }
    const guard = accountGuard();
    const revision = catalogRevision;
    const groups = await Promise.all([catalogApi.products("active"), catalogApi.products("archived")]);
    const ids = groups.flat().map((product) => String(product.id));
    const [products, postGroups, runs] = await Promise.all([
      Promise.all(ids.map(async (id) => productFromApi(await catalogApi.product(id)))),
      Promise.all(ids.map((id) => catalogApi.posts(id))),
      simulationApi.runs(),
    ]);
    const posts = await Promise.all(postGroups.flat().map(async (post) => {
      const [detail, versions] = await Promise.all([catalogApi.post(String(post.id)), catalogApi.versions(String(post.id))]);
      return postFromApi(detail, versions);
    }));
    if (version !== loadingVersion) return;
    guard();
    if (revision !== catalogRevision) return;
    store.warn("");
    store.catalog(products, posts);
    store.runs(runs);
  } catch (error) {
    if (version !== loadingVersion) return;
    if (error instanceof ApiError && error.status === 401) clearSession();
    else if (store.getSnapshot().status === "ready") store.warn(`Workspace refresh failed: ${errorMessage(error)}`);
    else store.fail(errorMessage(error));
  }
}
function upsertProduct(product: Product) {
  catalogRevision++;
  const { products, posts } = store.getSnapshot().data;
  store.catalog(products.some((p) => p.id === product.id) ? products.map((p) => p.id === product.id ? product : p) : [...products, product], posts);
}
function upsertPost(post: Post) {
  catalogRevision++;
  const { products, posts } = store.getSnapshot().data;
  store.catalog(products, posts.some((p) => p.id === post.id) ? posts.map((p) => p.id === post.id ? post : p) : [...posts, post]);
}
export async function saveProduct(product: Product) {
  const guard = accountGuard();
  const exists = store.getSnapshot().data.products.some((p) => p.id === product.id);
  const response = exists ? await catalogApi.updateProduct(product.id, productToApi(product)) : await catalogApi.createProduct(productToApi(product));
  guard();
  const previous = store.getSnapshot().data.products.find((p) => p.id === product.id);
  const saved = { ...productFromApi(response), image: previous?.image ?? "", images: previous?.images ?? [] };
  upsertProduct(saved);
  return saved;
}
export async function refreshProduct(id: string) {
  const guard = accountGuard();
  const saved = productFromApi(await catalogApi.product(id));
  guard(); upsertProduct(saved); return saved;
}
export async function uploadProductImage(id: string, file: File) {
  const guard = accountGuard();
  const image = await catalogApi.uploadImage(id, file);
  guard(); return image;
}
export async function removeProductImage(id: string, imageId: string) {
  const guard = accountGuard();
  await catalogApi.deleteImage(id, imageId); guard();
  const product = store.getSnapshot().data.products.find((p) => p.id === id);
  if (product) {
    const images = product.images?.filter((image) => image.id !== imageId) ?? [];
    upsertProduct({ ...product, images, image: images[0]?.url ?? "" });
  }
}
export async function duplicateProduct(id: string) {
  const guard = accountGuard();
  const result = await catalogApi.duplicateProduct(id); guard(); upsertProduct(productFromApi(result));
}
export async function archiveProduct(id: string, archived: boolean) {
  const guard = accountGuard();
  const result = await catalogApi.updateProduct(id, { status: archived ? "archived" : "active" }); guard();
  const previous = store.getSnapshot().data.products.find((p) => p.id === id);
  upsertProduct({ ...productFromApi(result), image: previous?.image ?? "", images: previous?.images });
}
export async function deleteProduct(id: string) {
  const guard = accountGuard();
  await catalogApi.deleteProduct(id); guard();
  catalogRevision++;
  const { products, posts } = store.getSnapshot().data;
  store.catalog(products.filter((p) => p.id !== id), posts.filter((p) => p.productId !== id));
  await loadWorkspace();
}
export async function loadPostHistory(id: string) {
  const guard = accountGuard();
  const [detail, versions] = await Promise.all([catalogApi.post(id), catalogApi.versions(id)]);
  guard(); const post = postFromApi(detail, versions); upsertPost(post); return post;
}
export async function savePost(post: Post) {
  const guard = accountGuard();
  const existing = store.getSnapshot().data.posts.find((p) => p.id === post.id);
  if (existing && existing.productId !== post.productId) throw new ApiError("A saved post cannot be moved to a different product.");
  const input = postToApi(post);
  if (existing && JSON.stringify(postToApi(existing)) === JSON.stringify(input)) return existing;
  if (!existing) {
    const detail = await catalogApi.createPost(post.productId, input); guard();
    const saved = postFromApi(detail); upsertPost(saved); return saved;
  }
  const version = await catalogApi.createVersion(post.id, input); guard();
  const saved: Post = {
    ...post, headline: version.headline, body: version.body, offer: version.offer ?? "", cta: version.call_to_action ?? "",
    hashtags: version.hashtags?.join(" ") ?? "", platform: version.platform,
    latestVersionId: String(version.id), latestVersionCreatedAt: version.created_at, versionNumber: version.version_number,
    versions: [...existing.versions, {
      id: existing.latestVersionId!, body: existing.body, createdAt: existing.latestVersionCreatedAt!, versionNumber: existing.versionNumber,
      headline: existing.headline, offer: existing.offer, cta: existing.cta, hashtags: existing.hashtags, platform: existing.platform,
    }],
  };
  upsertPost(saved);
  // The new version is already committed. A history refresh failure must not
  // make the caller retry a successful write and create another version.
  try { return await loadPostHistory(saved.id); }
  catch (error) { guard(); store.warn(`Post saved; history refresh failed: ${errorMessage(error)}`); return saved; }
}
export async function deletePost(id: string) {
  const guard = accountGuard(); await catalogApi.deletePost(id); guard();
  catalogRevision++;
  const { products, posts } = store.getSnapshot().data;
  store.catalog(products, posts.filter((p) => p.id !== id));
  await loadWorkspace();
}
export async function startSimulation(data: ApiSchemas["RunCreate"]) {
  const guard = accountGuard();
  const run = await simulationApi.start(data); guard(); catalogRevision++; store.run(run); return run;
}
export async function refreshSimulation(id: string, signal?: AbortSignal) {
  const guard = accountGuard();
  const run = await simulationApi.run(id, signal); guard(); catalogRevision++; store.run(run); return run;
}
export async function refreshSimulationProgress(id: string, signal?: AbortSignal) {
  const guard = accountGuard();
  const progress = await simulationApi.progress(id, signal); guard();
  // Publish terminal status only with its finished report. Otherwise a report
  // page can unmount its poller and abort the final fetch while showing old data.
  if (finishedRun({ ...progress, report: null })) return refreshSimulation(id, signal);
  const previous = store.getSnapshot().runs.find((run) => run.id === id);
  const run = { ...progress, report: previous?.report ?? null };
  catalogRevision++; store.run(run); return run;
}
export async function retryFailedSimulation(id: string, requestId: string) {
  const guard = accountGuard();
  const run = await simulationApi.retryFailed(id, requestId); guard();
  catalogRevision++; store.run(run); return run;
}
export async function retrySimulation(id: string, evaluationId: number) {
  const guard = accountGuard();
  const run = await simulationApi.retry(id, evaluationId); guard(); catalogRevision++; store.run(run); return run;
}
export async function saveReportChanges(id: string, revised: string, applied: string[]) {
  const guard = accountGuard();
  const run = await simulationApi.saveReport(id, revised, applied); guard(); catalogRevision++; store.run(run); return run;
}
export async function removeSimulation(id: string) {
  const guard = accountGuard();
  await simulationApi.remove(id); guard(); catalogRevision++; store.removeRun(id);
}
let subscribers = 0;
function sync(event: StorageEvent) {
  const id = store.getAccountId();
  if (id !== null && (event.key === accountStorageKey(id) || event.key === null)) store.reloadLocal();
}
function subscribe(listener: () => void) {
  const unsubscribe = store.subscribe(listener);
  if (subscribers++ === 0) window.addEventListener("storage", sync);
  return () => {
    unsubscribe();
    if (--subscribers === 0) window.removeEventListener("storage", sync);
  };
}
export function useWorkspace() {
  return useSyncExternalStore(
    subscribe,
    store.getSnapshot,
    store.getServerSnapshot,
  );
}
export function useDemo() {
  return useWorkspace().data;
}
export function updateDemo(update: (current: DemoState) => DemoState) {
  store.updateLocal(update);
}
export function resetDemo() {
  updateDemo((state) => ({ ...state, reports: state.reports.filter((r) => r.source === "server"), draft: { ...structuredClone(initialDraft), productId: "", post: { ...structuredClone(initialDraft.post), id: "", productId: "" } } }));
}
export function download(
  name: string,
  content: string,
  type = "application/json",
) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
