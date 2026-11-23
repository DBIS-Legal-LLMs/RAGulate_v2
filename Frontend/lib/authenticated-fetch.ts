"use client";

import { readStoredToken, REFRESH_AHEAD_SECONDS, tokenExpiresWithin } from "@/lib/auth-storage";
import { refreshSession } from "@/lib/client-session";

// Drop-in replacement for fetch() that attaches the logged-in user's bearer token, for calls to the backend.
// The access token is short-lived: it is renewed shortly before it expires, and once more (with the request
// repeated once) after a 401. A repeated request is sent again with the same `init`, so a body must be
// re-readable (string, FormData, Blob).
export async function authenticatedFetch(input: RequestInfo | URL, init: RequestInit = {}): Promise<Response> {
  let token = readStoredToken();
  if ((!token || tokenExpiresWithin(token, REFRESH_AHEAD_SECONDS)) && (await refreshSession())) {
    token = readStoredToken();
  }

  const response = await send(input, init, token);
  if (response.status !== 401 || !(await refreshSession())) return response;
  return send(input, init, readStoredToken());
}

function send(input: RequestInfo | URL, init: RequestInit, token: string | null): Promise<Response> {
  const headers = new Headers(init.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return fetch(input, { ...init, headers });
}
