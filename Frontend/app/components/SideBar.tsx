"use client";

import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import {
  MessageSquare,
  Shield,
  X,
  PanelLeftOpen,
  PanelLeftClose,
  Folder,
} from "lucide-react";
import { useState } from "react";
import Image from "next/image";

interface UIFolder {
  id: string;
  name: string;
  parentId: string | null;
  depth: number;
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
  onConfirmCreateFolder: (
    tempId: string,
    name: string,
    parentId: string | null,
  ) => void;
  editingFolderId: string | null;
  setEditingFolderId: (id: string | null) => void;
  onUpdateDraftFolderName: (id: string, name: string) => void;
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
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);

  const topLevelFolders = folders
    .filter((f) => f.parentId === null)
    .sort((a, b) => {
      if (a.isDraft && !b.isDraft) return -1; // Draft nach unten
      if (!a.isDraft && b.isDraft) return 1; // Normale nach oben
      return 0;
    });
  const topLevelSessions = sessions
    .filter((s) => s.folderId === null)
    .sort((a, b) => {
      if (a.isDraft && !b.isDraft) return -1; // Draft nach unten
      if (!a.isDraft && b.isDraft) return 1; // Normale nach oben
      return 0;
    });

  const sessionsByFolder = (folderId: string) =>
    sessions.filter((s) => s.folderId === folderId);

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
            className="rounded h-8 w-auto object-contain ml-1 mt-1 dark:invert ease-in-out"
          />
        )}

        {/* Spacer */}
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
            className="w-full bg-primary hover:bg-accent border border-secondary text-black dark:text-white dark:hover:text-black "
          >
            <MessageSquare className="w-4 h-4 mr-2" />
            New Chat
          </Button>
        </div>
      )}

      {!collapsed && (
        <div className="px-4 pb-2">
          <Button
            onClick={() => {
              onNewFolder();
            }}
            className="w-full bg-primary hover:bg-accent border border-secondary text-black dark:text-white dark:hover:text-black"
          >
            <Folder className="w-4 h-4 mr-2" />
            New Folder
          </Button>
        </div>
      )}

      {/* Chat Sessions */}
      <ScrollArea className="flex-1 px-2">
        {!collapsed && (
          <div className="mb-2 mt-4 text-gray-500 dark:text-gray-400">
            <span>Folders</span>
          </div>
        )}

        {/* Folders */}
        {topLevelFolders.map((folder) => (
          <div key={folder.id} className="mt-2">
            {/* Folder Header */}
            <div
              onClick={() => {
                if (folder.isDraft) return;
                setActiveFolderId(folder.id);
                setActiveSessionId(null);
                console.log(folder.id);
              }}
              className={`p-3 font-semibold cursor-pointer rounded flex items-center
                ${collapsed ? " hidden" : "p-3"}
                ${
                  activeFolderId === folder.id || editingFolderId === folder.id
                    ? "bg-accent dark:text-black"
                    : "hover:bg-primary"
                }
              `}
            >
              <Folder className="w-4 h-4 mr-2 shrink-0" />
              {folder.isDraft && editingFolderId === folder.id ? (
                <input
                  autoFocus
                  value={folder.name}
                  onChange={(e) => {
                    const value = e.target.value;
                    onUpdateDraftFolderName(folder.id, value);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && folder.name.trim()) {
                      onConfirmCreateFolder(
                        folder.id,
                        folder.name,
                        folder.parentId,
                      );
                    }

                    if (e.key === "Escape") {
                      onCancelDraftFolder(folder.id);
                      setEditingFolderId(null);
                      setActiveFolderId(null);
                      onUpdateDraftFolderName(folder.id, "");
                    }
                  }}
                  onBlur={() => {
                    if (folder.name.trim()) {
                      onConfirmCreateFolder(
                        folder.id,
                        folder.name,
                        folder.parentId,
                      );
                    } else {
                      onCancelDraftFolder(folder.id);
                      setEditingFolderId(null);
                    }
                  }}
                  className="w-full bg-transparent border-b border-accent outline-none px-1"
                  placeholder="Folder name"
                />
              ) : (
                <span>{folder.name}</span>
              )}
              {activeFolderId === folder.id && !folder.isDraft && (
                <X
                  className="w-5 h-5 hover:text-red-500 hover:text-red-700 cursor-pointer ml-2"
                  onClick={(e) => {
                    e.stopPropagation(); // verhindert, dass der Folder selektiert wird
                    onDeleteFolder(folder.id);
                  }}
                />
              )}
            </div>

            {/* Sessions in Folder */}
            {sessionsByFolder(folder.id).map((session) => (
              <div
                key={session.id}
                onClick={() => setActiveSessionId(session.id)}
                className={`ml-4 p-2 rounded cursor-pointer
                  ${
                    activeSessionId === session.id ||
                    editingSessionId === session.id
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
                        onConfirmCreateSession(
                          session.id,
                          editedTitle,
                          session.folderId,
                        );
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
                        onConfirmCreateSession(
                          session.id,
                          editedTitle,
                          session.folderId,
                        );
                      } else {
                        onCancelDraftSession(session.id);
                        setActiveSessionId(null);
                      }
                      setEditingSessionId(null);
                      setEditedTitle("");
                    }}
                    className="w-full bg-transparent border-b border-accent outline-none px-1"
                    placeholder="Chat name"
                  />
                ) : (
                  <span>{session.title}</span>
                )}
                {activeSessionId === session.id && !session.isDraft && (
                  <X
                    className="w-5 h-5 hover:text-red-500 hover:text-red-700 cursor-pointer ml-2"
                    onClick={(e) => {
                      e.stopPropagation(); // verhindert, dass der Folder selektiert wird
                      onDeleteSession(session.id);
                    }}
                  />
                )}
              </div>
            ))}
          </div>
        ))}

        {!collapsed && (
          <div className="mb-2 mt-4 text-gray-500 dark:text-gray-400">
            <span>Chats</span>
          </div>
        )}

        {/* Top-Level Sessions */}
        {topLevelSessions.map((session) => (
          <div
            key={session.id}
            onClick={() => {
              if (session.isDraft) return;
              setActiveSessionId(session.id);
              setActiveFolderId(null);
            }}
            className={`
              mb-1 rounded cursor-pointer flex items-center
              ${collapsed ? " hidden" : "p-3"}
              ${
                activeSessionId === session.id ||
                editingSessionId === session.id
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
                    onConfirmCreateSession(
                      session.id,
                      editedTitle,
                      session.folderId,
                    );
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
                    onConfirmCreateSession(
                      session.id,
                      editedTitle,
                      session.folderId,
                    );
                  } else {
                    onCancelDraftSession(session.id);
                    setActiveSessionId(null);
                  }
                  setEditingSessionId(null);
                  setEditedTitle("");
                }}
                className="w-full bg-transparent border-b border-accent outline-none px-1"
                placeholder="Chat name"
              />
            ) : (
              <span>{session.title}</span>
            )}
            {activeSessionId === session.id && !session.isDraft && (
              <X
                className="w-5 h-5 hover:text-red-500 hover:text-red-700 cursor-pointer ml-2"
                onClick={(e) => {
                  e.stopPropagation(); // verhindert, dass der Folder selektiert wird
                  onDeleteSession(session.id);
                }}
              />
            )}
          </div>
        ))}
      </ScrollArea>

      {/* Footer */}
      {/* {!collapsed && (
        <div className="p-4 border-t border-gray-700">
          <div className="flex items-center space-x-2">
            <Shield className="w-5 h-5 text-blue-400" />
            <div>
              <div className="text-sm font-medium">GDPR Assistant</div>
              <div className="text-xs text-gray-400">Privacy Compliance Expert</div>
            </div>
          </div>
        </div>
      )} */}

      <div
        className="bottom-0 left-0 right-0 py-2 px-4 bg-sidebar
             text-sm 
             text-gray-600 dark:text-gray-300 flex justify-between z-50"
      >
        {!collapsed && <span>RAGulate</span>}
        <span>v{process.env.NEXT_PUBLIC_APP_VERSION}</span>
      </div>
    </div>
  );
}
