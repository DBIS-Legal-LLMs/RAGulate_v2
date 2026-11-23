// Browser-side session state. The access token (a short-lived JWT) and the username live in
// localStorage, as before. The refresh token is never here: it is an httpOnly cookie
// (`REFRESH_COOKIE_NAME`) that only the route handlers under app/api/session can read.
export const TOKEN_KEY = "token";
export const USERNAME_KEY = "username";
export const REFRESH_COOKIE_NAME = "ragulate_refresh";

// The refresh token lives 30 days from the login (auth-service); the access token's own `exp` is much shorter.
export const SESSION_MAX_AGE_SECONDS = 60 * 60 * 24 * 30;

/** Renew the access token this many seconds before it expires, instead of failing a request first. */
export const REFRESH_AHEAD_SECONDS = 30;

export function readStoredToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function storeSession(accessToken: string, username?: string): void {
  localStorage.setItem(TOKEN_KEY, accessToken);
  if (username) localStorage.setItem(USERNAME_KEY, username);
}

export function clearStoredSession(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(USERNAME_KEY);
}

/** True when the token is unreadable or expires within `seconds`. Not signature-verified: the backend does that. */
export function tokenExpiresWithin(token: string, seconds: number): boolean {
  try {
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    return typeof payload.exp === "number" && payload.exp * 1000 < Date.now() + seconds * 1000;
  } catch {
    return true;
  }
}
