// components/FolderDocumentsPanel.tsx
"use client";
import { useState, useRef, useEffect } from "react";
import { FileText, Upload, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";

const BACKEND_URL = "http://134.60.71.197:8000";

interface UploadedFile {
  id: string;
  name: string;
  size: string;
  status: "indexing" | "done" | "error";
}

interface Props {
  folderId: string;
}

export function FolderDocumentsPanel({ folderId }: Props) {
  const { t } = useTranslation();
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const load = async () => {
      // const token = localStorage.getItem("token");
      // const res = await fetch(`${BACKEND_URL}/api/folders/${folderId}/documents`, {
      //   headers: { Authorization: `Bearer ${token}` },
      // });
      // const data = await res.json();
      // setFiles(data.map((f: any) => ({
      //   id: f.id,
      //   name: f.name,
      //   size: formatSize(f.size_bytes),
      //   status: f.status,
      // })));
      setFiles([]);
    };
    load();
  }, [folderId]);

  const formatSize = (bytes: number) => {
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const uploadFile = async (file: File) => {
    setUploading(true);
    setProgress(0);

    const interval = setInterval(() => {
      setProgress((p) => (p >= 90 ? p : p + Math.random() * 15));
    }, 150);

    try {
      // const token = localStorage.getItem("token");
      // const formData = new FormData();
      // formData.append("file", file);
      // formData.append("folder_id", folderId);
      // const res = await fetch(`${BACKEND_URL}/api/documents/upload`, {
      //   method: "POST",
      //   headers: { Authorization: `Bearer ${token}` },
      //   body: formData,
      // });
      // const data = await res.json();

      await new Promise((r) => setTimeout(r, 1500)); // Dummy
      clearInterval(interval);
      setProgress(100);

      const newFile: UploadedFile = {
        id: Date.now().toString(), // echte ID: data.id
        name: file.name,
        size: formatSize(file.size),
        status: "indexing",
      };
      setFiles((prev) => [newFile, ...prev]);

      // Dummy: Status nach 2.5s auf "done" setzen
      // Ersetzen durch Polling: GET /api/documents/{id}/status
      setTimeout(() => {
        setFiles((prev) =>
          prev.map((f) => (f.id === newFile.id ? { ...f, status: "done" } : f)),
        );
      }, 2500);
    } catch (err) {
      console.error("Upload failed:", err);
    } finally {
      setUploading(false);
      setProgress(0);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) uploadFile(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) uploadFile(file);
  };

  const deleteFile = async (id: string) => {
    // const token = localStorage.getItem("token");
    // await fetch(`${BACKEND_URL}/api/documents/${id}`, {
    //   method: "DELETE",
    //   headers: { Authorization: `Bearer ${token}` },
    // });
    setFiles((prev) => prev.filter((f) => f.id !== id));
  };

  return (
    <div className="max-w-2xl mx-auto w-full mt-6">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <FileText className="w-4 h-4 text-gray-500" />
          <h3 className="text-sm font-medium">{t("documents.title")}</h3>
          {files.length > 0 && (
            <span className="text-xs bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-200 px-2 py-0.5 rounded-full">
              {files.length}
            </span>
          )}
        </div>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.docx,.txt,.md"
          className="hidden"
          onChange={handleFileChange}
        />
        <button
          onClick={() => inputRef.current?.click()}
          disabled={uploading}
          className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-md border border-sidebar-border hover:bg-accent hover:text-black transition disabled:opacity-50 bg-chat/60"
        >
          <Upload className="w-3.5 h-3.5" />
          {t("documents.uploadButton")}
        </button>
      </div>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        className={`rounded-xl border transition-colors bg-chat/60 ${
          dragOver ? "border-accent bg-accent/10" : "border-sidebar-border"
        }`}
      >
        {uploading && (
          <div className="px-4 pt-3 pb-1 space-y-1">
            <div className="h-1 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-green-500 rounded-full transition-all duration-300"
                style={{ width: `${Math.min(progress, 100)}%` }}
              />
            </div>
            <p className="text-xs text-gray-600">{t("documents.uploading")}</p>
          </div>
        )}

        {files.length === 0 && !uploading && (
          <div
            className="flex flex-col items-center justify-center py-10 gap-2 cursor-pointer"
            onClick={() => inputRef.current?.click()}
          >
            <Upload className="w-6 h-6 text-gray-600" />
            <p className="text-sm text-gray-800 dark:text-gray-600">
              {t("documents.dropZone")}
            </p>
            <p className="text-xs text-gray-600">
              {t("documents.acceptedFormats")}
            </p>
          </div>
        )}

        {files.length > 0 && (
          <div className="divide-y divide-sidebar-border">
            {files.map((file) => (
              <div
                key={file.id}
                className="group flex items-center gap-3 px-4 py-3 hover:bg-accent/5 transition"
              >
                <FileText className="w-4 h-4 text-gray-600 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium truncate">{file.name}</p>
                  <p className="text-xs text-gray-600">{file.size}</p>
                </div>
                <div className="flex items-center gap-1.5 text-xs shrink-0">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      file.status === "done"
                        ? "bg-green-500"
                        : file.status === "error"
                          ? "bg-red-600"
                          : "bg-amber-600 animate-pulse"
                    }`}
                  />
                  <span className="text-gray-600 hidden sm:inline">
                    {file.status === "done"
                      ? t("documents.statusDone")
                      : file.status === "error"
                        ? t("documents.statusError")
                        : t("documents.statusIndexing")}
                  </span>
                </div>
                <button
                  onClick={() => deleteFile(file.id)}
                  className="opacity-0 group-hover:opacity-100 transition-opacity text-gray-600 hover:text-red-500 shrink-0"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}

            {!uploading && (
              <div
                className="flex items-center gap-2 px-4 py-3 cursor-pointer hover:bg-accent/5 text-gray-600 hover:text-gray-600 transition"
                onClick={() => inputRef.current?.click()}
              >
                <Upload className="w-4 h-4" />
                <span className="text-xs">{t("documents.uploadMore")}</span>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
