"use client";

import { clearStoredSession, storeSession } from "@/lib/auth-storage";

// Browser side of the refresh-token session. The refresh token itself is httpOnly and never visible here:
// the api/session/refresh route handler reads it, calls auth-service and sets the new cookie; this file only asks.
//
// AuthProvider listens to these two window events instead of being called, so any fetch helper can refresh
// without knowing about React.
export const TOKEN_CHANGED_EVENT = "ragulate:token-changed";
export const SESSION_ENDED_EVENT = "ragulate:session-ended";

let inFlight: Promise<boolean> | null = null;

/** Gets a new access token with the refresh cookie. One request at a time: callers that arrive while it runs share it.
 * Resolves true when a new access token was stored. A refresh that auth-service rejects ends the session (login
 * modal); one that merely could not be made (network, auth-service down) does not. */
export function refreshSession(): Promise<boolean> {
  inFlight ??= requestRefresh().finally(() => {
    inFlight = null;
  });
  return inFlight;
}

async function requestRefresh(): Promise<boolean> {
  let res: Response;
  try {
    res = await fetch("/api/session/refresh", { method: "POST", credentials: "same-origin" });
  } catch {
    return false;
  }
  if (res.status === 401) {
    clearStoredSession();
    window.dispatchEvent(new Event(SESSION_ENDED_EVENT));
    return false;
  }
  if (!res.ok) return false;
  const data = await res.json();
  storeSession(data.access_token, data.user?.username);
  window.dispatchEvent(new Event(TOKEN_CHANGED_EVENT));
  return true;
}
