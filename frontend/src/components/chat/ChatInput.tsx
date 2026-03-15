"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send, Square } from "lucide-react";
import { useChatContext } from "@/context/ChatContext";
import { useSTT } from "@/hooks/useSTT";
import { VoiceInputButton } from "@/components/shared/VoiceInputButton";

export function ChatInput() {
  const { sendMessage, stopStreaming, isStreaming } = useChatContext();
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleTranscript = useCallback((text: string) => {
    setInput((prev) => (prev ? prev + " " + text : text));
  }, []);

  const { isListening, isSupported, toggle: toggleSTT } =
    useSTT(handleTranscript);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height =
        Math.min(textareaRef.current.scrollHeight, 120) + "px";
    }
  }, [input]);

  const handleSubmit = () => {
    if (!input.trim() || isStreaming) return;
    sendMessage(input);
    setInput("");
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t border-border bg-white px-4 py-3">
      <div className="flex items-end gap-2 max-w-3xl mx-auto">
        <VoiceInputButton
          isListening={isListening}
          isSupported={isSupported}
          onToggle={toggleSTT}
        />
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about parts, compatibility, or appliance issues..."
            rows={1}
            className="w-full resize-none border border-border bg-bg-light px-3 py-2.5 text-sm text-body-text placeholder:text-muted-text focus:outline-none focus:ring-2 focus:ring-cta-yellow focus:border-transparent"
          />
        </div>
        {isStreaming ? (
          <button
            onClick={stopStreaming}
            className="flex items-center justify-center w-10 h-10 bg-error-red text-white hover:bg-red-700 transition-colors flex-shrink-0"
            aria-label="Stop generating"
          >
            <Square size={16} />
          </button>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={!input.trim()}
            className="flex items-center justify-center w-10 h-10 bg-cta-yellow text-body-text hover:bg-yellow-dark transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0"
            aria-label="Send message"
          >
            <Send size={16} />
          </button>
        )}
      </div>
      <p className="text-center text-[10px] text-muted-text mt-1.5 max-w-3xl mx-auto">
        AI assistant for PartSelect.com - Refrigerators & Dishwashers only
      </p>
    </div>
  );
}
