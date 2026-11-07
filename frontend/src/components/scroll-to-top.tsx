"use client";

import { useSyncExternalStore } from "react";
import { Icon } from "./ui";
import styles from "./scroll-to-top.module.css";

function subscribe(onScroll: () => void) {
  window.addEventListener("scroll", onScroll, { passive: true });
  return () => window.removeEventListener("scroll", onScroll);
}

function getSnapshot() {
  return window.scrollY > 400;
}

function getServerSnapshot() {
  return false;
}

export function ScrollToTop() {
  const visible = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);

  if (!visible) return null;

  return (
    <button
      type="button"
      className={styles.button}
      aria-label="Back to top"
      title="Back to top"
      onClick={() => {
        window.scrollTo({
          top: 0,
          behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches
            ? "instant"
            : "smooth",
        });
      }}
    >
      <Icon name="arrow" size={22} className={styles.arrow} />
    </button>
  );
}
