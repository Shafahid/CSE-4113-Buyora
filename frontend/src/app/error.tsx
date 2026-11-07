"use client";
import { ButtonLink, EmptyState } from "@/components/ui";
export default function Error({
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <main className="not-found" id="main-content">
      <EmptyState
        title="This page needs another moment."
        description="Your saved workspace is still in this browser. Try again or return to your overview."
      >
        <button className="button primary" onClick={reset}>
          Try again
        </button>
        <ButtonLink href="/dashboard" secondary>
          Back to workspace
        </ButtonLink>
      </EmptyState>
    </main>
  );
}
