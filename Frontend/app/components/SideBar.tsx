"use client"

import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { MessageSquare, Shield, X, PanelLeftOpen, PanelLeftClose } from "lucide-react"
import { useState } from "react"
import Image from "next/image"

interface SidebarProps {
  chatSessions: any[]; // ChatSession[]
  currentSessionId: string | null;
  createNewChat: () => void;
  setCurrentSessionId: (id: string) => void;
  setMessages: (messages: any[]) => void;
  deleteChatSession: (id: string) => void;
  editingSessionId: string | null;
  setEditingSessionId: (id: string | null) => void;
  editedTitle: string;
  setEditedTitle: (title: string) => void;
}

export default function Sidebar({
  chatSessions,
  currentSessionId,
  createNewChat,
  setCurrentSessionId,
  setMessages,
  deleteChatSession,
  editingSessionId,
  setEditingSessionId,
  editedTitle,
  setEditedTitle,
}: SidebarProps) {
  const [collapsed, setCollapsed] = useState(false)

  return (
    <div
      className={`bg-sidebar flex flex-col transition-all duration-300 border-r border-sidebar-border
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
            onClick={createNewChat}
            className="w-full bg-primary hover:bg-accent border border-secondary text-black dark:text-white dark:hover:text-black "
          >
            <MessageSquare className="w-4 h-4 mr-2" />
            New Chat
          </Button>
        </div>
      )}

      {/* Chat Sessions */}
      <ScrollArea className="flex-1 px-2">
        {chatSessions.map((session) => (
          <div
            key={session.id}
            onClick={() => {
              setCurrentSessionId(session.id)
              setMessages(session.messages)
            }}
            className={`group p-3 mb-2 rounded cursor-pointer flex items-center transition-colors 
            ${currentSessionId === session.id ? "bg-accent dark:text-black" : "hover:secondary hover:bg-primary"}
            `}
          >
            {!collapsed ? (
              <div className="flex-1 min-w-0">
                {editingSessionId === session.id ? (
                  <form
                    onSubmit={(e) => {
                      e.preventDefault()
                      setEditingSessionId(null)
                    }}
                  >
                    <input
                      className={`text-sm font-medium rounded px-1 w-ful
                        ${currentSessionId === session.id ? "text-black bg-accent" : "bg-primary"}
                        `}
                      value={editedTitle}
                      onChange={(e) => setEditedTitle(e.target.value)}
                      autoFocus
                      onBlur={() => setEditingSessionId(null)}
                    />
                  </form>
                ) : (
                  <div
                    className="text-sm font-medium truncate cursor-pointer"
                    onClick={(e) => {
                      // only current session can be edited
                      if ((currentSessionId === session.id)) {
                        e.stopPropagation()
                        setEditingSessionId(session.id)
                        setEditedTitle(session.title)
                      }
                    }}
                  >
                    {session.title}
                  </div>
                )}

                <div className="text-xs">
                  {session.createdAt.toLocaleDateString()}
                </div>
              </div>
            ) : (
              <MessageSquare className="w-4 h-4 ml-1" />
            )}

            {/* Delete Button */}
            {!collapsed && (
              <button
                className={`opacity-0 group-hover:opacity-100 ml-2 hover:text-red-500 p-1
                  ${currentSessionId === session.id ? "text-secondary" : "text-accent"}
                  `}
                onClick={(e) => {
                  e.stopPropagation()
                  deleteChatSession(session.id)
                }}
              >
                <X className="w-4 h-4" />
              </button>
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
    </div>
  )
}
