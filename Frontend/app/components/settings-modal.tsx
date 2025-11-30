"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { X, Settings } from "lucide-react";

const API_BACKEND =
  process.env.NEXT_PUBLIC_API_BACKEND || "http://134.60.71.197:8000";

const QUERY_MODES = ["local", "global", "hybrid", "naive", "mix"] as const;
type QueryMode = (typeof QUERY_MODES)[number];

interface SettingsModalProps {
  onClose: () => void;
  username: string;
}

interface AppSettings {
  chatHistory: boolean;
  language: "en" | "es" | "fr" | "de";
  timeout: number;
  customPrompt: string;
  queryMode: QueryMode;
  responseType: string;
  llmProvider: string;
}

type ToastState = {
  open: boolean;
  type: "success" | "error";
  message: string;
};

export function SettingsModal({ onClose, username }: SettingsModalProps) {
  const placeholder: AppSettings = {
    chatHistory: false,
    language: "en",
    timeout: 180,
    customPrompt: "",
    queryMode: "naive",
    responseType: "Multiple Paragraphs",
    llmProvider: "hf",
  };

  const [settings, setSettings] = useState<AppSettings>(() => {
    const saved = localStorage.getItem("appSettings");
    return saved ? { ...placeholder, ...JSON.parse(saved) } : placeholder;
  });
  const [isSaving, setIsSaving] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [toast, setToast] = useState<ToastState>({
    open: false,
    type: "success",
    message: "",
  });

  useEffect(() => {
    if (!toast.open) return;
    const t = setTimeout(
      () => setToast((prev) => ({ ...prev, open: false })),
      4000
    );
    return () => clearTimeout(t);
  }, [toast.open]);

  useEffect(() => {
    let ignore = false;

    async function load() {
      setIsLoading(true);
      setLoadError(null);
      try {
        const res = await fetch(
          `${API_BACKEND}/getOptions?username=${encodeURIComponent(username)}`,
          { method: "GET" }
        );
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        const merged: AppSettings = {
          chatHistory:
            typeof data.chatHistory === "boolean"
              ? data.chatHistory
              : placeholder.chatHistory,
          language: (["en", "es", "fr", "de"] as const).includes(data.language)
            ? data.language
            : placeholder.language,
          timeout:
            typeof data.timeout === "number" && Number.isFinite(data.timeout)
              ? data.timeout
              : placeholder.timeout,
          customPrompt:
            typeof data.customPrompt === "string"
              ? data.customPrompt
              : placeholder.customPrompt,
          queryMode: (QUERY_MODES as readonly string[]).includes(data.queryMode)
            ? (data.queryMode as QueryMode)
            : placeholder.queryMode,
          responseType:
            typeof data.responseType === "string"
              ? data.responseType
              : placeholder.responseType,
          llmProvider:
            typeof data.llmProvider === "string"
              ? data.llmProvider
              : placeholder.llmProvider,
        };

        if (!ignore) {
          setSettings(merged);
          localStorage.setItem("appSettings", JSON.stringify(merged));
        }
      } catch (e: any) {
        if (!ignore) setLoadError(e?.message || "Failed to load options.");
      } finally {
        if (!ignore) setIsLoading(false);
      }
    }

    load();
    return () => {
      ignore = true;
    };
  }, [username]);

  const handleSave = async () => {
    setIsSaving(true);
    try {
      const res = await fetch(`${API_BACKEND}/setOptions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, options: settings }),
      });
      if (!res.ok) {
        const text = await res.text().catch(() => "");
        throw new Error(text || `HTTP ${res.status}`);
      }

      localStorage.setItem("appSettings", JSON.stringify(settings));
      setToast({
        open: true,
        type: "success",
        message: "Settings saved successfully.",
      });
    } catch (e: any) {
      setToast({
        open: true,
        type: "error",
        message: `Failed to save settings: ${e?.message || "Unknown error"}`,
      });
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <>
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <Card className="w-full max-w-2xl max-h-[90vh] overflow-y-auto bg-sidebar border-sidebar-border scrollbar-thin">
          <CardHeader className="flex flex-row items-center justify-between sticky top-0 bg-sidebar border-b border-sidebar-border mb-4">
            <CardTitle className="flex items-center space-x-2">
              <Settings className="w-5 h-5" />
              <span>Settings</span>
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

          <CardContent className="space-y-8">
            {isLoading && (
              <div className="text-sm text-muted-foreground">
                Loading options from server…
              </div>
            )}
            {loadError && (
              <div className="text-sm text-red-600">
                Couldn’t load from backend: {loadError}. Using placeholder
                settings.
              </div>
            )}

            {/* Chat History */}
            <div className="space-y-3">
              <h3 className="text-lg font-semibold">Chat History</h3>
              <div className="flex items-center justify-between">
                <Label htmlFor="chat-history">
                  Use chat history for answers (may be slower)
                </Label>
                <Switch
                  id="chat-history"
                  checked={settings.chatHistory}
                  onCheckedChange={(checked) =>
                    setSettings((prev) => ({ ...prev, chatHistory: checked }))
                  }
                  className="
                    data-[state=checked]:bg-accent
                    data-[state=unchecked]:bg-secondary
                  "
                />
              </div>
            </div>

            <Separator className="bg-sidebar-border" />

            {/* Language */}
            <div className="space-y-3">
              <h3 className="text-lg font-semibold">Language</h3>
              <div className="space-y-2">
                <Label htmlFor="language">Interface Language</Label>
                <Select
                  value={settings.language}
                  onValueChange={(value) =>
                    setSettings((prev) => ({
                      ...prev,
                      language: value as AppSettings["language"],
                    }))
                  }
                >
                  <SelectTrigger
                    id="language"
                    className="bg-primary border-sidebar-border"
                  >
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-primary border-sidebar-border">
                    <SelectItem
                      value="en"
                      className="data-[highlighted]:text-black"
                    >
                      English
                    </SelectItem>
                    <SelectItem
                      value="es"
                      className="data-[highlighted]:text-black"
                    >
                      Español
                    </SelectItem>
                    <SelectItem
                      value="fr"
                      className="data-[highlighted]:text-black"
                    >
                      Français
                    </SelectItem>
                    <SelectItem
                      value="de"
                      className="data-[highlighted]:text-black"
                    >
                      Deutsch
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <Separator className="bg-sidebar-border" />

            {/* Query Mode */}
            <div className="space-y-3">
              <h3 className="text-lg font-semibold">Query Mode</h3>
              <div className="space-y-2">
                <Label htmlFor="query-mode">How retrieval should behave</Label>
                <Select
                  value={settings.queryMode}
                  onValueChange={(value) =>
                    setSettings((prev) => ({
                      ...prev,
                      queryMode: value as QueryMode,
                    }))
                  }
                >
                  <SelectTrigger
                    id="query-mode"
                    className="bg-primary border-sidebar-border"
                  >
                    <SelectValue placeholder="Choose mode" />
                  </SelectTrigger>
                  <SelectContent className="bg-primary border-sidebar-border">
                    <SelectItem
                      value="local"
                      className="data-[highlighted]:text-black"
                    >
                      local: Focuses on context-dependent information.
                    </SelectItem>
                    <SelectItem
                      value="global"
                      className="data-[highlighted]:text-black"
                    >
                      global: Utilizes global knowledge.
                    </SelectItem>
                    <SelectItem
                      value="hybrid"
                      className="data-[highlighted]:text-black"
                    >
                      hybrid: Combines local and global retrieval.
                    </SelectItem>
                    <SelectItem
                      value="naive"
                      className="data-[highlighted]:text-black"
                    >
                      naive: Basic search without advanced techniques.
                    </SelectItem>
                    <SelectItem
                      value="mix"
                      className="data-[highlighted]:text-black"
                    >
                      mix: KG + vector retrieval integration.
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <Separator className="bg-sidebar-border" />

            {/* Timeout */}
            <div className="space-y-3">
              <h3 className="text-lg font-semibold">Request Timeout</h3>
              <div className="space-y-2">
                <Label htmlFor="timeout">Timeout (seconds)</Label>
                <Input
                  id="timeout"
                  className="bg-primary border-sidebar-border"
                  type="number"
                  min={5}
                  max={300}
                  value={settings.timeout}
                  onChange={(e) =>
                    setSettings((prev) => ({
                      ...prev,
                      timeout:
                        Number.parseInt(e.target.value || "0", 10) || 180,
                    }))
                  }
                />
              </div>
            </div>

            <Separator className="bg-sidebar-border" />

            {/* Response Type */}
            <div className="space-y-3">
              <h3 className="text-lg font-semibold">Response Type</h3>
              <div className="space-y-2">
                <Label>Defines the response format</Label>
                <Select
                  value={settings.responseType}
                  onValueChange={(value) =>
                    setSettings((prev) => ({
                      ...prev,
                      responseType: value as string,
                    }))
                  }
                >
                  <SelectTrigger
                    id="responseType"
                    className="bg-primary border-sidebar-border"
                  >
                    <SelectValue placeholder="Choose mode" />
                  </SelectTrigger>
                  <SelectContent className="bg-primary border-sidebar-border">
                    <SelectItem
                      value="Multiple Paragraphs"
                      className="data-[highlighted]:text-black"
                    >
                      Multiple Paragraphs
                    </SelectItem>
                    <SelectItem
                      value="Sinlge Paragraph"
                      className="data-[highlighted]:text-black"
                    >
                      Single Paragraph
                    </SelectItem>
                    <SelectItem
                      value="Bullet Points"
                      className="data-[highlighted]:text-black"
                    >
                      Bullet Points
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Custom Prompt */}
            <div className="space-y-3">
              <h3 className="text-lg font-semibold">Custom Prompt</h3>
              <div className="space-y-2">
                <Label htmlFor="custom-prompt">
                  Default Prompt for Backend
                </Label>
                <textarea
                  id="custom-prompt"
                  className="w-full min-h-[120px] rounded-md border border-sidebar-border border-input bg-primary p-2 text-sm ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
                  placeholder="e.g., 'Answer concisely and cite GDPR articles when relevant.'"
                  value={settings.customPrompt}
                  onChange={(e) =>
                    setSettings((prev) => ({
                      ...prev,
                      customPrompt: e.target.value,
                    }))
                  }
                />
              </div>
            </div>

            {/* LLM Provider */}
            <div className="space-y-3">
              <h3 className="text-lg font-semibold">LLM Provider</h3>
              <div className="space-y-2">
                <Label htmlFor="llm-provider">
                  Default LLM Provider (local by default)
                </Label>
                <Select
                  value={settings.llmProvider}
                  onValueChange={(value) =>
                    setSettings((prev) => ({
                      ...prev,
                      llmProvider: value as AppSettings["llmProvider"],
                    }))
                  }
                >
                  <SelectTrigger
                    id="llm-provider"
                    className="bg-primary border-sidebar-border"
                  >
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-primary border-sidebar-border">
                    <SelectItem
                      value="hf"
                      className="data-[highlighted]:text-black"
                    >
                      Local (Transformers / HF)
                    </SelectItem>
                    <SelectItem
                      value="openrouter"
                      className="data-[highlighted]:text-black"
                    >
                      OpenRouter · mistral-nemo
                    </SelectItem>
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  Hf uses a local model (slower), Openrouter uses an external
                  API (costs money).
                </p>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex justify-end space-x-2 pt-4 border-t border-sidebar-border">
              <Button
                variant="outline"
                onClick={onClose}
                className="hover:text-black border-sidebar-border bg-primary"
              >
                Cancel
              </Button>
              <Button
                variant="outline"
                onClick={handleSave}
                disabled={isSaving || !username}
                className="border-sidebar-border bg-primary hover:text-black"
              >
                {isSaving ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                    Saving…
                  </>
                ) : (
                  "Save Settings"
                )}
              </Button>
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
            onClick={() => setToast((prev) => ({ ...prev, open: false }))}
          >
            <div className="sr-only">
              {toast.type === "success" ? "Success" : "Error"}
            </div>
            <div className="flex-1 text-sm">{toast.message}</div>
            <button
              type="button"
              className="opacity-90 hover:opacity-100 transition"
              aria-label="Dismiss notification"
              onClick={(e) => {
                e.stopPropagation();
                setToast((prev) => ({ ...prev, open: false }));
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
