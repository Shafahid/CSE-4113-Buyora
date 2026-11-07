"use client";

import { useSyncExternalStore } from "react";
import { DemoState, initialState } from "./demo-data";
import { validWorkspace } from "./persistence";
import { createPersistentStore } from "./persistent-store";

const KEY = "buyora-workspace-v1";
const store = createPersistentStore(
  initialState,
  validWorkspace,
  () => localStorage,
  KEY,
);
let subscribers = 0;
function sync(event: StorageEvent) {
  // A null key means another tab called localStorage.clear().
  if (event.key === KEY || event.key === null) store.reload();
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
  store.update(update);
}
export function resetDemo() {
  updateDemo(() => structuredClone(initialState));
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
