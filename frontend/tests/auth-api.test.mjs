import { test, afterEach } from "node:test";
import assert from "node:assert/strict";
import { createTypeScriptLoader } from "./load-typescript.mjs";

const api = await createTypeScriptLoader()("../src/lib/auth-api.ts");
const originalFetch = globalThis.fetch;
afterEach(() => { globalThis.fetch = originalFetch; });

test("authentication requests send credentials and expected data", async () => {
  const calls = [];
  globalThis.fetch = async (url, options) => {
    calls.push({ url, options });
    return url.endsWith("/auth/logout") ? new Response(null, { status: 204 }) : Response.json({ id: 1, email: "seller@example.com", display_name: "Seller" });
  };
  await api.register("seller@example.com", "password123", "Seller");
  await api.login("seller@example.com", "password123");
  await api.currentUser();
  await api.logout();
  assert.deepEqual(calls.map((c) => new URL(c.url).pathname), ["/auth/register", "/auth/login", "/me", "/auth/logout"]);
  for (const call of calls) assert.equal(call.options.credentials, "include");
  assert.deepEqual(JSON.parse(calls[0].options.body), { email: "seller@example.com", password: "password123", display_name: "Seller" });
});

test("authentication errors preserve status and describe network failures", async () => {
  globalThis.fetch = async () => Response.json({ detail: "Invalid email or password" }, { status: 401 });
  await assert.rejects(api.login("seller@example.com", "bad"), (error) => error instanceof api.AuthError && error.status === 401 && error.message === "Invalid email or password");
  globalThis.fetch = async () => { throw new TypeError("network"); };
  await assert.rejects(api.currentUser(), /Could not reach the server/);
});
