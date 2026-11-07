"use client";
import { useState, type FormEvent } from "react";
import Link from "next/link";
import { download, resetDemo, updateDemo, useDemo } from "@/lib/store";
import {
  Badge,
  Field,
  Icon,
  Modal,
  Notice,
  PageHeading,
  ThemeToggle,
  useToast,
} from "./ui";

export function Settings() {
  const state = useDemo();
  const toast = useToast();
  const [name, setName] = useState<string | null>(null);
  const [email, setEmail] = useState<string | null>(null);
  const [reset, setReset] = useState(false);
  const [error, setError] = useState("");
  function save(e: FormEvent) {
    e.preventDefault();
    const n = (name ?? state.profile.name).trim();
    if (!n) {
      setError("Enter a name containing more than spaces.");
      return;
    }
    setError("");
    updateDemo((s) => ({
      ...s,
      profile: { name: n, email: email ?? s.profile.email },
    }));
    toast("Demo profile saved");
  }
  return (
    <>
      <PageHeading
        eyebrow="Settings"
        title="Make yourself at home."
        description="A few preferences for your workspace."
      />
      <div className="settings-grid">
        <section className="panel settings-panel">
          <div className="panel-heading">
            <div>
              <h2>Your profile</h2>
              <p>Personalize this local demo workspace.</p>
            </div>
            <Badge tone="blue">Demo account</Badge>
          </div>
          <form onSubmit={save}>
            <div className="form-grid">
              <Field label="Your name">
                <input
                  required
                  maxLength={80}
                  value={name ?? state.profile.name}
                  onChange={(e) => setName(e.target.value)}
                />
              </Field>
              <Field label="Email address">
                <input
                  required
                  type="email"
                  maxLength={180}
                  value={email ?? state.profile.email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </Field>
            </div>
            {error && (
              <p className="form-error" role="alert">
                {error}
              </p>
            )}
            <button className="button primary" type="submit">
              Save profile
            </button>
          </form>
          <div className="settings-row">
            <div>
              <h3>Appearance</h3>
              <p>Your theme follows your device until you choose one.</p>
            </div>
            <ThemeToggle />
          </div>
          <div className="settings-row">
            <div>
              <h3>Demo session</h3>
              <p>
                {state.signedIn
                  ? "You are signed in to a local demo session."
                  : "You are exploring without signing in."}
              </p>
            </div>
            {state.signedIn ? (
              <button
                className="button secondary small-button"
                onClick={() => {
                  updateDemo((s) => ({ ...s, signedIn: false }));
                  toast("Signed out of demo session");
                }}
              >
                Sign out
              </button>
            ) : (
              <Link href="/login" className="button secondary small-button">
                Sign in
              </Link>
            )}
          </div>
        </section>
        <section className="panel settings-panel">
          <div className="panel-heading">
            <div>
              <h2>Your workspace data</h2>
              <p>Products, drafts, and reports live in this browser.</p>
            </div>
            <Icon name="shield" size={21} />
          </div>
          <div className="data-counts">
            <div>
              <strong>{state.products.length}</strong>
              <span>Products</span>
            </div>
            <div>
              <strong>{state.posts.length}</strong>
              <span>Posts</span>
            </div>
            <div>
              <strong>{state.reports.length}</strong>
              <span>Reports</span>
            </div>
          </div>
          <button
            className="button secondary"
            onClick={() =>
              download("buyora-workspace.json", JSON.stringify(state, null, 2))
            }
          >
            <Icon name="download" size={16} />
            Export workspace
          </button>
          <Notice>
            Browser storage is local to this device and profile. Clearing
            browser data removes your demo workspace. Export a copy if you want
            to keep it.
          </Notice>
          <div className="settings-row">
            <div>
              <h3>Start with fresh sample data</h3>
              <p>Replace your changes with the original demo.</p>
            </div>
            <button
              className="button secondary small-button danger-text"
              onClick={() => setReset(true)}
            >
              Reset demo
            </button>
          </div>
        </section>
      </div>
      <Notice>
        Authentication, password recovery, AI generation, and server
        synchronization are frontend demonstrations. They will need backend
        integration before real use. No passwords are stored.
      </Notice>
      {reset && (
        <Modal
          title="Reset this demo workspace?"
          onClose={() => setReset(false)}
        >
          <p>
            Your products, post versions, drafts, and reports will be replaced
            with the original sample data. Export your workspace first if you
            want to keep a copy.
          </p>
          <div className="modal-actions">
            <button
              className="button secondary"
              onClick={() => setReset(false)}
            >
              Keep my changes
            </button>
            <button
              className="button danger"
              onClick={() => {
                resetDemo();
                setName(null);
                setEmail(null);
                setReset(false);
                toast("Demo workspace reset");
              }}
            >
              Reset demo
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}
