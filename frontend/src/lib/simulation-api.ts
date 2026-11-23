import { jsonBody, request } from "./api-client";
import type { ApiSchemas } from "./api-schema";
import type { Report } from "./demo-data";
import { validReport } from "./persistence";

export type SimulationRun = ApiSchemas["RunResponse"];
export const finishedRun = (run: SimulationRun) => ["completed", "partially_failed", "failed"].includes(run.status);
export function reportFromRun(run: SimulationRun): Report | null {
  if (!run.report) return null;
  if (!validReport(run.report)) throw new Error("The saved simulation report is invalid. Please reload it.");
  return run.report as Report;
}
export const simulationApi = {
  adapt: (data: ApiSchemas["PersonaAdaptRequest"]) => request<ApiSchemas["PersonaAdaptResponse"]>("/persona-adaptations", { method: "POST", ...jsonBody(data) }),
  adaptation: (id: string, signal?: AbortSignal) => request<ApiSchemas["PersonaAdaptResponse"]>(`/persona-adaptations/${id}`, { signal }),
  revise: (id: string, applied: string[]) => request<SimulationRun>(`/simulation-runs/${id}/revise`, { method: "POST", ...jsonBody({ applied }) }),
  options: () => request<ApiSchemas["SimulationOptions"]>("/simulation-options"),
  start: (data: ApiSchemas["RunCreate"]) => request<SimulationRun>("/simulation-runs", { method: "POST", ...jsonBody(data) }),
  run: (id: string, signal?: AbortSignal) => request<SimulationRun>(`/simulation-runs/${id}`, { signal }),
  progress: (id: string, signal?: AbortSignal) => request<ApiSchemas["RunProgress"]>(`/simulation-runs/${id}/progress`, { signal }),
  preview: (data: ApiSchemas["RunPreview"], signal?: AbortSignal) => request<ApiSchemas["PreviewResponse"]>("/simulation-runs/preview", { method: "POST", ...jsonBody(data), signal }),
  retryFailed: (id: string, requestId: string) => request<SimulationRun>(`/simulation-runs/${id}/retry-failed`, { method: "POST", ...jsonBody({ request_id: requestId }) }),
  async runs() {
    const runs: SimulationRun[] = [];
    for (let offset = 0; ; offset += 100) {
      const page = await request<SimulationRun[]>(`/simulation-runs?offset=${offset}&limit=100`);
      runs.push(...page);
      if (page.length < 100) return runs;
    }
  },
  retry: (id: string, evaluationId: number) => request<SimulationRun>(`/simulation-runs/${id}/retry`, { method: "POST", ...jsonBody({ evaluation_id: evaluationId }) }),
  saveReport: (id: string, revised: string, applied: string[]) => request<SimulationRun>(`/simulation-runs/${id}/report`, { method: "PATCH", ...jsonBody({ revised, applied }) }),
  remove: (id: string) => request<void>(`/simulation-runs/${id}`, { method: "DELETE" }),
};
