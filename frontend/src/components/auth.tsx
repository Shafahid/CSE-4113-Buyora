"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState, useSyncExternalStore, type FormEvent } from "react";
import { setSession } from "@/lib/store";
import { Brand, Field, Icon, ThemeToggle } from "./ui";
import { AuthError, login, register } from "@/lib/auth-api";

export function Auth({ mode }: { mode: "login" | "register" | "forgot" }) {
  const router = useRouter();
  const ready = useSyncExternalStore(() => () => {}, () => true, () => false);
  useEffect(() => {
    const url = new URL(window.location.href);
    if (url.searchParams.has("password") || url.searchParams.has("email")) {
      url.searchParams.delete("password");
      url.searchParams.delete("email");
      window.history.replaceState(window.history.state, "", url.pathname + url.search + url.hash);
    }
  }, []);
  const [show, setShow] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  async function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    const email = String(data.get("email") || "").trim();
    const name = String(data.get("name") || "").trim();
    const password = String(data.get("password") || "");
    setError("");
    if (mode === "forgot") {
      setSent(true);
      return;
    }
    if (mode === "register" && !name) {
      setError("Please enter your name.");
      return;
    }
    setPending(true);
    let registered = false;
    try {
      if (mode === "register") {
        await register(email, password, name);
        registered = true;
      }
      const user = await login(email, password);
      setSession(user);
      const next = new URL(window.location.href).searchParams.get("next");
      router.replace(next?.startsWith("/") && !next.startsWith("//") && !next.includes("\\") ? next : "/dashboard");
    } catch (err) {
      const message = err instanceof AuthError ? err.message : "Something went wrong. Please try again.";
      setError(registered ? "Your account was created, but sign in failed. Please sign in from the login page." : message);
    } finally {
      setPending(false);
    }
  }
  return (
    <div className="auth-page">
      <aside className="auth-story">
        <Brand />
        <div>
          {/* <Badge tone="blue">A new perspective for your next post</Badge> */}
          <h1>
            Understand your buyers.
            <br />
            Sell with clarity.
          </h1>
          {/* <p>
            Get to know the questions behind the click. Build better product
            posts with different buyer perspectives.
          </p> */}
          {/* <div className="auth-personas">
            {personas.slice(0, 4).map((p) => (
              <Avatar persona={p} key={p.id} />
            ))}
          </div> */}
          
          <blockquote>
            Build Successful Products
            <br />
            through Agentic Simulations
          </blockquote>
        </div>
        <span>Built for the people behind businesses.</span>
      </aside>
      <main className="auth-main" id="main-content">
        <div className="auth-top">
          <Link href="/" className="text-link">
            <Icon name="back" size={16} />
            Back to home
          </Link>
          <ThemeToggle />
        </div>
        <div className="auth-form">
          <span className="small-brand-mark" />
          <h1>
            {mode === "register"
              ? "A fresh perspective awaits."
              : mode === "forgot"
                ? "Let’s get you back in."
                : "Good to see you"}
          </h1>
          <p>
            {mode === "register"
              ? "Create a profile and make yourself at home."
              : mode === "forgot"
                ? "Enter your email to preview the recovery flow."
                : ""}
          </p>
          {sent ? (
            <div className="recovery-success">
              <span className="small-icon">
                <Icon name="check" size={25} />
              </span>
              <h2>Recovery screen preview</h2>
              <p>
                The recovery request is complete in this frontendo. No email was
                sent. Password recovery will be connected when the backend is
                ready.
              </p>
              <Link href="/login" className="button primary">
                Back to sign in
              </Link>
            </div>
          ) : (
            <form method="post" onSubmit={submit}>
              <noscript>Enable JavaScript to sign in securely.</noscript>
              {mode === "register" && (
                <Field label="Your name">
                  <input
                    required
                    name="name"
                    autoComplete="name"
                    maxLength={80}
                    placeholder="Your name"
                  />
                </Field>
              )}
              <Field label="Email address">
                <input
                  type="email"
                  required
                  name="email"
                  maxLength={180}
                  autoComplete="email"
                  placeholder="you@example.com"
                />
              </Field>
              {mode !== "forgot" && (
                <Field
                  label="Password"
                  hint={mode === "register" ? "Use a unique password with at least 8 characters." : undefined}
                >
                  <div className="password-input">
                    <input
                      name="password"
                      type={show ? "text" : "password"}
                      minLength={mode === "register" ? 8 : 1}
                      required
                      autoComplete={mode === "register" ? "new-password" : "current-password"}
                      placeholder="At least 8 characters"
                    />
                    <button
                      type="button"
                      className="icon-button"
                      aria-label={show ? "Hide password" : "Show password"}
                      onClick={() => setShow((v) => !v)}
                    >
                      <Icon name="eye" size={17} />
                    </button>
                  </div>
                </Field>
              )}
              {mode === "login" && (
                <Link href="/forgot-password" className="forgot-link">
                  Forgot password?
                </Link>
              )}
              {error && (
                <p className="form-error" role="alert">
                  {error}
                </p>
              )}
              <button type="submit" className="button primary auth-submit" disabled={!ready || pending}>
                {pending ? "Please wait?" : mode === "register"
                  ? "Create account"
                  : mode === "forgot"
                    ? "Preview password recovery"
                    : "Sign in "}
                <Icon name="arrow" size={17} />
              </button>
            </form>
          )}
          {mode !== "forgot" && (
            <div className="auth-switch">
              {mode === "login" ? "New to Buyora?" : "Already have a profile?"}{" "}
              <Link href={mode === "login" ? "/register" : "/login"}>
                {mode === "login" ? "Create a account" : "Sign in"}
              </Link>
            </div>
          )}
        </div>
        <span className="auth-footer">
          Simulated perspectives. Thoughtful decisions.
        </span>
      </main>
    </div>
  );
}
