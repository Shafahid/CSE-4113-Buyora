import { initialDraft, type DemoState, type Product, type Post } from "./demo-data";
import { validWorkspace } from "./persistence";
import type { AuthUser } from "./auth-api";

export type WorkspaceSnapshot = {
  data: DemoState;
  error: string;
  status: "loading" | "ready" | "unauthenticated" | "error";
};
export const accountStorageKey = (id: number) => `buyora-account-v1:${id}`;
const emptyWorkspace = (): DemoState => ({
  version: 1, products: [], posts: [], reports: [], signedIn: false,
  profile: { name: "", email: "" },
  draft: { ...structuredClone(initialDraft), productId: "", post: { ...structuredClone(initialDraft.post), id: "", productId: "" } },
});

// Only unfinished demo simulations and their reports use browser storage.
// Identity, products, posts and signed image URLs always come from the API.
export function createWorkspaceState(storage: () => Pick<Storage, "getItem" | "setItem">) {
  const serverSnapshot: WorkspaceSnapshot = { data: emptyWorkspace(), error: "", status: "loading" };
  let snapshot = serverSnapshot;
  let accountId: number | null = null;
  let localError = "";
  let remoteError = "";
  const listeners = new Set<() => void>();
  function publish(next: WorkspaceSnapshot) {
    snapshot = { ...next, error: [localError, remoteError].filter(Boolean).join(" ") };
    listeners.forEach((listener) => listener());
  }
  function readLocal() {
    const data = emptyWorkspace();
    let error = "";
    if (accountId !== null) {
      try {
        const raw = storage().getItem(accountStorageKey(accountId));
        if (raw) {
          const parsed: unknown = JSON.parse(raw);
          if (!parsed || typeof parsed !== "object") throw new Error();
          const candidate = { ...data, reports: "reports" in parsed ? parsed.reports : null, draft: "draft" in parsed ? parsed.draft : null };
          if (!validWorkspace(candidate)) throw new Error();
          data.reports = candidate.reports;
          data.draft = candidate.draft;
        }
      } catch { error = "Saved simulation previews could not be loaded. Products and posts are safe on the server."; }
    }
    return { data, error };
  }
  return {
    getSnapshot: () => snapshot,
    getServerSnapshot: () => serverSnapshot,
    getAccountId: () => accountId,
    subscribe(listener: () => void) { listeners.add(listener); return () => { listeners.delete(listener); }; },
    activate(user: AuthUser) {
      accountId = user.id;
      const local = readLocal();
      localError = local.error;
      remoteError = "";
      publish({ ...local, status: "loading", data: { ...local.data, signedIn: true, profile: { name: user.display_name, email: user.email } } });
    },
    catalog(products: Product[], posts: Post[]) {
      publish({ ...snapshot, status: "ready", data: { ...snapshot.data, products, posts } });
    },
    clear() {
      accountId = null;
      localError = "";
      remoteError = "";
      publish({ data: emptyWorkspace(), error: "", status: "unauthenticated" });
    },
    fail(error: string) { remoteError = error; publish({ ...snapshot, status: "error" }); },
    warn(error: string) { remoteError = error; publish(snapshot); },
    reloadLocal() {
      const local = readLocal();
      localError = local.error;
      publish({ ...snapshot, error: local.error, data: { ...snapshot.data, reports: local.data.reports, draft: local.data.draft } });
    },
    updateLocal(update: (value: DemoState) => DemoState) {
      if (accountId === null) return;
      const updated = update(snapshot.data);
      const data = { ...snapshot.data, draft: updated.draft, reports: updated.reports };
      localError = "";
      try { storage().setItem(accountStorageKey(accountId), JSON.stringify({ version: 1, draft: data.draft, reports: data.reports })); }
      catch { localError = "Simulation previews could not be saved in this browser. Server products and posts are unaffected."; }
      publish({ ...snapshot, data });
    },
  };
}
