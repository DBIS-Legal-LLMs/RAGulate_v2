import React, { useState } from "react";
import { FocusScope } from "@radix-ui/react-focus-scope";

const BACKEND_URL = "http://134.60.71.197:8000";

interface AuthModalProps {
  onLoginSuccess: (sessions: any, username: string) => void;
}

export function AuthModal({ onLoginSuccess }: AuthModalProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [usernameError, setUsernameError] = useState(false);
  const [passwordError, setPasswordError] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Reset Server Error
    setServerError(null);

    // Client-side Validation pro Feld
    let hasError = false;
    if (!username.trim()) {
      setUsernameError(true);
      setServerError("Please enter username")
      hasError = true;
    }
    if (!password.trim()) {
      setPasswordError(true);
      setServerError("Please enter password")
      hasError = true;
    }
    if (hasError) return;

    // Alles validiert → Login/Register starten
    setLoading(true);

    try {
      if (mode === "login") {
        const res = await fetch(BACKEND_URL + "/api/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password }),
        });
        const data = await res.json();
        if (res.ok) {
          onLoginSuccess(data.sessions, username);
        } else {
          setServerError(data.error || "Login failed");
        }
      } else {
        const res = await fetch(BACKEND_URL + "/api/register", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password }),
        });
        const data = await res.json();
        if (res.ok) {
          // Optional: direkt einloggen
          const loginRes = await fetch(BACKEND_URL + "/api/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password }),
          });
          const loginData = await loginRes.json();
          if (loginRes.ok) {
            onLoginSuccess(loginData.sessions, username);
          } else {
            setMode("login");
            setServerError("Registration successful, but login failed. Please try logging in.");
          }
        } else {
          setServerError(data.error || "Registration failed");
        }
      }
    } catch (err) {
      setServerError("Network error");
    } finally {
      setLoading(false);
    }
  };

  return (
    
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40">
        <FocusScope trapped>
        <div className="bg-sidebar rounded-lg border border-sidebar-border shadow-lg p-8 w-full max-w-sm relative">
          <h2 className="text-xl font-bold mb-4 text-center">{mode === "login" ? "Login" : "Register"}</h2>
          
          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <input
              autoFocus
              tabIndex={0}
              type="text"
              placeholder="Username"
              value={username}
              onChange={e => {
                setUsername(e.target.value);
                if (usernameError) setUsernameError(false);
              }}
              className={`bg-primary w-full px-3 py-2 border rounded
                ${usernameError ? "border-red-500 placeholder-red-500" : "border-sidebar-border"}`}
            />
            <input
              tabIndex={0}
              type="password"
              placeholder="Password"
              value={password}
              onChange={e => {
                setPassword(e.target.value);
                if (passwordError) setPasswordError(false);
              }}
              className={`bg-primary w-full px-3 py-2 border rounded
                ${passwordError ? "border-red-500 placeholder-red-500" : "border-sidebar-border"}`}
            />
            <button
              tabIndex={0}
              type="submit"
              className="w-full bg-primary py-2 rounded hover:bg-accent hover:text-black disabled:opacity-50 focus:bg-accent"
              disabled={loading}
            >
              {loading ? "Processing..." : mode === "login" ? "Login" : "Register"}
            </button>
          </form>
          {/* Server Error */}
          {serverError && <div className="text-red-600 text-sm mt-2 text-center">{serverError}</div>}

          <div className="mt-4 text-center">
            {mode === "login" ? (
              <span>
                Don't have an account?{" "}
                <button
                  tabIndex={0}
                  className="text-blue-600 underline"
                  onClick={() => {
                    setMode("register");
                    setServerError(null);
                    setUsernameError(false);
                    setPasswordError(false);
                  }}
                  type="button"
                >
                  Register
                </button>
              </span>
            ) : (
              <span>
                Already have an account?{" "}
                <button
                  tabIndex={0}
                  className="text-blue-600 underline"
                  onClick={() => {
                    setMode("login");
                    setServerError(null);
                    setUsernameError(false);
                    setPasswordError(false);
                  }}
                  type="button"
                >
                  Login
                </button>
              </span>
            )}
          </div>
        </div>
        </FocusScope>
        </div>
      
  );
}
