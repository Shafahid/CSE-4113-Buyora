"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";
import { updateDemo } from "@/lib/store";
import { Avatar, Brand, Field, Icon, ThemeToggle } from "./ui";
import { personas } from "@/lib/demo-data";

export function Auth({ mode }: { mode: "login" | "register" | "forgot" }) {
  const router = useRouter();
  const [show, setShow] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");
  function submit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const data = new FormData(e.currentTarget);
    const email = String(data.get("email")).trim();
    const name = String(data.get("name") || email.split("@")[0]).trim();
    if (mode === "forgot") {
      setSent(true);
      return;
    }
    if (!name) {
      setError("Please enter your name.");
      return;
    }
    updateDemo((s) => ({ ...s, signedIn: true, profile: { name, email } }));
    router.push("/dashboard");
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
            <form onSubmit={submit}>
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
                  hint="Use any 8+ characters. Please don’t use a real password."
                >
                  <div className="password-input">
                    <input
                      name="password"
                      type={show ? "text" : "password"}
                      minLength={8}
                      required
                      autoComplete="off"
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
              <button className="button primary auth-submit">
                {mode === "register"
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
