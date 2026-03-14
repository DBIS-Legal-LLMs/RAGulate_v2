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
import "./i18n";
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
import { useTranslation } from "react-i18next";

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
  title: string;
  parent_folder_id: string | null;
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
  const abortRef = useRef<AbortController | null>(null);
  const [streamingEnabled, setStreamingEnabled] = useState(true); //switch for chat streaming or whole

  // Session management
  const [folders, setFolders] = useState<UIFolder[]>([]);
  const [sessions, setSessions] = useState<UISession[]>([]);

  const [activeFolderId, setActiveFolderId] = useState<string | null>(null);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  const [editingFolderId, setEditingFolderId] = useState<string | null>(null);

  const [isSessionLoading, setIsSessionLoading] = useState(false);

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
  const { t } = useTranslation();

  /* Helper Functions */
  const onUpdateDraftFolderName = (id: string, title: string) => {
    setFolders((prev) => prev.map((f) => (f.id === id ? { ...f, title } : f)));
  };

  const onCancelDraftFolder = (id: string) => {
    setFolders((prev) => prev.filter((f) => f.id !== id));
  };

  const onUpdateDraftSessionName = (id: string, title: string) => {
    setSessions((prev) => prev.map((f) => (f.id === id ? { ...f, title } : f)));
  };

  const onCancelDraftSession = (id: string) => {
    setSessions((prev) => prev.filter((f) => f.id !== id));
  };

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
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  /**
   * Load Messages from Backend
   */
  useEffect(() => {
    if (!activeSessionId) {
      setMessages([]);
      return;
    }

    const loadMessages = async () => {
      setIsSessionLoading(true);
      const token = localStorage.getItem("token");
      const res = await fetch(`${BACKEND_URL}/api/chat/${activeSessionId}`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      const data = await res.json();
      console.log(data.messages);

      setMessages((data.messages || []).map(transformMessage));
      setIsSessionLoading(false);
    };
    loadMessages();
  }, [activeSessionId]);

  /**
   * Decides weather to stream the answer from the LLM or get the whole, set by a button
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (streamingEnabled) {
      await handleSubmitStream();
    } else {
      await handleSubmitNormal();
    }
  };

  /**
   * Handles the submission of new chat messages via stream
   * Sends message to backend API and updates UI with chunks send from the backend.
   *
   * @param {React.FormEvent} e - Form submission event
   * @returns {Promise<void>}
   */
  const handleSubmitStream = async () => {
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

    // Platzhalter für die streaming Antwort
    const placeholderId = Date.now().toString() + "-assistant";
    setMessages((prev) => [
      ...prev,
      {
        id: placeholderId,
        role: "assistant",
        content: "",
        created_at: new Date(),
      },
    ]);

    abortRef.current = new AbortController();

    try {
      const res = await fetch(
        `${BACKEND_URL}/api/chat/${activeSessionId}/messages`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
            Accept: "text/event-stream",
          },
          body: JSON.stringify({ content: input }),
          signal: abortRef.current.signal,
        },
      );

      if (!res.ok) throw new Error("Failed to send message");

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // SSE Events sind durch \n\n getrennt
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          for (const line of part.split("\n")) {
            if (!line.startsWith("data: ")) continue;

            const data = line.slice(6).trim();
            if (data === "[DONE]") break;

            try {
              const parsed = JSON.parse(data);

              if (parsed.type === "done") {
                // Komplette Antwort vom Backend → Platzhalter überschreiben
                // Das korrigiert auch einen abgebrochenen Stream automatisch!!!
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === placeholderId
                      ? { ...m, content: parsed.content } // replaces text at the end
                      : m,
                  ),
                );
                continue;
              }
              const chunk =
                parsed.choices?.[0]?.delta?.content ??
                parsed.content ??
                parsed.text ??
                "";
              if (chunk) {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === placeholderId
                      ? { ...m, content: m.content + chunk }
                      : m,
                  ),
                );
              }
            } catch {
              // rohen Text anhängen
              if (data) {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === placeholderId
                      ? { ...m, content: m.content + data }
                      : m,
                  ),
                );
              }
            }
          }
        }
      }
    } catch (error: any) {
      if (error.name === "AbortError") return;

      console.error("Error sending message:", error);
      // Platzhalter durch Fehlermeldung ersetzen
      setMessages((prev) =>
        prev.map((m) =>
          m.id === placeholderId
            ? {
                ...m,
                content: t("chat.error"),
              }
            : m,
        ),
      );
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Handles the submission of new chat messages
   * Sends message to backend API and updates UI with the whole message.
   *
   * @param {React.FormEvent} e - Form submission event
   * @returns {Promise<void>}
   */
  const handleSubmitNormal = async () => {
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
        `${BACKEND_URL}/api/chat/${activeSessionId}/messages`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ content: input }),
        },
      );

      if (!res.ok) throw new Error("Failed to send message");

      const reader = res.body!.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          for (const line of part.split("\n")) {
            if (!line.startsWith("data: ")) continue;
            const data = line.slice(6).trim();

            try {
              const parsed = JSON.parse(data);

              // Wait for data: done, skips the chunks
              if (parsed.type === "done") {
                setMessages((prev) => [
                  ...prev,
                  {
                    id: Date.now().toString() + "-assistant",
                    role: "assistant",
                    content: parsed.content,
                    created_at: new Date(),
                  },
                ]);
                return;
              }
            } catch {
              /* ignore chunk Events */
            }
          }
        }
      }
    } catch (error) {
      console.error("Error sending message:", error);
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString() + "-error",
          role: "assistant",
          content: t("chat.error"),
          created_at: new Date(),
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Fetch Folders from Backend, gives additional parent folder id to load subfolders
   */
  const fetchFolders = async (parent_id?: string) => {
    const token = localStorage.getItem("token");
    const url = new URL(`${BACKEND_URL}/api/folderslist`);

    if (parent_id) {
      url.searchParams.append("parent_folder_id", parent_id);
    }
    const res = await fetch(url.toString(), {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    if (!res.ok) throw new Error("Failed to fetch folders");
    return res.json();
  };

  /**
   * Loads content of a folder when active Folder ID changes, this indicates that a folder was selected
   */
  useEffect(() => {
    if (activeFolderId === null) return;

    loadFolderContent(activeFolderId);
  }, [activeFolderId]);

  /**
   * Loads content for a folder, this includes Folders and Chat sessions
   */
  const loadFolderContent = async (folderId: string | null) => {
    const token = localStorage.getItem("token");

    /* Load subfolder */
    const folderUrl = new URL(`${BACKEND_URL}/api/folderslist`);
    if (folderId) folderUrl.searchParams.append("parent_folder_id", folderId);

    const folderRes = await fetch(folderUrl.toString(), {
      headers: { Authorization: `Bearer ${token}` },
    });

    const rawFolders = await folderRes.json();

    const uiFolders: UIFolder[] = rawFolders.map((f: any) => ({
      id: f.id,
      title: f.title,
      parent_folder_id: f.parent_folder_id,
      depth: f.depth,
      createdAt: new Date(f.created_at),
    }));

    /* Load Sessions*/
    const sessionUrl = new URL(`${BACKEND_URL}/api/chat/list/`);
    if (folderId) sessionUrl.searchParams.append("folder_id", folderId);

    const sessionRes = await fetch(sessionUrl.toString(), {
      headers: { Authorization: `Bearer ${token}` },
    });

    const rawSessions = await sessionRes.json();

    const uiSessions: UISession[] = rawSessions.map((s: any) => ({
      id: s.id,
      title: s.title,
      folderId: s.folder_id,
      createdAt: new Date(s.created_at),
    }));
    setFolders((prev) => {
      const filtered = prev.filter(
        (f) => f.isDraft || f.parent_folder_id !== activeFolderId,
      );
      return [...filtered, ...uiFolders];
    });
    setSessions(uiSessions);
  };

  /**
   * Retrieves all chat sessions for a given user from the backend
   */
  const fetchSessions = async () => {
    const token = localStorage.getItem("token");

    const res = await fetch(`${BACKEND_URL}/api/chat/list/`, {
      headers: { Authorization: `Bearer ${token}` },
    });

    return res.ok ? res.json() : [];
  };

  /**
   * Creates new Draft Session, this is only used for Frontend, is confirmed later
   */
  const createNewSession = () => {
    const tempId = `draft-${Date.now()}`;

    const draftSession: UISession = {
      id: tempId,
      title: "",
      folderId: activeFolderId ?? null,
      createdAt: new Date(),
      isDraft: true,
    };

    setSessions((prev) => [draftSession, ...prev]);
    setEditingSessionId(tempId);
  };

  /**
   * Confirms the Session, sends a POST reuqest to the Backend to fully create the Session
   * @param tempId ID from Draft Session
   * @param name title of the Session
   * @param parentId which folder it belongs to
   */
  const confirmCreateSession = async (
    tempId: string,
    name: string,
    parentId: string | null,
  ) => {
    // console.log(name);
    // console.log(parentId);
    const token = localStorage.getItem("token");
    const res = await fetch(`${BACKEND_URL}/api/chat/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        title: name,
        folder_id: parentId,
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

      return [confirmedSession, ...withoutDraft];
    });

    setEditingSessionId(null);
    setActiveSessionId(session.id);
  };

  /**
   * Create new Draft Folder, this is only used for Frontend, is confirmed later
   */
  const createNewFolder = () => {
    const tempId = `draft-${Date.now()}`;

    const draftFolder: UIFolder = {
      id: tempId,
      title: "",
      parent_folder_id: activeFolderId ?? null,
      depth: 0,
      createdAt: new Date(),
      isDraft: true,
    };

    setEditingFolderId(tempId);
    setFolders((prev) => [draftFolder, ...prev]);
    // setEditingFolderId(tempId);
    // setActiveSessionId(null);
  };

  /**
   * Confirms the Folder, sends a POST reuqest to the Backend to fully create the Folder
   * @param tempId ID from Draft Folder
   * @param name name of Folder
   * @param parent_folder_id which folder it belongs to, none for root folder
   */
  const confirmCreateFolder = async (
    tempId: string,
    title: string,
    parent_folder_id: string | null,
  ) => {
    const token = localStorage.getItem("token");

    const res = await fetch(`${BACKEND_URL}/api/folders`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({
        title,
        parent_folder_id,
      }),
    });

    if (!res.ok) {
      onCancelDraftFolder;
      setFolders((prev) => prev.filter((f) => f.id !== tempId));
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
              title: folder.title,
              parent_folder_id: folder.parent_folder_id,
              isDraft: false,
            }
          : f,
      ),
    );

    setEditingFolderId(null);
    setActiveFolderId(folder.id);
    setActiveSessionId(null);
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
          "Ordner konnte nicht gelöscht werden, evtl. ist Ordner nicht leer",
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

    if (!confirm("Willst du diesen Chat wirklich löschen?")) return;

    try {
      const res = await fetch(`${BACKEND_URL}/api/chat/${sessionID}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!res.ok) {
        alert("Chat konnte nicht gelöscht werden.");
        return;
      }
      // remove Chat from State
      setSessions((prev) => prev.filter((f) => f.id !== sessionID));

      if (activeSessionId === sessionID) setActiveSessionId(null);
    } catch (error) {
      console.error(error);
      alert("Fehler beim Löschen des Chats");
    }
  };

  const moveFolder = async (folderId: string, newFolderId: string | null) => {
    console.log(folderId, newFolderId);
  };

  const moveSession = async (sessionId: string, newFolderId: string | null) => {
    console.log(sessionId, newFolderId);
  };

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
        title: f.title,
        parent_folder_id: f.parent_folder_id,
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
    usernameFromAuth: string,
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

  const activeFolder = folders.find((f) => f.id === activeFolderId);

  const sessionsInActiveFolder = sessions.filter(
    (s) => s.folderId === activeFolderId,
  );
  const foldersinActiveFolder = folders.filter(
    (f) => f.parent_folder_id === activeFolderId,
  );

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
            onMoveFolder={moveFolder}
            onMoveSession={moveSession}
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
                      {t("header.title")}
                    </h1>
                    <p className="text-sm text-gray-600">
                      {t("header.subtitle")}
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2">
                  <Button
                    variant="ghost"
                    className="hover:bg-accent hover:text-black"
                    onClick={() => setShowGraph(true)}
                  >
                    {t("buttons.graph")}
                  </Button>
                  <Button
                    variant="ghost"
                    className="hover:bg-accent hover:text-black"
                    onClick={() => setShowDocuments(true)}
                  >
                    {t("buttons.documents")}
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
              <div className="max-w-4xl mx-auto space-y-6">
                {/* ================= FOLDER VIEW ================= */}
                {activeFolderId && !activeSessionId && activeFolder && (
                  <>
                    <div className="text-center py-6">
                      <h2 className="text-4xl font-semibold">
                        {activeFolder.title}
                      </h2>
                    </div>

                    <div className="space-y-2">
                      <p className="text-sm text-gray-500">
                        {t("folder.subfolderCount", {
                          count: foldersinActiveFolder.length,
                        })}
                      </p>
                      {/* Displays Subfolders for Active Folder */}
                      {foldersinActiveFolder
                        .sort((a, b) => {
                          // Drafts on top
                          if (a.isDraft && !b.isDraft) return -1;
                          if (!a.isDraft && b.isDraft) return 1;
                          return b.createdAt.getTime() - a.createdAt.getTime();
                        })
                        .map((folder) => (
                          <Card
                            key={folder.id}
                            className="p-4 cursor-pointer bg-sidebar hover:bg-accent hover:text-black transition border-none"
                            onClick={() => setActiveFolderId(folder.id)}
                          >
                            {folder.isDraft && editingFolderId === folder.id ? (
                              <input
                                autoFocus
                                value={folder.title}
                                onChange={(e) => {
                                  const value = e.target.value;
                                  onUpdateDraftFolderName(folder.id, value);
                                }}
                                onKeyDown={(e) => {
                                  if (
                                    e.key === "Enter" &&
                                    folder.title.trim()
                                  ) {
                                    confirmCreateFolder(
                                      folder.id,
                                      folder.title,
                                      folder.parent_folder_id,
                                    );
                                  }
                                  if (e.key === "Escape") {
                                    onCancelDraftFolder(folder.id);
                                    setEditingFolderId(null);
                                    // setActiveFolderId(null);
                                  }
                                }}
                                onBlur={() => {
                                  if (folder.title.trim()) {
                                    confirmCreateFolder(
                                      folder.id,
                                      folder.title,
                                      folder.parent_folder_id,
                                    );
                                  } else {
                                    onCancelDraftFolder(folder.id);
                                  }
                                  setEditingFolderId(null);
                                }}
                                className="w-full bg-transparent border-b border-accent outline-none px-1"
                                placeholder={t("folder.placeholderFolder")}
                              />
                            ) : (
                              <div className="flex justify-between items-center">
                                <span className="flex font-medium">
                                  <Folder className="w-4 h-4 mr-2 mt-1" />
                                  {folder.title || t("folder.untitledChat")}
                                </span>
                                <span className="text-xs text-gray-500">
                                  {folder.createdAt.toLocaleDateString()}
                                </span>
                              </div>
                            )}
                          </Card>
                        ))}

                      {foldersinActiveFolder.length === 0 && (
                        <p className="text-center text-gray-500 py-4">
                          {t("folder.emptyFolders")}
                        </p>
                      )}
                    </div>

                    <div className="space-y-2">
                      <p className="text-sm text-gray-500">
                        {sessionsInActiveFolder.length}{" "}
                        {t("folder.chatCount", {
                          count: sessionsInActiveFolder.length,
                        })}
                      </p>
                      {sessionsInActiveFolder.map((session) => (
                        <Card
                          key={session.id}
                          className="p-4 cursor-pointer bg-sidebar hover:bg-accent hover:text-black transition border-none"
                          onClick={() => setActiveSessionId(session.id)}
                        >
                          {session.isDraft &&
                          editingSessionId === session.id ? (
                            <input
                              autoFocus
                              value={editedTitle}
                              onChange={(e) => setEditedTitle(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === "Enter" && editedTitle.trim()) {
                                  confirmCreateSession(
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
                                  confirmCreateSession(
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
                              placeholder={t("folder.placeholderChat")}
                            />
                          ) : (
                            <div className="flex justify-between items-center">
                              <span className="flex font-medium">
                                <MessageSquare className="w-4 h-4 mr-2 mt-1" />
                                {session.title || t("folder.untitledChat")}
                              </span>
                              <span className="text-xs text-gray-500">
                                {session.createdAt.toLocaleDateString()}
                              </span>
                            </div>
                          )}
                        </Card>
                      ))}

                      {sessionsInActiveFolder.length === 0 && (
                        <p className="text-center text-gray-500 py-4">
                          {t("folder.emptyChats")}
                        </p>
                      )}
                    </div>

                    <div className="p-4 flex flex-col items-center justify-center gap-3 w-full max-w-xs mx-auto">
                      <Button
                        onClick={createNewSession}
                        className="w-full bg-sidebar hover:bg-accent border border-secondary text-black dark:text-white dark:hover:text-black dark:bg-primary dark:hover:bg-accent"
                      >
                        <MessageSquare className="w-4 h-4 mr-2" />
                        {t("buttons.newChat")}
                      </Button>

                      <Button
                        onClick={createNewFolder}
                        className="w-full bg-sidebar hover:bg-accent border border-secondary text-black dark:text-white dark:hover:text-black dark:bg-primary dark:hover:bg-accent"
                      >
                        <Folder className="w-4 h-4 mr-2" />
                        {t("buttons.newFolder")}
                      </Button>
                    </div>
                  </>
                )}

                {/* ================= CHAT VIEW ================= */}
                {activeSessionId && (
                  <>
                    {/*Session Loader */}
                    {isSessionLoading && (
                      <div className="flex justify-center py-12">
                        <div className="flex flex-col items-center gap-3">
                          <div className="w-8 h-8 border-4 border-accent border-t-transparent rounded-full animate-spin"></div>
                          <p className="text-gray-500 text-sm">
                            {t("chat.loading")}
                          </p>
                        </div>
                      </div>
                    )}

                    {/*Messages */}
                    {!isSessionLoading && messages.length > 0 && (
                      <>
                        {messages.map((message) => (
                          <ChatMessage key={message.id} message={message} />
                        ))}
                      </>
                    )}

                    {/*Empty Chat Welcome */}
                    {!isSessionLoading && messages.length === 0 && (
                      <div className="text-center py-12">
                        <Shield className="w-12 h-12 text-accent mx-auto mb-4" />
                        <h2 className="text-xl font-semibold mb-2">
                          {t("welcome.title")}
                        </h2>
                        <p className="text-gray-600 mb-4">
                          {t("welcome.subtitle")}
                        </p>
                      </div>
                    )}
                    {isLoading &&
                      messages[messages.length - 1]?.role === "user" && (
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
                  </>
                )}

                {/* ================= DEFAULT VIEW ================= */}
                {!activeFolderId && !activeSessionId && (
                  <div className="flex flex-col items-center justify-center">
                    <div className="text-center py-12">
                      <Shield className="w-12 h-12 text-accent mx-auto mb-4" />
                      <h2 className="text-xl font-semibold mb-2">
                        {t("welcome.title")}
                      </h2>
                      <p className="text-gray-600 mb-4">
                        {t("welcome.subtitle")}
                      </p>
                      <p className="text-gray-600 mb-4">
                        {t("welcome.selectChat")}
                      </p>
                    </div>

                    <div className="p-4 flex flex-col items-center gap-3 w-full max-w-xs">
                      <Button
                        onClick={createNewSession}
                        className="w-full bg-sidebar hover:bg-accent border border-secondary text-black dark:text-white dark:hover:text-black dark:bg-primary dark:hover:bg-accent"
                      >
                        <MessageSquare className="w-4 h-4 mr-2" />
                        {t("buttons.newChat")}
                      </Button>

                      <Button
                        onClick={createNewFolder}
                        className="w-full bg-sidebar hover:bg-accent border border-secondary text-black dark:text-white dark:hover:text-black dark:bg-primary dark:hover:bg-accent"
                      >
                        <Folder className="w-4 h-4 mr-2" />
                        {t("buttons.newFolder")}
                      </Button>
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
            {activeSessionId && !editingSessionId && (
              <div className="bg-chat p-4">
                <div className="max-w-4xl mx-auto mb-5">
                  <div className="flex items-center gap-2 mb-3">
                    <button
                      type="button"
                      onClick={() => setStreamingEnabled((prev) => !prev)}
                      className={`relative inline-flex h-5 w-10 items-center rounded-full transition-colors ${
                        streamingEnabled ? "bg-accent" : "bg-gray-300"
                      }`}
                    >
                      <span
                        className={`inline-block h-3 w-3 transform rounded-full bg-white transition-transform ${
                          streamingEnabled ? "translate-x-6" : "translate-x-1"
                        }`}
                      />
                    </button>
                    <span className="text-xs text-gray-500">
                      {streamingEnabled
                        ? t("chat.streamingOn")
                        : t("chat.streamingOff")}
                    </span>
                  </div>

                  <form onSubmit={handleSubmit} className="flex items-end">
                    <div className="flex-1 relative ">
                      <Input
                        value={input}
                        onChange={(e) => setInput(e.target.value)}
                        placeholder={t("chat.inputPlaceholder")}
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
                    {t("chat.inputHint")}
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
