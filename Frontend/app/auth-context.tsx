"use client";

import React, { createContext, useContext, useEffect, useState } from "react";

export const AUTH_SERVICE_URL =
  process.env.NEXT_PUBLIC_AUTH_SERVICE_URL || "http://localhost:8100";

interface AuthContextValue {
  token: string | null;
  username: string | null;
  userId: string | null;
  isLoading: boolean;
  login: (usernameOrEmail: string, password: string) => Promise<void>;
  register: (email: string, username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}

function isExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    return typeof payload.exp === "number" && payload.exp * 1000 < Date.now();
  } catch {
    return true;
  }
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

  useEffect(() => {
    const storedToken = localStorage.getItem("token");
    const storedUsername = localStorage.getItem("username");
    if (storedToken && storedUsername && !isExpired(storedToken)) {
      setToken(storedToken);
      setUsername(storedUsername);
    } else if (storedToken) {
      // Expired — don't carry a dead session forward.
      localStorage.removeItem("token");
      localStorage.removeItem("username");
    }
    setIsLoading(false);
  }, []);

  const login = async (usernameOrEmail: string, password: string) => {
    const body = new URLSearchParams();
    body.set("grant_type", "password");
    body.set("username", usernameOrEmail);
    body.set("password", password);

    const res = await fetch(`${AUTH_SERVICE_URL}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    if (!res.ok) {
      throw new Error(await extractErrorDetail(res, "Login failed"));
    }
    const data = await res.json();
    localStorage.setItem("token", data.access_token);
    localStorage.setItem("username", data.user.username);
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

  const logout = () => {
    localStorage.removeItem("token");
    localStorage.removeItem("username");
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
