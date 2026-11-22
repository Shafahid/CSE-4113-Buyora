import { Simulation } from "@/components/simulation";
export default async function Page({ searchParams }: { searchParams: Promise<{ run?: string }> }) {
  const { run } = await searchParams;
  const id = run && /^[0-9a-f-]{36}$/i.test(run) ? run : undefined;
  return <Simulation key={id ?? "setup"} initialRunId={id} />;
}
