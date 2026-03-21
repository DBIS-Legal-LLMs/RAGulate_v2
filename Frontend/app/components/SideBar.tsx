"use client";

import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import {
  MessageSquare,
  X,
  PanelLeftOpen,
  PanelLeftClose,
  Folder,
} from "lucide-react";
import { useState } from "react";
import Image from "next/image";
import { useTranslation } from "react-i18next";

interface UIFolder {
  id: string;
  title: string;
  createdAt: Date;
  isDraft?: boolean;
}

interface UISession {
  id: string;
  title: string;
  folderId: string | null;
  createdAt: Date;
  isDraft?: boolean;
}

interface SidebarProps {
  folders: UIFolder[];
  sessions: UISession[];
  activeFolderId: string | null;
  setActiveFolderId: (id: string | null) => void;
  activeSessionId: string | null;
  setActiveSessionId: (id: string | null) => void;
  editingSessionId: string | null;
  setEditingSessionId: (id: string | null) => void;
  editedTitle: string;
  setEditedTitle: (title: string) => void;
  onNewChat: () => void;
  onNewFolder: () => void;
  onConfirmCreateFolder: (tempId: string, title: string) => void;
  editingFolderId: string | null;
  setEditingFolderId: (id: string | null) => void;
  onUpdateDraftFolderName: (id: string, title: string) => void;
  onCancelDraftFolder: (id: string) => void;
  onDeleteFolder: (folderId: string) => void;
  onDeleteSession: (sessionID: string) => void;
  onConfirmCreateSession: (
    tempId: string,
    name: string,
    parentId: string | null,
  ) => void;
  onUpdateDraftSessionName: (id: string, name: string) => void;
  onCancelDraftSession: (id: string) => void;
  onMoveSession: (sessionId: string, newFolderId: string | null) => void;
  draggingSessionId: string | null;
  setDraggingSessionId: (id: string | null) => void;
}

export default function Sidebar({
  folders,
  sessions,
  activeFolderId,
  setActiveFolderId,
  activeSessionId,
  setActiveSessionId,
  editingSessionId,
  setEditingSessionId,
  editedTitle,
  setEditedTitle,
  onNewChat,
  onNewFolder,
  editingFolderId,
  setEditingFolderId,
  onConfirmCreateFolder,
  onUpdateDraftFolderName,
  onCancelDraftFolder,
  onDeleteFolder,
  onDeleteSession,
  onConfirmCreateSession,
  onUpdateDraftSessionName,
  onCancelDraftSession,
  onMoveSession,
  draggingSessionId,
  setDraggingSessionId
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [dragOverFolderId, setDragOverFolderId] = useState<string | null>(null);
  const { t } = useTranslation();

  const topLevelSessions = sessions
    .filter((s) => s.folderId === null)
    .sort((a, b) => {
      if (a.isDraft && !b.isDraft) return -1;
      if (!a.isDraft && b.isDraft) return 1;
      return 0;
    });

  const sortedFolders = [...folders].sort((a, b) => {
    if (a.isDraft && !b.isDraft) return -1;
    if (!a.isDraft && b.isDraft) return 1;
    return b.createdAt.getTime() - a.createdAt.getTime();
  });

  const renderSession = (session: UISession) => (
    <div
      key={session.id}
      draggable={!session.isDraft}
      onDragStart={(e) => {
        setDraggingSessionId(session.id);
        e.dataTransfer.effectAllowed = "move";
      }}
      onDragEnd={() => {
        setDraggingSessionId(null);
        setDragOverFolderId(null);
      }}
      onClick={() => {
        if (session.isDraft) return;
        setActiveSessionId(session.id);
        setActiveFolderId(null);
      }}
      className={`
        mb-1 rounded cursor-pointer flex items-center justify-between
        ${collapsed ? "hidden" : "p-3"}
        ${
          activeSessionId === session.id || editingSessionId === session.id
            ? "bg-accent dark:text-black"
            : "hover:bg-primary"
        }
      `}
    >
      <MessageSquare className="w-4 h-4 mr-2 shrink-0" />
      {session.isDraft && editingSessionId === session.id ? (
        <input
          autoFocus
          value={editedTitle}
          onChange={(e) => setEditedTitle(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && editedTitle.trim()) {
              onConfirmCreateSession(session.id, editedTitle, session.folderId);
              setEditedTitle("");
            }
            if (e.key === "Escape") {
              onCancelDraftSession(session.id);
              setEditingSessionId(null);
              setActiveSessionId(null);
              setEditedTitle("");
            }
          }}
          onBlur={() => {
            if (editedTitle.trim()) {
              onConfirmCreateSession(session.id, editedTitle, session.folderId);
            } else {
              onCancelDraftSession(session.id);
              setActiveSessionId(null);
            }
            setEditingSessionId(null);
            setEditedTitle("");
          }}
          className="w-full bg-transparent border-b border-accent outline-none px-1"
          placeholder={t("sidebar.placeholderChat")}
        />
      ) : (
        <span className="flex-1 truncate">{session.title}</span>
      )}
      {activeSessionId === session.id && !session.isDraft && (
        <X
          className="w-5 h-5 hover:text-red-500 hover:text-red-700 cursor-pointer ml-auto shrink-0"
          onClick={(e) => {
            e.stopPropagation();
            onDeleteSession(session.id);
          }}
        />
      )}
    </div>
  );

  return (
    <div
      className={`bg-sidebar flex flex-col transition-all duration-300 
        ${collapsed ? "w-16" : "w-64"}`}
    >
      {/* Collapse / Expand Button */}
      <div className="p-2 flex justify-end">
        {!collapsed && (
          <Image
            src="logo_light.png"
            alt="Logo"
            width={32}
            height={32}
            className="rounded h-8 w-auto object-contain ml-1 mt-1 dark:invert ease-in-out cursor-pointer"
            onClick={() => {
              setActiveFolderId(null);
              setActiveSessionId(null);
            }}
          />
        )}
        <div className="flex-1" />
        <Button
          size="icon"
          variant="ghost"
          className="hover:bg-accent mr-1 dark:hover:text-black"
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? (
            <PanelLeftOpen className="!w-6 !h-6" />
          ) : (
            <PanelLeftClose className="!w-6 !h-6" />
          )}
        </Button>
      </div>

      {/* New Chat */}
      {!collapsed && (
        <div className="p-4">
          <Button
            onClick={() => {
              setActiveSessionId(null);
              onNewChat();
            }}
            className="w-full bg-primary hover:bg-accent border border-secondary text-black dark:text-white dark:hover:text-black"
          >
            <MessageSquare className="w-4 h-4 mr-2" />
            {t("sidebar.newChat")}
          </Button>
        </div>
      )}

      {!collapsed && (
        <div className="px-4 pb-2">
          <Button
            onClick={onNewFolder}
            className="w-full bg-primary hover:bg-accent border border-secondary text-black dark:text-white dark:hover:text-black"
          >
            <Folder className="w-4 h-4 mr-2" />
            {t("sidebar.newFolder")}
          </Button>
        </div>
      )}

      <ScrollArea className="flex-1 px-2">
        {/* Folders */}
        {!collapsed && (
          <>
            <div className="mb-2 mt-4 text-gray-500 dark:text-gray-400">
              <span>{t("sidebar.folders")}</span>
            </div>

            {sortedFolders.map((folder) => (
              <div
                key={folder.id}
                onDragOver={(e) => {
                  e.preventDefault();
                  setDragOverFolderId(folder.id);
                  e.dataTransfer.dropEffect = "move";
                }}
                onDragLeave={() => setDragOverFolderId(null)}
                onDrop={(e) => {
                  e.preventDefault();
                  if (draggingSessionId) {
                    onMoveSession(draggingSessionId, folder.id);
                  }
                  setDraggingSessionId(null);
                  setDragOverFolderId(null);
                }}
                onClick={() => {
                  setActiveFolderId(folder.id);
                  setActiveSessionId(null);
                }}
                className={`p-3 font-semibold cursor-pointer rounded flex items-center mb-1
                  ${activeFolderId === folder.id ? "bg-accent dark:text-black" : "hover:bg-primary"}
                  ${dragOverFolderId === folder.id ? "ring-2 ring-blue-400 bg-blue-100 dark:bg-blue-900" : ""}
                `}
              >
                <Folder className="w-4 h-4 mr-2 shrink-0" />
                {folder.isDraft && editingFolderId === folder.id ? (
                  <input
                    autoFocus
                    value={folder.title}
                    onChange={(e) =>
                      onUpdateDraftFolderName(folder.id, e.target.value)
                    }
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && folder.title.trim()) {
                        onConfirmCreateFolder(folder.id, folder.title);
                      }
                      if (e.key === "Escape") {
                        onCancelDraftFolder(folder.id);
                        setEditingFolderId(null);
                        setActiveFolderId(null);
                      }
                    }}
                    onBlur={() => {
                      if (folder.title.trim()) {
                        onConfirmCreateFolder(folder.id, folder.title.trim());
                      } else {
                        onCancelDraftFolder(folder.id);
                        setActiveFolderId(null);
                      }
                      setEditingFolderId(null);
                    }}
                    className="w-full bg-transparent border-b border-accent outline-none px-1"
                    placeholder={t("sidebar.placeholderFolder")}
                  />
                ) : (
                  <span className="flex-1">{folder.title}</span>
                )}
                {activeFolderId === folder.id && !folder.isDraft && (
                  <X
                    className="w-5 h-5 hover:text-red-500 cursor-pointer ml-2"
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteFolder(folder.id);
                    }}
                  />
                )}
              </div>
            ))}
          </>
        )}

        {/* Top-level sessions (no folder) */}
        {!collapsed && (
          <>
            <div
              className="mb-2 mt-4 text-gray-500 dark:text-gray-400"
              onDragOver={(e) => {
                e.preventDefault();
                setDragOverFolderId("root");
              }}
              onDragLeave={() => setDragOverFolderId(null)}
              onDrop={(e) => {
                e.preventDefault();
                if (draggingSessionId) onMoveSession(draggingSessionId, null);
                setDraggingSessionId(null);
                setDragOverFolderId(null);
              }}
            >
              <span>{t("sidebar.chats")}</span>
            </div>
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragOverFolderId("root");
              }}
              onDragLeave={() => setDragOverFolderId(null)}
              onDrop={(e) => {
                e.preventDefault();
                if (draggingSessionId) onMoveSession(draggingSessionId, null);
                setDraggingSessionId(null);
                setDragOverFolderId(null);
              }}
              className={`rounded transition-colors ${dragOverFolderId === "root" ? "ring-2 ring-dashed ring-blue-400" : ""}`}
            >
              {topLevelSessions.map(renderSession)}
            </div>
          </>
        )}
      </ScrollArea>

      <div className="bottom-0 left-0 right-0 py-2 px-4 bg-sidebar text-sm text-gray-600 dark:text-gray-300 flex justify-between z-50">
        {!collapsed && <span>RAGulate</span>}
        <span>v{process.env.NEXT_PUBLIC_APP_VERSION}</span>
      </div>
    </div>
  );
}