"use client";

import type React from "react";
import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { X, Camera, Save, User, Eye, EyeOff } from "lucide-react";
import { useTranslation } from "react-i18next";

const BACKEND_URL = "http://134.60.71.197:8000";

interface ProfileModalProps {
  username: string;
  onClose: () => void;
  onSaveUsername?: (newUsername: string) => void;
  onApiKeyChanged?: () => void;
}

type ToastState = {
  open: boolean;
  type: "success" | "error";
  message: string;
};

export function ProfileModal({
  username,
  onClose,
  onSaveUsername,
  onApiKeyChanged,
}: ProfileModalProps) {
  const [name, setName] = useState<string>(username);
  const [avatar, setAvatar] = useState<string>("");
  const [isSaving, setIsSaving] = useState(false);
  const [toast, setToast] = useState<ToastState>({
    open: false,
    type: "success",
    message: "",
  });
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [apiKey, setApiKey] = useState<string>("");
  const [showApiKey, setShowApiKey] = useState(false);

  const { t } = useTranslation();

  useEffect(() => {
    setName(username);
  }, [username]);

  useEffect(() => {
    const fetchApiKey = async () => {
      const token = localStorage.getItem("token");
      try {
        const res = await fetch(`${BACKEND_URL}/api/user/api-key`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          const data = await res.json();
          setApiKey(data.api_key ?? "");
        }
      } catch (e) {
        console.error("API-Key konnte nicht geladen werden", e);
      }
    };
    fetchApiKey();
  }, []);

  useEffect(() => {
    if (!toast.open) return;
    const t = setTimeout(() => setToast((p) => ({ ...p, open: false })), 4000);
    return () => clearTimeout(t);
  }, [toast.open]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const token = localStorage.getItem("token");
      const res = await fetch(
        `${BACKEND_URL}/api/user/api-key?api_key=${encodeURIComponent(apiKey.trim())}`,
        {
          method: "POST",
          headers: { Authorization: `Bearer ${token}` },
        },
      );
      if (!res.ok) throw new Error("API-Key konnte nicht gesetzt werden.");
      onApiKeyChanged?.();

      // Username-API-Call nur wenn er sich geändert hat
      if (name.trim() && name.trim() !== username) {
        const token = localStorage.getItem("token");
        const url = new URL(`${BACKEND_URL}/api/user/change-name`);
        url.searchParams.append("new_username", name);

        const res = await fetch(url.toString(), {
          method: "PUT",
          headers: {
            accept: "application/json",
            Authorization: `Bearer ${token}`,
          },
        });

        if (!res.ok) throw new Error("Username konnte nicht geändert werden.");

        const updated = await res.json();
        onSaveUsername?.(updated.username);
      }

      setToast({
        open: true,
        type: "success",
        message: t("profile.successMessage"),
      });
    } catch (e: any) {
      setToast({
        open: true,
        type: "error",
        message: t("profile.errorMessage", {
          error: e?.message || t("profile.unknownError"),
        }),
      });
    } finally {
      setIsSaving(false);
    }
  };

  const handleImageUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (e) => setAvatar(e.target?.result as string);
      reader.readAsDataURL(file);
    }
  };

  return (
    <>
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto bg-sidebar border-sidebar-border">
          <CardHeader className="flex flex-row items-center justify-between">
            <CardTitle className="flex items-center space-x-2">
              <User className="w-5 h-5" />
              <span>{t("profile.title")}</span>
            </CardTitle>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClose}
              className="hover:text-black"
            >
              <X className="w-4 h-4" />
            </Button>
          </CardHeader>

          <CardContent className="space-y-6">
            {/* Avatar Section */}
            <div className="flex flex-col items-center space-y-4">
              <div className="relative">
                <Avatar className="w-24 h-24">
                  <AvatarImage
                    src={avatar || "/Portrait_Placeholder.png"}
                    alt={name}
                  />
                  <AvatarFallback>
                    {(name || "U").slice(0, 2).toUpperCase()}
                  </AvatarFallback>
                </Avatar>

                <Button
                  size="sm"
                  className="absolute -bottom-2 -right-2 rounded-full w-8 h-8 p-0 bg-secondary text-secondary-foreground  hover:text-black hover:bg-accent "
                  onClick={() => fileInputRef.current?.click()}
                >
                  <Camera className="w-4 h-4 transition-colors group-hover:text-black" />
                </Button>
              </div>
              <input
                ref={fileInputRef}
                type="file"
                accept="image/*"
                className="hidden"
                onChange={handleImageUpload}
              />
            </div>

            {/* Profile Form: Only Name */}
            <div className="space-y-2">
              <Label htmlFor="name">{t("profile.username")}</Label>
              <Input
                id="name"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="bg-primary border-sidebar-border"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="apiKey">{t("profile.apiKey")}</Label>
              <div className="relative">
                <Input
                  id="apiKey"
                  type={showApiKey ? "text" : "password"}
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  placeholder="sk-..."
                  className="bg-primary border-sidebar-border pr-10"
                />
                <button
                  type="button"
                  className="absolute right-2 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-700"
                  onClick={() => setShowApiKey((v) => !v)}
                >
                  {showApiKey ? (
                    <EyeOff className="w-4 h-4" />
                  ) : (
                    <Eye className="w-4 h-4" />
                  )}
                </button>
              </div>
              <p className="text-xs text-gray-500">{t("profile.apiKeyHint")}</p>
            </div>

            {/* Action Buttons */}
            <div className="flex justify-end space-x-2 pt-4 border-t border-sidebar-border">
              <>
                <Button
                  variant="outline"
                  onClick={onClose}
                  disabled={isSaving}
                  className="hover:text-black border-sidebar-border bg-primary"
                >
                  {t("profile.cancel")}
                </Button>
                <Button
                  variant="outline"
                  onClick={handleSave}
                  disabled={isSaving}
                  className="hover:text-black border-sidebar-border bg-primary"
                >
                  {isSaving ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                      {t("profile.saving")}
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4 mr-2" />
                      {t("profile.save")}
                    </>
                  )}
                </Button>
              </>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Bottom toast */}
      <div
        aria-live="polite"
        className="pointer-events-none fixed inset-x-0 bottom-6 z-[60] flex justify-center px-4"
      >
        {toast.open && (
          <div
            role="status"
            className={[
              "pointer-events-auto max-w-xl w-full sm:w-auto rounded-xl shadow-lg border text-white",
              "flex items-start gap-3 px-4 py-3",
              toast.type === "success"
                ? "bg-green-600 border-green-700"
                : "bg-red-600 border-red-700",
            ].join(" ")}
            onClick={() => setToast((p) => ({ ...p, open: false }))}
          >
            <div className="sr-only">
              {toast.type === "success"
                ? t("profile.success")
                : t("profile.error")}
            </div>
            <div className="flex-1 text-sm">{toast.message}</div>
            <button
              type="button"
              className="opacity-90 hover:opacity-100 transition"
              aria-label="Dismiss notification"
              onClick={(e) => {
                e.stopPropagation();
                setToast((p) => ({ ...p, open: false }));
              }}
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        )}
      </div>
    </>
  );
}
