import { jsonBody, request } from "./api-client";
import type { ApiSchemas } from "./api-schema";

export { ApiError as AuthError } from "./api-client";
export type AuthUser = ApiSchemas["PublicUser"];

export function register(email: string, password: string, display_name: string) {
  const data: ApiSchemas["Registration"] = { email, password, display_name };
  return request<AuthUser>("/auth/register", { method: "POST", ...jsonBody(data) });
}
export function login(email: string, password: string) {
  const data: ApiSchemas["Credentials"] = { email, password };
  return request<AuthUser>("/auth/login", { method: "POST", ...jsonBody(data) });
}
export function currentUser() {
  return request<AuthUser>("/me");
}
export function logout() {
  return request<void>("/auth/logout", { method: "POST" });
}
