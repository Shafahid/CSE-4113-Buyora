export type StoreSnapshot<T> = { data: T; error: string };
type StorageAdapter = Pick<Storage, "getItem" | "setItem">;

// A cached snapshot includes both data and errors so error-only changes notify
// React too. Storage is obtained lazily, keeping server rendering safe.
export function createPersistentStore<T>(
  initial: T,
  validate: (value: unknown) => value is T,
  storage: () => StorageAdapter,
  key: string,
) {
  const serverSnapshot: StoreSnapshot<T> = { data: initial, error: "" };
  let current = serverSnapshot;
  let loaded = false;
  const listeners = new Set<() => void>();
  function publish(data: T, error: string) {
    if (current.data === data && current.error === error) return;
    current = { data, error };
    listeners.forEach((listener) => listener());
  }
  function reload() {
    loaded = true;
    let raw: string | null;
    try {
      raw = storage().getItem(key);
    } catch {
      publish(
        current.data,
        "Browser storage is unavailable. Changes will last for this session only.",
      );
      return;
    }
    if (!raw) {
      publish(initial, "");
      return;
    }
    try {
      const parsed: unknown = JSON.parse(raw);
      if (validate(parsed)) {
        publish(parsed, "");
        return;
      }
    } catch {
      /* Malformed JSON follows the same recovery as an invalid shape. */
    }
    publish(
      initial,
      "Saved demo data could not be read. A fresh workspace is available.",
    );
  }
  return {
    getSnapshot() {
      if (!loaded) reload();
      return current;
    },
    getServerSnapshot: () => serverSnapshot,
    reload,
    subscribe(listener: () => void) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    update(update: (data: T) => T) {
      if (!loaded) reload();
      const data = update(current.data);
      let error = "";
      try {
        storage().setItem(key, JSON.stringify(data));
      } catch {
        error =
          "Browser storage is full or unavailable. Your changes are only saved for this session. Try a smaller image or export your workspace.";
      }
      publish(data, error);
    },
  };
}
