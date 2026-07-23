/**
 * Auth API calls. All go through the shared axios client, so the access
 * token (once set) is attached automatically by its interceptor.
 */
import client, { setTokens, clearTokens } from "./client";

export async function register(email, password) {
  const { data } = await client.post("/auth/register", { email, password });
  return data;
}

export async function login(email, password) {
  const { data } = await client.post("/auth/login", { email, password });
  setTokens(data);
  return data;
}

export async function getCurrentUser() {
  const { data } = await client.get("/auth/me");
  return data;
}

export function logout() {
  clearTokens();
}