"use client";

import { RotateCcw } from "lucide-react";
import { useChatContext } from "@/context/ChatContext";
import { MessageList } from "./MessageList";
import { ChatInput } from "./ChatInput";

export function ChatContainer() {
  const { clearMessages, messages } = useChatContext();

  return (
    <div className="flex flex-col h-[100dvh] bg-bg-light">
      {/* Header */}
      <header className="bg-primary-teal text-white px-4 py-3 flex items-center justify-between flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <svg
              width="28"
              height="28"
              viewBox="0 0 28 28"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
              aria-hidden="true"
            >
              <rect width="28" height="28" rx="2" fill="white" />
              <path
                d="M6 8h16v2H6zM6 13h12v2H6zM6 18h14v2H6z"
                fill="#337778"
              />
            </svg>
            <div>
              <h1 className="text-base font-bold leading-tight">PartSelect</h1>
              <p className="text-[10px] text-teal-100 leading-tight">
                Parts Assistant
              </p>
            </div>
          </div>
        </div>
        {messages.length > 0 && (
          <button
            onClick={clearMessages}
            className="flex items-center gap-1.5 text-xs text-teal-100 hover:text-white transition-colors px-2 py-1"
          >
            <RotateCcw size={14} />
            New Chat
          </button>
        )}
      </header>

      {/* Messages */}
      <MessageList />

      {/* Input */}
      <ChatInput />
    </div>
  );
}
