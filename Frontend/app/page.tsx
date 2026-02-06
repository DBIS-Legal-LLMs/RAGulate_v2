/**
 * GDPR Chatbot - Main Application Component
 *
 * This is the root component of the GDPR compliance chatbot application.
 * It provides an interactive interface for users to:
 * - Ask questions about GDPR compliance
 * - Upload and review documents
 * - Manage chat sessions
 * - View knowledge graphs
 *
 * @module GDPRChatbot
 */

"use client";

import type React from "react";

import { useState, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Send, MessageSquare, Shield, X, Folder } from "lucide-react";
import { ChatMessage } from "./components/chat-message";
import { ProfileDropdown } from "./components/profile-dropdown";
import { ProfileModal } from "./components/profile-modal";
import { SettingsModal } from "./components/settings-modal";
import { ThemeProvider } from "./components/theme-provider";
import { AuthModal } from "./components/auth-modal";
import { GraphOverlay } from "../components/GraphOverlay";
import { DocumentsModal } from "./components/documents-modal";
import Sidebar from "./components/SideBar";

/**
 * Backend API endpoint configuration
 * @constant {string}
 */
const BACKEND_URL = "http://134.60.71.197:8000";

/**
 * Represents a single chat message in the conversation
 * @interface Message
 * @property {string} id - Unique identifier for the message
 * @property {"user" | "assistant"} role - Sender role (user or AI assistant)
 * @property {string} content - Message content in markdown format
 * @property {Date} timestamp - When the message was sent
 * @property {string} [userName] - Optional username of the sender
 */
interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: Date;
  userName?: string;
}

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

/**
 * Main GDPR Chatbot component that handles the chat interface and session management
 * @returns {JSX.Element} The rendered chatbot interface
 */
export default function GDPRChatbot() {
  // Chat state management
  const [messages, setMessages] = useState<Message[]>([]); // Current conversation messages
  const [input, setInput] = useState(""); // User input field
  const [isLoading, setIsLoading] = useState(false); // Loading state for API calls

  // Session management
  const [folders, setFolders] = useState<UIFolder[]>([]);
  const [sessions, setSessions] = useState<UISession[]>([]);

  const [activeFolderId, setActiveFolderId] = useState<string | null>(null);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  const [editingFolderId, setEditingFolderId] = useState<string | null>(null);

  // UI References and state
  const messagesEndRef = useRef<HTMLDivElement>(null); // For auto-scrolling
  const [showProfileModal, setShowProfileModal] = useState(false); // Profile modal visibility
  const [showSettingsModal, setShowSettingsModal] = useState(false); // Settings modal visibility
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null); // Session being edited
  const [editedTitle, setEditedTitle] = useState<string>(""); // New title for edited session
  const [showAuthModal, setShowAuthModal] = useState(true); // Auth modal visibility

  const [username, setUsername] = useState<string>(""); // Current user's username

  // Modal and overlay state
  const [showGraph, setShowGraph] = useState(false); // Knowledge graph visibility
  const [showDocuments, setShowDocuments] = useState(false); // Documents modal visibility

  /* Helper Functions */
  const onUpdateDraftFolderName = (id: string, name: string) => {
    setFolders((prev) => prev.map((f) => (f.id === id ? { ...f, name } : f)));
  };

  const onCancelDraftFolder = (id: string) => {
    setFolders((prev) => prev.filter((f) => f.id !== id));
  };

  const onUpdateDraftSessionName = (id: string, title: string) => {
    setSessions((prev) => prev.map((f) => (f.id === id ? { ...f, title } : f)));
  };

  const onCancelDraftSession = (id: string) => {
    setSessions((prev) => prev.filter((f) => f.id !== id))
  }

  /**
   * Transforms a raw message object from the API into the frontend Message format
   *
   * @param {any} msg - Raw message object from backend
   * @returns {Message} Formatted message for frontend use
   *
   * @example
   * const formatted = transformMessage({
   *   _id: "123",
   *   role: "user",
   *   content: "Hello",
   *   timestamp: "2023-01-01T00:00:00Z",
   *   user_name: "john"
   * });
   */
  const transformMessage = (msg: any): Message => {
    return {
      id: msg.id || Date.now().toString(),
      role: msg.role as "user" | "assistant",
      content: msg.content,
      created_at: new Date(msg.created_at),
      userName: msg.user_name,
    };
  };

  /**
   * Scrolls the chat window to the most recent message
   * Used after new messages are added or on viewport changes
   */
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  /**
   * Adds delay, used to give delay for echo chat
   * @param ms time in ms
   */
  function delay(ms: number) {
    return new Promise( resolve => setTimeout(resolve, ms) );
  }

  /**
   * Load Messages from Backend
   */
  useEffect(() => {
    if (!activeSessionId) {
      setMessages([])
      return;
    } 

    const loadMessages = async () => {
      const token = localStorage.getItem("token");
      const res = await fetch(
        `${BACKEND_URL}/api/chat/sessions/${activeSessionId}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      );
      const data = await res.json();
      console.log(data.messages);

      setMessages((data.messages || []).map(transformMessage));
    };
    loadMessages();
  }, [activeSessionId]);

  /**
   * Handles the submission of new chat messages
   * Sends message to backend API and updates UI with response
   *
   * @param {React.FormEvent} e - Form submission event
   * @returns {Promise<void>}
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !activeSessionId) return;

    const token = localStorage.getItem("token");

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      created_at: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const res = await fetch(
        `${BACKEND_URL}/api/chat/sessions/${activeSessionId}/messages`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            content: input,
          }),
        }
      );

      if (!res.ok) throw new Error("Failed to send message");
      const data = await res.json();
      await delay(1000);

      if (data.assistant_message.id) {
        const assistantMessage: Message = {
          id: data.assistant_message.id,
          role: data.assistant_message.role as "assistant",
          content: data.assistant_message.content,
          created_at: new Date(data.assistant_message.created_at),
        };
        setMessages((prev) => [...prev, assistantMessage]);
      }
    } catch (error) {
      console.error("Error sending message:", error);
      const errorMessage: Message = {
        id: Date.now().toString() + "-error",
        role: "assistant",
        content:
          "Sorry, ich konnte deine Nachricht nicht senden. Bitte versuche es erneut.",
        created_at: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Fetch Folders from Backend
   */
  const fetchFolders = async () => {
    const token = localStorage.getItem("token");

    const res = await fetch(`${BACKEND_URL}/api/folderslist`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    if (!res.ok) throw new Error("Failed to fetch folders");
    return res.json();
  };

  /**
   * Retrieves all chat sessions for a given user from the backend
   */
  const fetchSessions = async () => {
    const token = localStorage.getItem("token");

    const res = await fetch(`${BACKEND_URL}/api/chat/sessions`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    return res.ok ? res.json() : [];
  };

  /**
   * Creates new Draft Session, this is only used for Frontend, is confirmed later
   */
  const createNewSession = () => {
    const tempId = `draft-${Date.now()}`

    const draftSession: UISession = {
      id: tempId,
      title: "",
      folderId: activeFolderId ?? null,
      createdAt: new Date(),
      isDraft: true,
    }

    setSessions((prev) => [draftSession,...prev])
    setEditingSessionId(tempId)
  }

  /**
   * Confirms the Session, sends a POST reuqest to the Backend to fully create the Session
   * @param tempId ID from Draft Session
   * @param name title of the Session
   * @param parentId which folder it belongs to
   */
  const confirmCreateSession = async (
    tempId: string,
    name:string,
    parentId: string | null
  ) => {
    console.log(name)
    console.log(parentId)
    const token = localStorage.getItem("token");
    const res = await fetch(`${BACKEND_URL}/api/chat/sessions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        title: name,
        folder_id: parentId
      }),
    });

    if (!res.ok) {
      onCancelDraftSession;
      setSessions((prev) => prev.filter((f) => f.id !== tempId));
      setEditingSessionId(null);
      alert("Folder konnte nicht erstellt werden (Name evtl. schon vergeben)");
      return;
    }

    const session = await res.json();

    setSessions((prev) => {
      const withoutDraft = prev.filter((s) => s.id !== tempId);

      const confirmedSession: UISession = {
        id: session.id,
        title: session.title,
        folderId: session.folder_id ?? null,
        createdAt: new Date(session.created_at ?? Date.now()),
        isDraft: false,
      };

      return [confirmedSession,...withoutDraft];
    });

    setEditingSessionId(null);
    setActiveSessionId(session.id);
  }

  /**
   * Create new Draft Folder, this is only used for Frontend, is confirmed later
   */
  const createNewFolder = () => {
    const tempId = `draft-${Date.now()}`;

    const draftFolder: UIFolder = {
      id: tempId,
      name: "",
      parentId: activeFolderId ?? null,
      depth: 0,
      createdAt: new Date(),
      isDraft: true,
    };

    setFolders((prev) => [draftFolder,...prev]);
    setEditingFolderId(tempId);
    setActiveSessionId(null);
  };

  /**
   * Confirms the Folder, sends a POST reuqest to the Backend to fully create the Folder
   * @param tempId ID from Draft Folder
   * @param name name of Folder
   * @param parentId which folder it belongs to, none for root folder
   */
  const confirmCreateFolder = async (
    tempId: string,
    name: string,
    parentId: string | null
  ) => {
    const token = localStorage.getItem("token");

    const res = await fetch(`${BACKEND_URL}/api/folders`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        name,
        parent_id: parentId,
      }),
    });

    if (!res.ok) {
      onCancelDraftFolder;
      setFolders((prev) => prev.filter((f) => f.id !== tempId));
      setEditingFolderId(null);
      setEditingFolderId(null);
      alert("Folder konnte nicht erstellt werden (Name evtl. schon vergeben)");
      return;
    }

    const folder = await res.json();

    setFolders((prev) =>
      prev.map((f) =>
        f.id === tempId
          ? {
              ...f, 
              id: folder.id, 
              name: folder.name,
              parentId: folder.parent_id,
              isDraft: false,
            }
          : f
      )
    );

    setEditingFolderId(null);
    setActiveFolderId(folder.id);
  };

  /**
   * Deleted Folder from Backend
   * @param folderId ID of folder
   */
  const deleteFolder = async (folderId: string) => {
    const token = localStorage.getItem("token");

    if (!confirm("Willst du diesen Ordner wirklich löschen?")) return;

    try {
      const res = await fetch(`${BACKEND_URL}/api/folders/${folderId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!res.ok) {
        alert(
          "Ordner konnte nicht gelöscht werden, evtl. ist Ordner nicht leer"
        );
        return;
      }

      // Folder aus State entfernen
      setFolders((prev) => prev.filter((f) => f.id !== folderId));

      // Falls dieser Ordner aktiv war → ActiveFolderId zurücksetzen
      if (activeFolderId === folderId) setActiveFolderId(null);
    } catch (error) {
      console.error(error);
      alert("Fehler beim Löschen des Ordners");
    }
  };

  /**
   * Delets Session from Backend
   * @param sessionID Id from Session
   */
  const deleteSession = async (sessionID: string) => {
    const token = localStorage.getItem("token");

    if(!confirm("Willst du diesen Chat wirklich löschen?")) return;

    try {
      const res = await fetch(`${BACKEND_URL}/api/chat/sessions/${sessionID}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        }
      });

      if (!res.ok) {
        alert(
          "Chat konnte nicht gelöscht werden."
        );
        return;
      }
      // remove Chat from State
      setSessions((prev) => prev.filter((f) => f.id !== sessionID));

      if (activeSessionId === sessionID) setActiveSessionId(null)
    } catch (error) {
      console.error(error);
      alert("Fehler beim Löschen des Chats")
    }
  }

  /**
   * Loads Sidebar content. Contains Sessions and Folders
   */
  useEffect(() => {
    const loadSidebarData = async () => {
      if (!username) return;

      /* 1. Folder */
      const rawFolders = await fetchFolders();
      console.log(rawFolders);
      const uiFolders: UIFolder[] = rawFolders.map((f: any) => ({
        id: f.id,
        name: f.name,
        parentId: f.parent_id,
        depth: f.depth,
        createdAt: new Date(f.created_at),
      }));

      /* 2. Sessions */
      const rawSessions = await fetchSessions();
      console.log(rawSessions);
      const uiSessions: UISession[] = rawSessions.map((s: any) => ({
        id: s.id,
        title: s.title,
        folderId: s.folder_id,
        createdAt: new Date(s.created_at),
      }));

      setFolders(uiFolders);
      setSessions(uiSessions);
    };

    loadSidebarData();
  }, [username]);

  /**
   * Handles successful user login
   * Loads user's existing chat sessions and sets up the interface
   *
   * @param {any} sessions - Initial sessions data from auth
   * @param {string} usernameFromAuth - Authenticated username
   *
   * @example
   * handleLoginSuccess(userSessions, "john_doe")
   */
  const handleLoginSuccess = async (
    _sessions: any,
    usernameFromAuth: string
  ) => {
    // RESET OLD USER STATE
    setFolders([]);
    setSessions([]);
    setMessages([]);
    setActiveFolderId(null);
    setActiveSessionId(null);
    setEditingFolderId(null);
    setEditingSessionId(null);
    setEditedTitle("");

    setUsername(usernameFromAuth);
    setShowAuthModal(false);
  };

  return (
    <ThemeProvider>
      {showAuthModal && (
        <div className="fixed inset-0 z-[2000] flex items-center justify-center bg-black/60 backdrop-blur-sm">
          <AuthModal onLoginSuccess={handleLoginSuccess} />
        </div>
      )}
      <div
        className={`${showAuthModal ? "pointer-events-none select-none" : ""}`}
        aria-hidden={showAuthModal ? "true" : "false"}
      >
        {/* Main Background */}
        <div className="flex h-screen">
          {/* 
          Sidebar Component
          Contains:
          - New chat button
          - List of chat sessions
          - Session management controls
          - Assistant info footer
        */}
          <Sidebar
            folders={folders}
            sessions={sessions}
            activeFolderId={activeFolderId}
            setActiveFolderId={setActiveFolderId}
            activeSessionId={activeSessionId}
            setActiveSessionId={setActiveSessionId}
            editingSessionId={editingSessionId}
            setEditingSessionId={setEditingSessionId}
            editedTitle={editedTitle}
            setEditedTitle={setEditedTitle}
            onNewChat={createNewSession}
            onNewFolder={createNewFolder}
            editingFolderId={editingFolderId}
            setEditingFolderId={setEditingFolderId}
            onConfirmCreateFolder={confirmCreateFolder}
            onUpdateDraftFolderName={onUpdateDraftFolderName}
            onCancelDraftFolder={onCancelDraftFolder}
            onDeleteFolder={deleteFolder}
            onConfirmCreateSession={confirmCreateSession}
            onCancelDraftSession={onCancelDraftSession}
            onUpdateDraftSessionName={onUpdateDraftSessionName}
            onDeleteSession={deleteSession}
          />

          {/* 
          Main Chat Area
          Contains:
          - Header with assistant info and controls
          - Message history with Markdown support
          - Input area for user messages
          - Loading indicators and status messages
        */}
          <div className="flex-1 flex flex-col bg-sidebar">
            {/* 
            Header Section
            Shows assistant identity and provides access to:
            - Graph visualization
            - Document management
            - Profile settings
          */}
            <div className="bg-toolbar p-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div>
                    <h1 className="text-lg font-semibold">
                      GDPR Compliance Assistant
                    </h1>
                    <p className="text-sm text-gray-600">
                      Ask me anything about GDPR regulations and compliance
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Button variant="ghost" className="hover:bg-accent hover:text-black" onClick={() => setShowGraph(true)}>
                    Graph
                  </Button>
                  <Button
                    variant="ghost" className="hover:bg-accent hover:text-black"
                    onClick={() => setShowDocuments(true)}
                  >
                    Documents
                  </Button>
                  <ProfileDropdown
                    username={username}
                    onProfileClick={() => setShowProfileModal(true)}
                    onSettingsClick={() => setShowSettingsModal(true)}
                  />
                </div>
              </div>
            </div>

            {/* 
            Messages Section
            Features:
            - Scrollable message history
            - Welcome message for empty chats
            - Markdown rendering for messages
            - Loading indicators
            - Auto-scroll behavior
          */}
            <ScrollArea className="flex-1 p-4 rounded-tl-2xl bg-chat">
              <div className="max-w-4xl mx-auto space-y-4">
                {messages.length === 0 && (
                  <div className="text-center py-12">
                    <Shield className="w-12 h-12 text-accent mx-auto mb-4" />
                    <h2 className="text-xl font-semibold mb-2">
                      Welcome to the RAGulate GDPR Assistant
                    </h2>
                    <p className="text-gray-600 mb-4">
                      I'm here to help you understand and comply with GDPR
                      regulations.
                    </p>
                  </div>
                )}

                {(!activeSessionId || editingSessionId) && (
                  <div className="flex justify-center">
                    <div className="p-4 flex flex-col items-center gap-3 w-full max-w-xs" >
                      <Button 
                        onClick={createNewSession}
                        className="w-full bg-primary hover:bg-accent border border-secondary text-black dark:text-white dark:hover:text-black " 
                      >
                        <MessageSquare className="w-4 h-4 mr-2" />
                        New Chat
                      </Button>

                      <Button
                        onClick={createNewFolder}
                        className="w-full bg-primary hover:bg-accent border border-secondary text-black dark:text-white dark:hover:text-black"
                      >
                        <Folder className="w-4 h-4 mr-2" />
                        New Folder
                      </Button>
                    </div>
                  </div>
                )}

                {messages.map((message) => (
                  <ChatMessage key={message.id} message={message} />
                ))}

                {isLoading && (
                  <div className="flex justify-start">
                    <div className="bg-gray-100 rounded-lg p-4 max-w-xs">
                      <div className="flex space-x-1">
                        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                        <div
                          className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                          style={{ animationDelay: "0.1s" }}
                        ></div>
                        <div
                          className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                          style={{ animationDelay: "0.2s" }}
                        ></div>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            </ScrollArea>

            {/* 
            Input Area
            Features:
            - Message input field
            - Send button with loading state
            - Helper text for document upload
            - Responsive layout with max width
            - Submit handling with error prevention
          */}
          {activeSessionId && !editingSessionId &&(
            <div className="bg-chat p-4">
              <div className="max-w-4xl mx-auto mb-5">
                <form onSubmit={handleSubmit} className="flex items-end">
                  <div className="flex-1 relative ">
                    <Input
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      placeholder="Ask about GDPR compliance, data protection, or upload documents for review..."
                      className="pr-12 min-h-[44px] resize-none bg-secondary dark:bg-primary border-sidebar-border"
                      disabled={isLoading}
                    />

                    {/* Button inside input */}
                    <button
                      type="submit"
                      disabled={isLoading || !input.trim()}
                      className="
                        absolute right-2 top-1/2 -translate-y-1/2 
                        p-2 rounded-md 
                        bg-white dark:bg-sidebar hover:bg-accent dark:hover:bg-accent dark:hover:text-black
                        text-invert
                      "
                    >
                      <Send className="w-4 h-4" />
                    </button>
                  </div>
                </form>

                <p className="text-xs text-gray-500 mt-2 text-center">
                  Upload documents for GDPR compliance review or ask questions
                  about data protection regulations
                </p>
              </div>
            </div>
          )}

          </div>

          {showProfileModal && (
            <ProfileModal
              username={username}
              onSaveUsername={(newName) => setUsername(newName)}
              onClose={() => setShowProfileModal(false)}
            />
          )}

          {showSettingsModal && (
            <SettingsModal
              onClose={() => setShowSettingsModal(false)}
              username={username}
            />
          )}
        </div>
      </div>
      {/* Graph Overlay */}
      <GraphOverlay open={showGraph} onClose={() => setShowGraph(false)} />
      {/* Documents Modal */}
      <DocumentsModal
        open={showDocuments}
        onClose={() => setShowDocuments(false)}
      />
    </ThemeProvider>
  );
}
