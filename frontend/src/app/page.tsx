"use client";

import React, { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeRaw from "rehype-raw";
import { Send, Loader2, AlertCircle, User, Bot, Sparkles, RefreshCw, Mic, MicOff, Paperclip, X, Trash2, Menu, MessageSquarePlus } from "lucide-react";

// Backend URL. Use NEXT_PUBLIC_BACKEND_URL env var in production/deployment.
// Falls back to localhost:8001 for local development.
const getApiBase = () => {
  const envUrl = process.env.NEXT_PUBLIC_BACKEND_URL;
  // When explicitly set to an empty string, use same-origin requests so the
  // dev server can proxy /chat, /chats, /upload, /recommend and /advisor to
  // the local backend. Otherwise fall back to localhost:8001.
  if (envUrl === "") return "";
  return envUrl || "http://localhost:8001";
};

type Message = {
  role: "user" | "assistant";
  content: string;
};

type ChatSession = {
  id: string;
  title: string;
  messages: Message[];
  turn: number;
  isFinal: boolean;
  started: boolean;
  updatedAt: number;
};

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        "Hi! I'm your Career & Scholarship Advisor. Tell me about your background, interests, and goals to get started.",
    },
  ]);
  const [input, setInput] = useState("");
  const [turn, setTurn] = useState(0);
  const [isFinal, setIsFinal] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [started, setStarted] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [chatHistory, setChatHistory] = useState<ChatSession[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [currentChatId, setCurrentChatId] = useState<string>(() => Date.now().toString());
  const [userId, setUserId] = useState<string>("");
  const scrollRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<any>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const USER_ID_KEY = "career-scholar-agent-user-id";

  useEffect(() => {
    let uid = "";
    if (typeof window !== "undefined") {
      uid = localStorage.getItem(USER_ID_KEY) || "";
      if (!uid) {
        uid = Math.random().toString(36).substring(2) + Date.now().toString(36);
        localStorage.setItem(USER_ID_KEY, uid);
      }
      setUserId(uid);
    }
  }, []);

  useEffect(() => {
    if (userId) {
      fetchChats();
    }
  }, [userId]);

  const fetchChats = async () => {
    try {
      const res = await fetch(`${getApiBase()}/chats?user_id=${encodeURIComponent(userId)}`);
      if (!res.ok) throw new Error("Failed to load chats");
      const data = await res.json();
      setChatHistory(data.chats || []);
    } catch (err: any) {
      console.error("Failed to load chat history:", err);
    }
  };

  const persistChat = async (session: ChatSession) => {
    try {
      await fetch(`${getApiBase()}/chats`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          userId: userId,
          id: session.id,
          title: session.title,
          messages: session.messages,
          turn: session.turn,
          isFinal: session.isFinal,
          started: session.started,
        }),
      });
    } catch (err: any) {
      console.error("Failed to save chat:", err);
    }
  };

  const deleteChatApi = async (id: string) => {
    try {
      await fetch(`${getApiBase()}/chats/${id}?user_id=${encodeURIComponent(userId)}`, { method: "DELETE" });
    } catch (err: any) {
      console.error("Failed to delete chat:", err);
    }
  };

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, loading]);

  useEffect(() => {
    const timeout = setTimeout(() => {
      saveCurrentChat();
    }, 500);
    return () => clearTimeout(timeout);
  }, [messages, turn, isFinal, started]);

  const handleSend = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!input.trim() || loading) return;

    const userText = input.trim();
    const nextMessages: Message[] = [...messages, { role: "user", content: userText }];
    setMessages(nextMessages);
    setInput("");
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${getApiBase()}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: nextMessages, turn }),
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Server error ${res.status}: ${text || res.statusText}`);
      }

      const data = await res.json();
      setMessages((prev) => [...prev, { role: "assistant", content: data.reply }]);

      if (data.is_final) {
        setIsFinal(true);
      } else {
        setTurn((prev) => prev + 1);
      }
    } catch (err: any) {
      console.error("API Error:", err);
      let msg = err.message || "Failed to get a response.";
      const lower = msg.toLowerCase();
      if (lower.includes("rate limit")) {
        msg = "AI service rate limit reached. Please wait a moment and try again.";
      } else if (lower.includes("unavailable") || lower.includes("503") || lower.includes("busy")) {
        msg = "AI service is temporarily busy. Please wait a few seconds and try again.";
      } else if (lower.includes("500") || lower.includes("server error")) {
        msg = "Server is temporarily overloaded. Please wait a few seconds and try again.";
      } else if (msg.length > 200) {
        // Avoid dumping raw JSON/error details into the UI.
        msg = "Something went wrong. Please try again.";
      }
      setError(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || loading) return;
    setStarted(true);
    await handleSend();
  };

  const generateTitle = (msgs: Message[]) => {
    const firstUser = msgs.find((m) => m.role === "user");
    if (firstUser) {
      return firstUser.content.slice(0, 40) + (firstUser.content.length > 40 ? "..." : "");
    }
    return "New chat";
  };

  const saveCurrentChat = async () => {
    if (messages.length <= 1) return;
    const session: ChatSession = {
      id: currentChatId,
      title: generateTitle(messages),
      messages,
      turn,
      isFinal,
      started,
      updatedAt: Date.now(),
    };
    setChatHistory((prev) => {
      const filtered = prev.filter((s) => s.id !== session.id);
      return [session, ...filtered].slice(0, 50);
    });
    await persistChat(session);
  };

  const loadChat = (session: ChatSession) => {
    saveCurrentChat();
    setCurrentChatId(session.id);
    setMessages(session.messages);
    setTurn(session.turn);
    setIsFinal(session.isFinal);
    setStarted(session.started);
    setInput("");
    setError(null);
    setSidebarOpen(false);
  };

  const deleteChat = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setChatHistory((prev) => prev.filter((s) => s.id !== id));
    await deleteChatApi(id);
  };

  const handleNewChat = () => {
    saveCurrentChat();
    setMessages([
      {
        role: "assistant",
        content:
          "Hi! I'm your Career & Scholarship Advisor. Tell me about your background, interests, and goals to get started.",
      },
    ]);
    setInput("");
    setTurn(0);
    setIsFinal(false);
    setStarted(false);
    setError(null);
    setCurrentChatId(Date.now().toString());
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {}
      setIsListening(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(`${getApiBase()}/upload`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const text = await res.text();
        throw new Error(`Upload failed ${res.status}: ${text || res.statusText}`);
      }

      const data = await res.json();
      const docSummary = `[Uploaded document: ${data.filename}]\n\n${data.extracted_text}`;
      setInput((prev) => (prev ? prev + "\n\n" + docSummary : docSummary));
    } catch (err: any) {
      console.error("Upload Error:", err);
      setError(err.message || "Failed to upload document.");
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const getSpeechLang = () => {
    // Try to infer the user's language from the last user message.
    const lastUser = [...messages].reverse().find((m) => m.role === "user");
    const text = lastUser?.content || "";
    if (/[\u4e00-\u9fff]/.test(text)) return "zh-CN";
    if (/[\u0600-\u06ff]/.test(text)) return "ur-PK";
    if (/[\u0900-\u097f]/.test(text)) return "hi-IN";
    return "en-US";
  };

  const toggleListening = () => {
    if (!("webkitSpeechRecognition" in window || "SpeechRecognition" in window)) {
      setError("Voice input is not supported in this browser. Try Chrome or Edge.");
      return;
    }

    if (isListening && recognitionRef.current) {
      recognitionRef.current.stop();
      setIsListening(false);
      return;
    }

    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = getSpeechLang();

    recognition.onstart = () => setIsListening(true);
    recognition.onend = () => setIsListening(false);
    recognition.onerror = (event: any) => {
      setIsListening(false);
      if (event.error !== "aborted") {
        setError(`Voice input error: ${event.error}`);
      }
    };
    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setInput((prev) => (prev ? prev + " " + transcript : transcript));
    };

    recognitionRef.current = recognition;
    recognition.start();
  };

  const renderMarkdown = (text: string) => (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      rehypePlugins={[rehypeRaw]}
      components={{
        h1: ({ children }) => <h1 className="text-xl font-bold text-white mt-4 mb-2">{children}</h1>,
        h2: ({ children }) => <h2 className="text-lg font-semibold text-white mt-3 mb-2">{children}</h2>,
        h3: ({ children }) => <h3 className="text-base font-semibold text-white mt-3 mb-1">{children}</h3>,
        p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
        ul: ({ children }) => <ul className="list-disc pl-4 mb-2 space-y-0.5">{children}</ul>,
        ol: ({ children }) => <ol className="list-decimal pl-4 mb-2 space-y-0.5">{children}</ol>,
        li: ({ children }) => <li className="mb-0.5">{children}</li>,
        strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
        a: ({ href, children }) => (
          <a href={href} className="text-indigo-300 hover:text-indigo-200 underline" target="_blank" rel="noopener noreferrer">
            {children}
          </a>
        ),
        code: ({ children }) => (
          <code className="bg-slate-950/50 text-indigo-200 px-1 py-0.5 rounded text-xs">{children}</code>
        ),
        pre: ({ children }) => (
          <pre className="bg-slate-950/50 border border-slate-700 rounded-lg p-3 overflow-x-auto mb-2">{children}</pre>
        ),
        blockquote: ({ children }) => (
          <blockquote className="border-l-4 border-indigo-400 pl-3 italic text-slate-300 mb-2">{children}</blockquote>
        ),
      }}
    >
      {text}
    </ReactMarkdown>
  );

  const isComplete = isFinal && messages.length > 0 && messages[messages.length - 1].role === "assistant";

  const sidebarContent = (
    <>
      <div className="p-4 border-b border-slate-800">
        <button
          onClick={() => {
            handleNewChat();
            setSidebarOpen(false);
          }}
          className="w-full flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium transition"
        >
          <MessageSquarePlus className="w-4 h-4" />
          New chat
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-3 space-y-1">
        {chatHistory.length === 0 ? (
          <p className="text-slate-500 text-sm text-center py-8">No saved chats yet.</p>
        ) : (
          chatHistory.map((session) => (
            <div
              key={session.id}
              onClick={() => loadChat(session)}
              className={`group flex items-center justify-between gap-2 p-3 rounded-xl cursor-pointer transition ${
                session.id === currentChatId
                  ? "bg-indigo-500/10 text-indigo-200"
                  : "text-slate-300 hover:bg-slate-800"
              }`}
            >
              <div className="min-w-0 flex-1">
                <p className="text-sm truncate">{session.title}</p>
                <p className="text-xs text-slate-500">
                  {new Date(session.updatedAt).toLocaleDateString()}
                </p>
              </div>
              <button
                onClick={(e) => deleteChat(e, session.id)}
                className="p-1.5 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition opacity-0 group-hover:opacity-100"
                aria-label="Delete chat"
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          ))
        )}
      </div>
    </>
  );

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 flex overflow-hidden">
      {/* Collapsible sidebar overlay drawer */}
      <div
        className={`fixed inset-0 z-40 transition-opacity duration-300 ${
          sidebarOpen ? "opacity-100 pointer-events-auto" : "opacity-0 pointer-events-none"
        }`}
      >
        <div
          className="absolute inset-0 bg-black/60"
          onClick={() => setSidebarOpen(false)}
        />
        <aside
          className={`absolute left-0 top-0 bottom-0 w-72 flex flex-col bg-slate-950 border-r border-slate-800 transform transition-transform duration-300 ease-in-out ${
            sidebarOpen ? "translate-x-0" : "-translate-x-full"
          }`}
        >
          <div className="flex items-center justify-between p-4 border-b border-slate-800">
            <span className="font-semibold text-white">Chat history</span>
            <button
              onClick={() => setSidebarOpen(false)}
              className="p-2 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-white transition"
              aria-label="Close sidebar"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          {sidebarContent}
        </aside>
      </div>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col h-screen">
        {/* Header */}
        <div className="shrink-0 px-4 py-3 border-b border-slate-800 bg-slate-950/80 backdrop-blur-sm">
          <div className="max-w-3xl mx-auto flex items-center justify-between gap-4">
            <div className="flex items-center gap-3 min-w-0">
              <button
                onClick={() => setSidebarOpen(true)}
                className="p-2 rounded-xl bg-slate-900 border border-slate-800 text-slate-300 hover:bg-slate-800 hover:text-white transition"
                aria-label="Open chat history"
                title="Open chat history"
              >
                <Menu className="w-5 h-5" />
              </button>
              <div className="flex items-center gap-2 text-indigo-400 text-sm font-medium truncate">
                <Sparkles className="w-4 h-4 shrink-0" />
                <span className="hidden sm:inline">AI Career & Scholarship Advisor</span>
                <span className="sm:hidden">AI Advisor</span>
              </div>
            </div>
            <button
              onClick={handleNewChat}
              className="flex items-center gap-2 px-3 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white transition text-sm font-medium"
            >
              <RefreshCw className="w-4 h-4" />
              <span className="hidden sm:inline">New chat</span>
            </button>
          </div>
        </div>

        {/* Chat container */}
        <div
          ref={scrollRef}
          className="flex-1 overflow-y-auto space-y-4 px-4 md:px-6 pb-24"
        >
          {/* Sticky chat title header - stays visible while messages scroll underneath */}
          <div className="sticky top-0 z-10 bg-slate-950/95 backdrop-blur-sm border-b border-slate-800 -mx-4 md:-mx-6 px-4 md:px-6 py-5">
            <div className="max-w-3xl mx-auto">
              <h1 className="text-3xl md:text-4xl font-extrabold text-white tracking-tight">
                Your Personalized Growth Path
              </h1>
              <p className="text-sm md:text-base text-slate-400 mt-2">
                Career & Scholarship guidance tailored for you
              </p>
            </div>
          </div>

          {messages.map((msg, index) => (
            <div
              key={index}
              className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}
            >
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                  msg.role === "user" ? "bg-indigo-600" : "bg-slate-700"
                }`}
              >
                {msg.role === "user" ? (
                  <User className="w-4 h-4 text-white" />
                ) : (
                  <Bot className="w-4 h-4 text-indigo-300" />
                )}
              </div>
              <div
                className={`max-w-[80%] rounded-2xl px-5 py-3 text-sm leading-relaxed ${
                  msg.role === "user"
                    ? "bg-indigo-600 text-white rounded-br-none"
                    : "bg-slate-900 border border-slate-800 text-slate-200 rounded-bl-none"
                }`}
              >
                {msg.role === "assistant" ? renderMarkdown(msg.content) : msg.content}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 text-indigo-300" />
              </div>
              <div className="bg-slate-900 border border-slate-800 rounded-2xl rounded-bl-none px-5 py-3 flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin text-indigo-400" />
                <span className="text-sm text-slate-400">Thinking...</span>
              </div>
            </div>
          )}
        </div>

        {/* Input area */}
        <div className="shrink-0 pt-4 space-y-3">
          {error && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 flex items-center gap-2 text-sm">
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}

          {isComplete && (
            <button
              onClick={handleNewChat}
              className="w-full py-3 px-4 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium flex items-center justify-center gap-2 transition duration-200"
            >
              <RefreshCw className="w-4 h-4" />
              Start a new conversation
            </button>
          )}

          <form onSubmit={started ? handleSend : handleStart} className="flex gap-2 items-end">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                isListening
                  ? "Listening... speak now"
                  : started
                  ? "Type your answer and press Enter..."
                  : "Tell me about your background, interests, and goals..."
              }
              className="flex-1 min-h-[48px] rounded-xl bg-slate-900 border border-slate-800 px-4 py-3 text-base text-slate-100 placeholder-slate-500 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition duration-200 outline-none"
            />
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={loading || uploading}
              className="px-4 py-3 min-h-[48px] rounded-xl bg-slate-800 hover:bg-slate-700 disabled:bg-slate-800 disabled:cursor-not-allowed text-slate-200 flex items-center justify-center transition duration-200"
              aria-label="Upload document"
              title="Upload document (.txt, .pdf, .docx)"
            >
              {uploading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Paperclip className="w-5 h-5" />}
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt,.pdf,.docx"
              onChange={handleFileUpload}
              className="hidden"
            />
            <button
              type="button"
              onClick={toggleListening}
              disabled={loading || uploading}
              className={`px-4 py-3 min-h-[48px] rounded-xl flex items-center justify-center transition duration-200 ${
                isListening
                  ? "bg-rose-600 hover:bg-rose-500 text-white animate-pulse"
                  : "bg-slate-800 hover:bg-slate-700 text-slate-200"
              } disabled:bg-slate-800 disabled:cursor-not-allowed`}
              aria-label={isListening ? "Stop listening" : "Use microphone"}
              title={isListening ? "Stop listening" : "Use microphone"}
            >
              {isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
            </button>
            <button
              type="submit"
              disabled={loading || !input.trim()}
              className="px-4 py-3 min-h-[48px] rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:cursor-not-allowed text-white font-semibold flex items-center justify-center transition duration-200"
              aria-label="Send message"
            >
              {loading ? (
                <Loader2 className="w-5 h-5 animate-spin" />
              ) : (
                <Send className="w-5 h-5" />
              )}
            </button>
          </form>
        </div>
      </div>
    </main>
  );
}
