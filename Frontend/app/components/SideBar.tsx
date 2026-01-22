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
}

interface UISession {
  id: string;
  title: string;
  folderId: string | null;
  createdAt: Date;
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
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false);

  const topLevelFolders = folders.filter((f) => f.parentId === null);
  const topLevelSessions = sessions.filter((s) => s.folderId === null);

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
          <Button className="w-full bg-primary hover:bg-accent border border-secondary text-black dark:text-white dark:hover:text-black ">
            <MessageSquare className="w-4 h-4 mr-2" />
            New Chat
          </Button>
        </div>
      )}

      {/* Chat Sessions */}
      <ScrollArea className="flex-1 px-2">
        {/* Top-Level Sessions */}
        {topLevelSessions.map((session) => (
          <div
            key={session.id}
            onClick={() => {
              setActiveSessionId(session.id);
              setActiveFolderId(null);
              console.log(session.id);
            }}
            className={`p-3 mb-1 rounded cursor-pointer flex items-center
              ${
                activeSessionId === session.id
                  ? "bg-accent dark:text-black"
                  : "hover:bg-primary"
              }
            `}
          >
            <MessageSquare className="w-4 h-4 mr-2 shrink-0" />
            <span className="truncate">{session.title}</span>
          </div>
        ))}

        {/* Folders */}
        {topLevelFolders.map((folder) => (
          <div key={folder.id} className="mt-2">
            {/* Folder Header */}
            <div
              onClick={() => {
                setActiveFolderId(folder.id);
                setActiveSessionId(null);
                console.log(folder.id);
              }}
              className={`p-3 font-semibold cursor-pointer rounded flex items-center
                ${
                  activeFolderId === folder.id
                    ? "bg-accent dark:text-black"
                    : "hover:bg-primary"
                }
              `}
            >
              <Folder className="w-4 h-4 mr-2 shrink-0" />
              <span>{folder.name}</span>
            </div>

            {/* Sessions in Folder */}
            {sessionsByFolder(folder.id).map((session) => (
              <div
                key={session.id}
                onClick={() => setActiveSessionId(session.id)}
                className={`ml-4 p-2 rounded cursor-pointer
                  ${
                    activeSessionId === session.id
                      ? "bg-accent dark:text-black"
                      : "hover:bg-primary"
                  }
                `}
              >
                💬 {session.title}
              </div>
            ))}
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
