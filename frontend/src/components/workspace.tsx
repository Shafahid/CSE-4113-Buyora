"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import { Brand, Icon, ThemeToggle } from "./ui";
import { clearSession, loadWorkspace, useWorkspace } from "@/lib/store";
import { unauthorizedEvent } from "@/lib/api-client";
import { Footer } from "./footer";

const navigation = [
  { href: "/dashboard", label: "Overview", icon: "grid" },
  { href: "/products", label: "Products", icon: "box" },
  { href: "/posts", label: "Promotional posts", icon: "file" },
  { href: "/simulate", label: "Run simulation", icon: "spark" },
  { href: "/history", label: "Simulation history", icon: "history" },
  { href: "/compare", label: "Compare reports", icon: "compare" },
];
export function Workspace({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const { data: state, error, status } = useWorkspace();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);
  useEffect(() => {
    const expired = () => clearSession();
    const refresh = () => { if (document.visibilityState === "visible") void loadWorkspace(); };
    window.addEventListener(unauthorizedEvent, expired);
    window.addEventListener("focus", refresh);
    const timer = setInterval(refresh, 240000);
    void loadWorkspace();
    return () => {
      window.removeEventListener(unauthorizedEvent, expired);
      window.removeEventListener("focus", refresh);
      clearInterval(timer);
    };
  }, []);
  useEffect(() => {
    if (status === "unauthenticated") router.replace(`/login?next=${encodeURIComponent(pathname)}`);
  }, [status, pathname, router]);
  if (status === "loading" || status === "unauthenticated") return (
    <main className="workspace-content" id="main-content" role="status">
      {status === "loading" ? "Loading your workspace…" : "Opening sign in…"}
    </main>
  );
  if (status === "error") return (
    <main className="workspace-content" id="main-content">
      <h1>Your workspace could not be loaded</h1>
      <p role="alert">{error}</p>
      <button className="button primary" onClick={() => void loadWorkspace()}>Try again</button>
      <Link className="button secondary" href="/login">Back to sign in</Link>
    </main>
  );
  const active = navigation.find((n) => pathname.startsWith(n.href));
  return (
    <div className="workspace">
      <aside className={`sidebar ${menuOpen ? "open" : ""}`}>
        <div className="sidebar-brand">
          <Brand />
          <button
            className="icon-button mobile-only"
            aria-label="Close menu"
            onClick={() => setMenuOpen(false)}
          >
            <Icon name="close" />
          </button>
        </div>
        <div className="workspace-switch">
          <span className="workspace-avatar">
            {state.profile.name.trim().charAt(0).toUpperCase()}
          </span>
          <div>
            <strong>{state.profile.name}</strong>
            {/* <small>Personal workspace</small> */}
          </div>
          <Icon name="chevron" size={14} />
        </div>
        <div className="nav-caption">Your workspace</div>
        <nav aria-label="Workspace navigation">
          {navigation.map((n) => (
            <Link
              key={n.href}
              href={n.href}
              onClick={() => setMenuOpen(false)}
              className={`nav-item ${pathname.startsWith(n.href) ? "active" : ""}`}
              aria-current={pathname.startsWith(n.href) ? "page" : undefined}
            >
              <Icon name={n.icon} size={19} />
              {n.label}
              {n.href === "/history" && (
                <span className="nav-count">{state.reports.length}</span>
              )}
            </Link>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="small-icon">
            <Icon name="spark" size={19} />
          </span>
          <h4>
            A little clarity.
            <br />
            Before you publish.
          </h4>
          <p>Get to know your buyers before your next post goes live.</p>
          <Link href="/simulate">
            Start a simulation <Icon name="arrow" size={15} />
          </Link>
        </div>
        <div className="sidebar-bottom">
          <Link
            className={`nav-item ${pathname === "/settings" ? "active" : ""}`}
            href="/settings"
          >
            <Icon name="settings" size={19} />
            Settings
          </Link>
          <Link className="profile-link" href="/settings">
            <span className="profile-avatar">
              {state.profile.name
                .split(" ")
                .map((n) => n[0])
                .slice(0, 2)
                .join("")}
            </span>
            <span>
              <strong>{state.profile.name}</strong>
              <small>
                {state.signedIn ? "Signed in" : "Demo workspace"}
              </small>
            </span>
            <Icon name="chevron" size={14} />
          </Link>
        </div>
      </aside>
      {menuOpen && (
        <button
          className="sidebar-backdrop"
          aria-label="Close navigation"
          onClick={() => setMenuOpen(false)}
        />
      )}
      <div className="workspace-main">
        <header className="topbar">
          <div className="row">
            <button
              className="icon-button mobile-only"
              aria-label="Open navigation"
              onClick={() => setMenuOpen(true)}
            >
              <Icon name="menu" />
            </button>
            <span>
              {active?.label ||
                (pathname.startsWith("/reports")
                  ? "Simulation report"
                  : "Settings")}
            </span>
          </div>
          <div className="row">
            <ThemeToggle />
            <Link
              className="icon-button"
              href="/settings"
              aria-label="Workspace settings"
            >
              <Icon name="settings" size={19} />
            </Link>
          </div>
        </header>
        {error && (
          <div className="storage-warning" role="alert">
            {error}
            <button className="text-link" onClick={() => void loadWorkspace()}>Reload workspace</button>
          </div>
        )}
        <main className="workspace-content" id="main-content">
          {children}
        </main>
        <Footer compact />
      </div>
    </div>
  );
}
