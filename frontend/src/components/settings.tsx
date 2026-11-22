"use client";
import { useState, type FormEvent } from "react";
import Link from "next/link";
import { download, resetDemo, updateDemo, useDemo, clearSession } from "@/lib/store";
import { AuthError, logout } from "@/lib/auth-api";
import { useRouter } from "next/navigation";
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
  const router = useRouter();
  const [signingOut, setSigningOut] = useState(false);
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
              <p>{state.signedIn ? "Your account details." : "Personalize this local demo workspace."}</p>
            </div>
            <Badge tone="blue">{state.signedIn ? "Account" : "Demo workspace"}</Badge>
          </div>
          <form onSubmit={save}>
            <div className="form-grid">
              <Field label="Your name">
                <input
                  required
                  disabled={state.signedIn}
                  maxLength={80}
                  value={name ?? state.profile.name}
                  onChange={(e) => setName(e.target.value)}
                />
              </Field>
              <Field label="Email address">
                <input
                  required
                  disabled={state.signedIn}
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
            {!state.signedIn && <button className="button primary" type="submit">Save profile</button>}
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
              <h3>Session</h3>
              <p>
                {state.signedIn
                  ? "You are signed in to your account."
                  : "You are exploring without signing in."}
              </p>
            </div>
            {state.signedIn ? (
              <button
                className="button secondary small-button"
                disabled={signingOut}
                onClick={async () => {
                  setSigningOut(true);
                  try {
                    await logout();
                    clearSession();
                    router.replace("/login");
                  } catch (err) {
                    setError(err instanceof AuthError ? err.message : "Could not sign out.");
                  } finally {
                    setSigningOut(false);
                  }
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
              <p>Products and posts are saved to your account. Simulation previews remain in this browser.</p>
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
            Clearing browser data removes local simulation drafts and demo reports.
            Your server products, images, post versions, and simulation reports are preserved.
          </Notice>
          <div className="settings-row">
            <div>
              <h3>Clear simulation previews</h3>
              <p>Remove this account’s local draft and demo reports.</p>
            </div>
            <button
              className="button secondary small-button danger-text"
              onClick={() => setReset(true)}
            >
              Clear previews
            </button>
          </div>
        </section>
      </div>
      <Notice>
        Profile updates and password recovery are pending backend support.
        Simulation results are saved to your account. Buyer reactions are fictional and should be used as guidance.
      </Notice>
      {reset && (
        <Modal
          title="Clear local simulation previews?"
          onClose={() => setReset(false)}
        >
          <p>
            This removes this account’s local simulation draft and demo reports.
            Export a copy first if needed. Products, images, and post versions
            saved on the server are preserved.
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
                toast("Local simulation previews cleared");
              }}
            >
              Clear previews
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}
