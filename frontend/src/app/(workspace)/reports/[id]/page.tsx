import { ReportView } from "@/components/report";
export default async function Page({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ view?: string }>;
}) {
  const { id } = await params;
  const { view } = await searchParams;
  return (
    <ReportView
      key={`${id}:${view || "overview"}`}
      id={id}
      initialTab={view === "spread" ? 2 : 0}
    />
  );
}
