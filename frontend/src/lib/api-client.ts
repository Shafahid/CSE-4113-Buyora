export class ApiError extends Error {
  constructor(message: string, readonly status?: number, readonly fields: Record<string, string> = {}) {
    super(message);
    this.name = "ApiError";
  }
}
export const unauthorizedEvent = "buyora:unauthorized";

export async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const baseUrl = (process.env.NEXT_PUBLIC_API_URL ||
    (typeof window === "undefined" ? "http://localhost:8000" :
      `${window.location.protocol}//${window.location.hostname}:8000`)).replace(/\/$/, "");
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 20000);
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  let response: Response;
  try {
    response = await fetch(baseUrl + path, {
      ...options, headers, credentials: "include", cache: "no-store",
      signal: options.signal ? AbortSignal.any([options.signal, controller.signal]) : controller.signal,
    });
  } catch {
    throw new ApiError(controller.signal.aborted ? "The server took too long to respond. Please try again." :
      "Could not reach the server. Check that the backend is running.");
  } finally { clearTimeout(timeout); }
  if (!response.ok) {
    const data: unknown = await response.json().catch(() => null);
    const detail = data && typeof data === "object" && "detail" in data ? data.detail : null;
    const fields: Record<string, string> = {};
    if (Array.isArray(detail)) {
      for (const item of detail) {
        if (item && Array.isArray(item.loc) && typeof item.msg === "string") {
          fields[item.loc.filter((part: unknown) => part !== "body").join(".")] = item.msg;
        }
      }
    }
    if (response.status === 401 && typeof window !== "undefined") window.dispatchEvent(new Event(unauthorizedEvent));
    const fallback: Record<number, string> = {
      401: "Your session has expired. Please sign in again.",
      403: "This request is not allowed. Check the frontend origin configuration.",
      404: "This item is no longer available.",
      409: "This change conflicts with the current saved data. Please reload and try again.",
      422: "Check the supplied details.",
    };
    throw new ApiError(typeof detail === "string" ? detail :
      Object.entries(fields).map(([field, message]) => `${field}: ${message}`).join("; ") ||
      fallback[response.status] || "The request failed. Please try again.", response.status, fields);
  }
  if (response.status === 204) return undefined as T;
  try { return await response.json() as T; }
  catch { throw new ApiError("The server returned an unreadable response.", response.status); }
}
export const jsonBody = (data: unknown): Pick<RequestInit, "body"> => ({ body: JSON.stringify(data) });
export const errorMessage = (error: unknown) => error instanceof Error ? error.message : "Something went wrong. Please try again.";
