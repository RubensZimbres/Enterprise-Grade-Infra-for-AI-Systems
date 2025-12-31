"use client";

import React, { useState, useEffect, useRef } from "react";
import { Send, Bot, User, ShieldCheck, Loader2 } from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import { auth } from "@/lib/firebase"; // Import auth
import { useRouter } from "next/navigation"; // Import router

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [sessionId] = useState(() => Math.random().toString(36).substring(7));
  const scrollRef = useRef<HTMLDivElement>(null);
  const router = useRouter();

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMessage }]);
    setIsLoading(true);

    // Add empty assistant message for streaming
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    try {
      // Get fresh token
      const token = await auth.currentUser?.getIdToken();
      
      if (!token) {
        throw new Error("Authentication failed. Please login.");
      }

      // PROXY: Call local API route instead of direct backend URL
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`, // Send real token
        },
        body: JSON.stringify({
          message: userMessage,
          session_id: sessionId,
        }),
      });

      if (response.status === 402 || response.status === 403) {
        // Payment Required / Forbidden
        router.push("/payment");
        throw new Error("Subscription required. Redirecting to payment...");
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.error || "Failed to fetch");
      }

      const reader = response.body?.getReader();
      if (!reader) return;

      const decoder = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        
        setMessages((prev) => {
          const newMessages = [...prev];
          const lastIdx = newMessages.length - 1;
          
          if (lastIdx >= 0 && newMessages[lastIdx].role === "assistant") {
            newMessages[lastIdx] = {
              ...newMessages[lastIdx],
              content: newMessages[lastIdx].content + chunk
            };
          }
          return newMessages;
        });
      }
    } catch (error: any) {
      console.error("Streaming error:", error);
      setMessages((prev) => [
        ...prev.slice(0, -1),
        { role: "assistant", content: `⚠️ Error: ${error.message || "Connection to neural core lost."}` },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="flex flex-col h-screen max-w-4xl mx-auto p-4 md:p-8">
      {/* Header */}
      <header className="flex items-center justify-between mb-8 pb-4 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-blue-600 rounded-lg">
            <ShieldCheck className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold tracking-tight">Enterprise AI Agent</h1>
            <p className="text-sm text-slate-400">Secure RAG Pipeline v2.0</p>
          </div>
        </div>
        <div className="hidden md:block">
          <span className="px-3 py-1 text-xs font-medium bg-green-500/10 text-green-400 rounded-full border border-green-500/20">
            System Online
          </span>
        </div>
      </header>

      {/* Chat Container */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto space-y-6 mb-8 pr-4 scrollbar-hide"
      >
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center space-y-4">
            <Bot className="w-12 h-12 text-slate-700" />
            <div className="max-w-xs">
              <p className="text-slate-400">
                Welcome to the Secure Knowledge Base. Ask me anything about our internal documentation.
              </p>
            </div>
          </div>
        )}

        {messages.map((m, i) => (
          <div
            key={i}
            className={cn(
              "flex gap-4 p-4 rounded-2xl transition-all",
              m.role === "user" ? "bg-slate-900/50" : "bg-blue-600/5"
            )}
          >
            <div className={cn(
              "w-8 h-8 rounded-full flex items-center justify-center shrink-0",
              m.role === "user" ? "bg-slate-800" : "bg-blue-600"
            )}>
              {m.role === "user" ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4 text-white" />}
            </div>
            <div className="flex-1 space-y-2">
              <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">
                {m.role === "user" ? "Human" : "Neural Core"}
              </p>
              <div className="text-slate-200 leading-relaxed whitespace-pre-wrap">
                {m.content || (isLoading && i === messages.length - 1 && <Loader2 className="w-4 h-4 animate-spin text-blue-500" />)}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="relative">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Query the internal knowledge base..."
          className="w-full bg-slate-900 border border-slate-800 rounded-2xl py-4 pl-6 pr-14 focus:outline-none focus:ring-2 focus:ring-blue-600/50 transition-all placeholder:text-slate-600"
        />
        <button
          type="submit"
          disabled={isLoading || !input.trim()}
          className="absolute right-3 top-1/2 -translate-y-1/2 p-2 bg-blue-600 text-white rounded-xl hover:bg-blue-500 disabled:opacity-50 disabled:hover:bg-blue-600 transition-colors"
        >
          {isLoading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Send className="w-5 h-5" />}
        </button>
      </form>
      
      <footer className="mt-4 text-center">
        <p className="text-[10px] text-slate-600 uppercase tracking-[0.2em]">
          End-to-End Encrypted • DLP Guardrails Active
        </p>
      </footer>
    </main>
  );
}
