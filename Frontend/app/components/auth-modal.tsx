import React, { useEffect, useState } from "react";
import { FocusScope } from "@radix-ui/react-focus-scope";
import { useTranslation } from "react-i18next";

const BACKEND_URL = "http://134.60.71.197:8000";

interface AuthModalProps {
  onLoginSuccess: (sessions: any, username: string) => void;
}

export function AuthModal({ onLoginSuccess }: AuthModalProps) {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [emailError, setEmailError] = useState(false);
  const [usernameError, setUsernameError] = useState(false);
  const [passwordError, setPasswordError] = useState(false);
  const [serverError, setServerError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const { t } = useTranslation();

  useEffect(() => {
    if (mode === "register" && !username) {
      fetchGeneratedUsername();
    }
  }, [mode]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Reset Server Error
    setServerError(null);

    // Client-side Validation pro Feld
    let hasError = false;
    if (!email.trim()) {
      setEmailError(true);
      setServerError(t("auth.errors.enterEmail"));
      hasError = true;
    }
    if (!password.trim()) {
      setPasswordError(true);
      setServerError(t("auth.errors.enterPassword"));
      hasError = true;
    }
    if (mode === "register" && !username.trim()) {
      setUsernameError(true);
      setServerError(t("auth.errors.enterUsername"));
      hasError = true;
    }

    if (mode === "register" && !isPasswordValid) {
      setPasswordError(true);
      setServerError(t("auth.errors.passwordInvalid"));
      return;
    }

    if (hasError) return;

    // Alles validiert → Login/Register starten
    setLoading(true);

    try {
      if (mode === "login") {
        const params = new URLSearchParams();
        params.append("grant_type", "password");
        params.append("username", email);
        params.append("password", password);
        const res = await fetch(BACKEND_URL + "/api/auth/login", {
          method: "POST",
          headers: {
            "Content-Type": "application/x-www-form-urlencoded",
          },
          body: params,
        });
        const data = await res.json();
        if (res.ok) {
          localStorage.setItem("token", data.access_token);
          onLoginSuccess(data.sessions, data.user.username);
        } else {
          setServerError(data.detail || t("auth.errors.loginFailed"));
        }
      } else {
        const res = await fetch(BACKEND_URL + "/api/auth/register", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({
            email: email,
            username: username,
            password: password,
          }),
        });
        const data = await res.json();
        if (res.ok) {
          // Optional: direkt einloggen
          const params = new URLSearchParams();
          params.append("grant_type", "password");
          params.append("username", email);
          params.append("password", password);
          const loginRes = await fetch(BACKEND_URL + "/api/auth/login", {
            method: "POST",
            headers: {
              "Content-Type": "application/x-www-form-urlencoded",
            },
            body: params,
          });
          const loginData = await loginRes.json();
          if (loginRes.ok) {
            localStorage.setItem("token", loginData.access_token);
            onLoginSuccess(loginData.sessions, data.username);
          } else {
            setMode("login");
            setServerError(t("auth.errors.registerSuccessLoginFailed"));
          }
        } else {
          const detail = data.detail;
          if (Array.isArray(detail)) {
            setServerError(detail.map((e: any) => e.msg).join(", "));
          } else {
            setServerError(detail || t("auth.errors.registerFailed"));
          }
        }
      }
    } catch (err) {
      setServerError(t("auth.errors.networkError"));
    } finally {
      setLoading(false);
    }
  };

  const passwordRules = {
    length: (pw: string) => pw.length >= 8,
    upper: (pw: string) => /[A-Z]/.test(pw),
    lower: (pw: string) => /[a-z]/.test(pw),
    number: (pw: string) => /[0-9]/.test(pw),
    special: (pw: string) => /[^A-Za-z0-9]/.test(pw),
  };

  const passwordValidation = {
    length: passwordRules.length(password),
    upper: passwordRules.upper(password),
    lower: passwordRules.lower(password),
    number: passwordRules.number(password),
    special: passwordRules.special(password),
  };

  const isPasswordValid = Object.values(passwordValidation).every(Boolean);

  const PasswordRuleItem = ({
    valid,
    text,
  }: {
    valid: boolean;
    text: string;
  }) => (
    <li
      className={`flex items-center gap-2 font-semibold ${
        valid ? "text-green-600" : "text-red-600"
      }`}
      aria-label={`${text} ${valid ? "fulfilled" : "not fulfilled"}`}
    >
      <span aria-hidden="true">{valid ? "✓" : "✗"}</span>
      <span>{text}</span>
    </li>
  );

  const fetchGeneratedUsername = async () => {
    try {
      const res = await fetch(BACKEND_URL + "/api/auth/register/genuser", {
        method: "GET",
        headers: {
          Accept: "application/json",
        },
      });

      if (!res.ok) {
        throw new Error("Failed to generate username");
      }

      const generatedUsername = await res.text();
      const cleanedUsername = generatedUsername.replace(/"/g, "");
      setUsername(cleanedUsername);
    } catch (err) {
      console.error(err);
      setServerError(t("auth.errors.usernameGenFailed"));
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40">
      <FocusScope trapped>
        <div className="bg-sidebar rounded-lg border border-sidebar-border shadow-lg p-8 w-full max-w-sm relative">
          <h2 className="text-xl font-bold mb-4 text-center">
            {mode === "login" ? t("auth.login") : t("auth.register")}
          </h2>

          <form onSubmit={handleSubmit} noValidate className="space-y-4">
            <input
              autoFocus
              tabIndex={0}
              type="text"
              placeholder={
                mode === "login"
                  ? t("auth.placeholderEmailOrUsername")
                  : t("auth.placeholderEmail")
              }
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                if (emailError) setEmailError(false);
              }}
              className={`bg-primary w-full px-3 py-2 border rounded
                ${
                  emailError
                    ? "border-red-500 placeholder-red-500"
                    : "border-sidebar-border"
                }`}
            />

            {mode === "register" && (
              <input
                tabIndex={0}
                type="text"
                placeholder={t("auth.placeholderUsername")}
                value={username}
                onChange={(e) => {
                  setUsername(e.target.value);
                  if (usernameError) setUsernameError(false);
                }}
                className={`bg-primary w-full px-3 py-2 border rounded
                  ${
                    usernameError
                      ? "border-red-500 placeholder-red-500"
                      : "border-sidebar-border"
                  }`}
              />
            )}

            <input
              tabIndex={0}
              type="password"
              placeholder={t("auth.placeholderPassword")}
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                if (passwordError) setPasswordError(false);
              }}
              className={`bg-primary w-full px-3 py-2 border rounded
                ${
                  passwordError
                    ? "border-red-500 placeholder-red-500"
                    : "border-sidebar-border"
                }`}
            />

            {mode === "register" && password && (
              <ul
                className="text-xs space-y-1 mt-2"
                role="status"
                aria-live="polite"
              >
                <PasswordRuleItem
                  valid={passwordValidation.length}
                  text={t("auth.passwordRules.length")}
                />
                <PasswordRuleItem
                  valid={passwordValidation.upper}
                  text={t("auth.passwordRules.upper")}
                />
                <PasswordRuleItem
                  valid={passwordValidation.lower}
                  text={t("auth.passwordRules.lower")}
                />
                <PasswordRuleItem
                  valid={passwordValidation.number}
                  text={t("auth.passwordRules.number")}
                />
                <PasswordRuleItem
                  valid={passwordValidation.special}
                  text={t("auth.passwordRules.special")}
                />
              </ul>
            )}

            <button
              tabIndex={0}
              type="submit"
              className="w-full bg-primary py-2 rounded hover:bg-accent hover:text-black disabled:opacity-50 focus:bg-accent"
              disabled={loading}
            >
              {loading
                ? t("auth.processing")
                : mode === "login"
                  ? t("auth.login")
                  : t("auth.register")}
            </button>
          </form>
          {/* Server Error */}
          {serverError && (
            <div className="text-red-600 text-sm mt-2 text-center">
              {serverError}
            </div>
          )}

          <div className="mt-4 text-center">
            {mode === "login" ? (
              <span>
                {t("auth.noAccount")}{" "}
                <button
                  tabIndex={0}
                  className="text-blue-600 underline"
                  onClick={() => {
                    setMode("register");
                    setServerError(null);
                    setEmailError(false);
                    setPasswordError(false);
                    setUsernameError(false);
                    // fetchGeneratedUsername();
                  }}
                  type="button"
                >
                  {t("auth.register")}
                </button>
              </span>
            ) : (
              <span>
                {t("auth.hasAccount")}{" "}
                <button
                  tabIndex={0}
                  className="text-blue-600 underline"
                  onClick={() => {
                    setMode("login");
                    setServerError(null);
                    setEmailError(false);
                    setPasswordError(false);
                    setUsernameError(false);
                  }}
                  type="button"
                >
                  {t("auth.login")}
                </button>
              </span>
            )}
          </div>
        </div>
      </FocusScope>
    </div>
  );
}
