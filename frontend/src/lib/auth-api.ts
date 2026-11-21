export type AuthUser = { id: number; email: string; display_name: string };

const baseUrl = (
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window === "undefined"
    ? "http://localhost:8000"
    : `${window.location.protocol}//${window.location.hostname}:8000`)
).replace(/\/$/, "");

export class AuthError extends Error {
  constructor(message: string, readonly status?: number) {
    super(message);
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  let response: Response;
  try {
    response = await fetch(baseUrl + path, {
      ...options,
      credentials: "include",
      headers: { "Content-Type": "application/json", ...options.headers },
      cache: "no-store",
    });
  } catch {
    throw new AuthError("Could not reach the server. Check that the backend is running.");
  }
  if (!response.ok) {
    const data: unknown = await response.json().catch(() => null);
    const detail = typeof data === "object" && data !== null && "detail" in data && typeof data.detail === "string" ? data.detail : "";
    throw new AuthError(detail || "Something went wrong. Please try again.", response.status);
  }
  return response.status === 204 ? undefined as T : response.json() as Promise<T>;
}

export function register(email: string, password: string, display_name: string) {
  return request<AuthUser>("/auth/register", { method: "POST", body: JSON.stringify({ email, password, display_name }) });
}
export function login(email: string, password: string) {
  return request<AuthUser>("/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
}
export function currentUser() {
  return request<AuthUser>("/me");
}
export function logout() {
  return request<void>("/auth/logout", { method: "POST" });
}
