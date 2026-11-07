import { Brand, ButtonLink, EmptyState } from "@/components/ui";
export default function NotFound() {
  return (
    <main className="not-found" id="main-content">
      <Brand />
      <EmptyState
        title="A little off the beaten path."
        description="We couldn’t find this page. Your workspace is a good place to start."
      >
        <ButtonLink href="/dashboard">Back to workspace</ButtonLink>
      </EmptyState>
    </main>
  );
}
