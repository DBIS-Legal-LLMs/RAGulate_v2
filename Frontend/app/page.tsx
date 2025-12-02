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
import { Send, MessageSquare, Shield, X } from "lucide-react";
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
  timestamp: Date;
  userName?: string;
}

/**
 * Represents a chat session with its messages and metadata
 * @interface ChatSession
 * @property {string} id - Unique identifier for the session
 * @property {string} title - Display title for the session
 * @property {Message[]} messages - Array of messages in the session
 * @property {Date} createdAt - Session creation timestamp
 * @property {string} sessionID - Backend reference ID for the session
 */
interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  sessionID: string;
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
  const [chatSessions, setChatSessions] = useState<ChatSession[]>([]); // All user's chat sessions
  const [currentSessionId, setCurrentSessionId] = useState<string | null>(null); // Active session ID

  // UI References and state
  const messagesEndRef = useRef<HTMLDivElement>(null); // For auto-scrolling
  const [showProfileModal, setShowProfileModal] = useState(false); // Profile modal visibility
  const [showSettingsModal, setShowSettingsModal] = useState(false); // Settings modal visibility
  const [editingSessionId, setEditingSessionId] = useState<string | null>(null); // Session being edited
  const [editedTitle, setEditedTitle] = useState<string>(""); // New title for edited session
  const [showAuthModal, setShowAuthModal] = useState(true); // Auth modal visibility

  // User and session state
  const [userSessions, setUserSessions] = useState<any[]>([]); // Raw session data from backend
  const [username, setUsername] = useState<string>(""); // Current user's username

  // Modal and overlay state
  const [showGraph, setShowGraph] = useState(false); // Knowledge graph visibility
  const [showDocuments, setShowDocuments] = useState(false); // Documents modal visibility

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
   * Generates a unique session identifier
   * Combines timestamp and random string for uniqueness
   * @returns {string} Unique session identifier
   */
  const generateSessionID = () => {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  };

  /**
   * Creates a new chat session and sets it as active
   * Adds the new session to the beginning of the sessions list
   * Clears current messages to start fresh conversation
   */
  const createNewChat = () => {
    const newSessionId = generateSessionID();
    const newSession: ChatSession = {
      id: Date.now().toString(),
      title: "New GDPR Consultation",
      messages: [],
      createdAt: new Date(),
      sessionID: newSessionId,
    };
    setChatSessions((prev) => [newSession, ...prev]);
    setCurrentSessionId(newSession.id);
    setMessages([]);
  };

  /**
   * Handles the submission of new chat messages
   * Sends message to backend API and updates UI with response
   *
   * @param {React.FormEvent} e - Form submission event
   * @returns {Promise<void>}
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: new Date(),
      userName: username,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const currentSession = chatSessions.find(
        (s) => s.id === currentSessionId
      );

      const response = await fetch(BACKEND_URL + "/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: input,
          sessionId: currentSession?.sessionID || "",
          userName: username,
        }),
      });

      if (!response.ok) {
        throw new Error("Failed to send message");
      }

      const data = await response.json();

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: data.answer,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error("Error sending message:", error);
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content:
          "Sorry, I encountered an error processing your request. Please try again.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Deletes a chat session and handles session switching
   * If deleted session is current, switches to another session or creates new one
   *
   * @param {string} sessionId - ID of session to delete
   *
   * @example
   * deleteChatSession("session123")
   *
   * @sideEffects
   * - Updates chatSessions state
   * - May update currentSessionId and messages
   * - May create new chat if last session deleted
   */
  const deleteChatSession = (sessionId: string) => {
    setChatSessions((prev) =>
      prev.filter((session) => session.id !== sessionId)
    );
    if (currentSessionId === sessionId) {
      // If the deleted session is current, switch to another or create new
      if (chatSessions.length > 1) {
        const nextSession = chatSessions.find((s) => s.id !== sessionId);
        if (nextSession) {
          setCurrentSessionId(nextSession.id);
          setMessages(nextSession.messages);
        }
      } else {
        createNewChat();
      }
    }
  };

  /**
   * Ensures initial chat session exists
   * Creates a new chat session if none exists on first load
   * Uses ref to prevent multiple creations on re-renders
   */
  const hasCreatedChat = useRef(false);
  useEffect(() => {
    if (!hasCreatedChat.current && chatSessions.length === 0) {
      createNewChat();
      hasCreatedChat.current = true;
    }
  }, []);

  /**
   * Monitors current session changes and logs session ID
   * Useful for debugging session switching and management
   */
  useEffect(() => {
    if (currentSessionId) {
      const session = chatSessions.find((s) => s.id === currentSessionId);
      if (session) {
        console.log("Current sessionID:", session.sessionID);
      }
    }
  }, [chatSessions, currentSessionId]);

  /**
   * Loads user's chat sessions on initial page load
   * Fetches all sessions and their details when user is authenticated
   * Sets the most recent session as active
   */
  useEffect(() => {
    const loadInitialSessions = async () => {
      if (username) {
        const userSessions = await fetchSessions(username);
        if (userSessions.sessions.length > 0) {
          const sessionsWithDetails = await Promise.all(
            userSessions.sessions.map(async (sessionId: string) => {
              const details = await fetchSessionDetails(sessionId);
              console.log("Session details for", sessionId, ":", details);
              return {
                id: sessionId,
                title: "GDPR Consultation", // Default title #TODO: not default name handling also needs to be sent to backend for saving of names
                messages: details ? details.map(transformMessage) : [],
                createdAt: new Date(),
                sessionID: sessionId,
              };
            })
          );

          setChatSessions(sessionsWithDetails);

          // Set the most recent session as current
          if (sessionsWithDetails.length > 0) {
            var lastIndex = sessionsWithDetails.length - 1;
            setCurrentSessionId(sessionsWithDetails[lastIndex].id);
            setMessages(sessionsWithDetails[lastIndex].messages || []);
          }
        }
      }
    };

    loadInitialSessions();
  }, [username]);

  /**
   * Retrieves all chat sessions for a given user from the backend
   *
   * @param {string} username - Username to fetch sessions for
   * @returns {Promise<{sessions: string[]}>} Array of session IDs
   *
   * @throws Will return empty array on fetch failure
   * @example
   * const sessions = await fetchSessions("john_doe");
   * // returns { sessions: ["session1", "session2"] }
   */
  const fetchSessions = async (username: string) => {
    try {
      const url = `${BACKEND_URL}/api/sessions?username=${encodeURIComponent(
        username
      )}`;
      console.log("Fetching sessions from:", url);
      const response = await fetch(url);
      if (!response.ok) throw new Error("Failed to fetch sessions");
      const sessions = await response.json();
      return sessions;
    } catch (error) {
      console.error("Error fetching sessions:", error);
      return [];
    }
  };

  /**
   * Fetches detailed information for a specific chat session
   * Including all messages and metadata
   *
   * @param {string} sessionId - ID of the session to fetch
   * @returns {Promise<any>} Session details including messages
   *
   * @throws Will return null on fetch failure
   * @example
   * const details = await fetchSessionDetails("session123");
   * // returns array of messages with content and metadata
   */
  const fetchSessionDetails = async (sessionId: string) => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/sessions/${sessionId}`);
      if (!response.ok) throw new Error("Failed to fetch session details");
      const sessionDetails = await response.json();
      return sessionDetails;
    } catch (error) {
      console.error("Error fetching session details:", error);
      return null;
    }
  };

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
    sessions: any,
    usernameFromAuth: string
  ) => {
    setUsername(usernameFromAuth);
    setShowAuthModal(false);

    const userSessions = await fetchSessions(usernameFromAuth);
    if (userSessions.sessions.length > 0) {
      const sessionsWithDetails = await Promise.all(
        userSessions.sessions.map(async (sessionId: string) => {
          const details = await fetchSessionDetails(sessionId);
          return {
            id: sessionId,
            title: "GDPR Consultation",
            messages: details ? details.map(transformMessage) : [],
            createdAt: new Date(),
            sessionID: sessionId,
          };
        })
      );

      setChatSessions(sessionsWithDetails);

      if (sessionsWithDetails.length > 0) {
        setCurrentSessionId(sessionsWithDetails[0].id);
        setMessages(sessionsWithDetails[0].messages || []);
      }
    }
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
      id: msg._id || Date.now().toString(),
      role: msg.role as "user" | "assistant",
      content: msg.content,
      timestamp: new Date(msg.timestamp),
      userName: msg.user_name,
    };
  };

  return (
    <ThemeProvider>
      {/* {showAuthModal && <AuthModal onLoginSuccess={handleLoginSuccess} />} */}
      {/* Main Background */}
      <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
        {/* 
          Sidebar Component
          Contains:
          - New chat button
          - List of chat sessions
          - Session management controls
          - Assistant info footer
        */}
        <Sidebar
          chatSessions={chatSessions}
          currentSessionId={currentSessionId}
          createNewChat={createNewChat}
          setCurrentSessionId={setCurrentSessionId}
          setMessages={setMessages}
          deleteChatSession={deleteChatSession}
          editingSessionId={editingSessionId}
          setEditingSessionId={setEditingSessionId}
          editedTitle={editedTitle}
          setEditedTitle={setEditedTitle}
        />

        {/* 
          Main Chat Area
          Contains:
          - Header with assistant info and controls
          - Message history with Markdown support
          - Input area for user messages
          - Loading indicators and status messages
        */}
        <div className="flex-1 flex flex-col bg-chat">
          {/* 
            Header Section
            Shows assistant identity and provides access to:
            - Graph visualization
            - Document management
            - Profile settings
          */}
          <div className="bg-toolbar border-b border-sidebar-border p-4">
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
                {/* <Button variant="outline" onClick={() => setShowGraph(true)}>
                  Graph
                </Button>
                <Button variant="outline" onClick={() => setShowDocuments(true)}>
                  Documents
                </Button> */}
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
          <ScrollArea className="flex-1 p-4 bg-chat">
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
          <div className="bg-chat p-4 mb-10">
            <div className="max-w-4xl mx-auto">
              <form onSubmit={handleSubmit} className="flex items-end">
                <div className="flex-1 relative">
                  <Input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask about GDPR compliance, data protection, or upload documents for review..."
                    className="pr-12 min-h-[44px] resize-none bg-primary border-sidebar-border"
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
      {/* Graph Overlay */}
      <GraphOverlay open={showGraph} onClose={() => setShowGraph(false)} />
      {/* Documents Modal */}
      <DocumentsModal
        open={showDocuments}
        onClose={() => setShowDocuments(false)}
      />

      {/* Bottom Bar */}
      <div
        className="fixed bottom-0 left-0 right-0 py-2 px-4 bg-sidebar
                      border-t border-sidebar-border text-sm 
                      text-gray-600 dark:text-gray-300 flex justify-between z-50"
      >
        <span>RAGulate</span>
        <span>v{process.env.NEXT_PUBLIC_APP_VERSION}</span>
      </div>
    </ThemeProvider>
  );
}
