"use client";

import { useEffect, useRef, type ReactNode } from "react";
import styles from "./landing-reveals.module.css";

export function LandingReveals({ children }: { children: ReactNode }) {
  const root = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = root.current;
    if (!container) return;
    const elements = Array.from(
      container.querySelectorAll<HTMLElement>("[data-landing-reveal]"),
    );
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)");
    const showAll = () => {
      elements.forEach((element) => {
        element.dataset.landingReveal = "visible";
      });
    };

    // Content stays visible without JavaScript or observer support.
    if (motion.matches || !("IntersectionObserver" in window)) {
      showAll();
      return;
    }

    container.querySelectorAll("[data-landing-stagger]").forEach((group) => {
      Array.from(group.children).forEach((child, index) => {
        if (
          child instanceof HTMLElement &&
          child.hasAttribute("data-landing-reveal")
        ) {
          child.style.setProperty(
            "--landing-reveal-delay",
            `${Math.min(index * 70, 280)}ms`,
          );
        }
      });
    });

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(({ target, isIntersecting }) => {
          if (!isIntersecting || !(target instanceof HTMLElement)) return;
          if (target.dataset.landingReveal === "pending") {
            target.dataset.landingReveal = "revealed";
          }
          observer.unobserve(target);
        });
      },
      { threshold: 0.06, rootMargin: "0px 0px -32px 0px" },
    );

    elements.forEach((element) => {
      if (["revealed", "visible"].includes(element.dataset.landingReveal ?? ""))
        return;
      element.dataset.landingReveal = "pending";
      observer.observe(element);
    });

    const handleMotionChange = () => {
      if (!motion.matches) return;
      observer.disconnect();
      showAll();
    };
    const handleFocus = (event: FocusEvent) => {
      if (!(event.target instanceof HTMLElement)) return;
      const element = event.target.closest<HTMLElement>(
        "[data-landing-reveal]",
      );
      if (element) {
        element.dataset.landingReveal = "visible";
        observer.unobserve(element);
      }
    };
    const handleAnimationEnd = (event: AnimationEvent) => {
      if (
        event.target instanceof HTMLElement &&
        event.target.dataset.landingReveal === "revealed"
      ) {
        event.target.dataset.landingReveal = "visible";
      }
    };
    motion.addEventListener("change", handleMotionChange);
    container.addEventListener("focusin", handleFocus);
    container.addEventListener("animationend", handleAnimationEnd);

    return () => {
      observer.disconnect();
      motion.removeEventListener("change", handleMotionChange);
      container.removeEventListener("focusin", handleFocus);
      container.removeEventListener("animationend", handleAnimationEnd);
      elements.forEach((element) => {
        if (element.dataset.landingReveal === "pending") {
          element.dataset.landingReveal = "";
        }
      });
    };
  }, []);

  return (
    <div className={`landing ${styles.root}`} ref={root}>
      {children}
    </div>
  );
}
