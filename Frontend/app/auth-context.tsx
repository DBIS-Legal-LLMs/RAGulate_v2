"use client";

import React, { createContext, useContext, useEffect, useState } from "react";
import {
  clearStoredSession,
  readStoredToken,
  REFRESH_AHEAD_SECONDS,
  storeSession,
  tokenExpiresWithin,
  USERNAME_KEY,
} from "@/lib/auth-storage";
import { refreshSession, SESSION_ENDED_EVENT, TOKEN_CHANGED_EVENT } from "@/lib/client-session";

export const AUTH_SERVICE_URL =
  process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || "http://localhost:8100";

interface AuthContextValue {
  token: string | null;
  username: string | null;
  userId: string | null;
  isLoading: boolean;
  login: (usernameOrEmail: string, password: string) => Promise<void>;
  register: (email: string, username: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

async function extractErrorDetail(res: Response, fallback: string): Promise<string> {
  try {
    const data = await res.json();
    if (Array.isArray(data.detail)) {
      return data.detail.map((e: any) => e.msg).join(", ");
    }
    return data.detail || fallback;
  } catch {
    return fallback;
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setToken] = useState<string | null>(null);
  const [username, setUsername] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const syncFromStorage = () => {
    setToken(readStoredToken());
    setUsername(localStorage.getItem(USERNAME_KEY));
  };

  useEffect(() => {
    // A valid stored access token is used as it is. An expired or missing one is renewed with the refresh
    // cookie before the page decides the user is logged out; a rejected refresh ends up logged out.
    const storedToken = readStoredToken();
    const start =
      storedToken && !tokenExpiresWithin(storedToken, REFRESH_AHEAD_SECONDS)
        ? Promise.resolve()
        : refreshSession().then(() => undefined);
    start.then(() => {
      syncFromStorage();
      setIsLoading(false);
    });

    // refreshSession() (authenticated-fetch.ts) reports renewed and ended sessions as window events
    const onChanged = () => syncFromStorage();
    const onEnded = () => {
      setToken(null);
      setUsername(null);
    };
    window.addEventListener(TOKEN_CHANGED_EVENT, onChanged);
    window.addEventListener(SESSION_ENDED_EVENT, onEnded);
    return () => {
      window.removeEventListener(TOKEN_CHANGED_EVENT, onChanged);
      window.removeEventListener(SESSION_ENDED_EVENT, onEnded);
    };
  }, []);

  const login = async (usernameOrEmail: string, password: string) => {
    // The route handler talks to auth-service and keeps the refresh token in an httpOnly cookie.
    const res = await fetch("/api/session/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: usernameOrEmail, password }),
    });
    if (!res.ok) {
      throw new Error(await extractErrorDetail(res, "Login failed"));
    }
    const data = await res.json();
    storeSession(data.access_token, data.user.username);
    setToken(data.access_token);
    setUsername(data.user.username);
  };

  const register = async (email: string, registerUsername: string, password: string) => {
    const res = await fetch(`${AUTH_SERVICE_URL}/auth/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "application/json" },
      body: JSON.stringify({ email, username: registerUsername, password }),
    });
    if (!res.ok) {
      throw new Error(await extractErrorDetail(res, "Registration failed"));
    }
    // Registration doesn't return a token — chain a login.
    await login(email, password);
  };

  const logout = async () => {
    // Revokes the session at auth-service and clears the refresh cookie; the local state is cleared either way.
    try {
      await fetch("/api/session/logout", { method: "POST", credentials: "same-origin" });
    } catch {
      /* the cookie and the refresh token expire on their own */
    }
    clearStoredSession();
    setToken(null);
    setUsername(null);
  };

  const userId = token ? decodeSubject(token) : null;

  return (
    <AuthContext.Provider value={{ token, username, userId, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

// Not signature-verified — display only, the backend independently verifies signatures.
function decodeSubject(token: string): string | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    return typeof payload.sub === "string" ? payload.sub : null;
  } catch {
    return null;
  }
}
