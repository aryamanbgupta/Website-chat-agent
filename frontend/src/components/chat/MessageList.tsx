"use client";

import { useChatContext } from "@/context/ChatContext";
import { useAutoScroll } from "@/hooks/useAutoScroll";
import { MessageBubble } from "./MessageBubble";
import { StarterPrompts } from "./StarterPrompts";
import { QuickReplyButtons } from "./QuickReplyButtons";

export function MessageList() {
  const { messages, isStreaming, statusText, sendMessage } = useChatContext();
  const { containerRef, handleScroll } = useAutoScroll([messages, statusText]);

  if (messages.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto">
        <StarterPrompts onSelect={sendMessage} />
      </div>
    );
  }

  const lastAssistant = [...messages]
    .reverse()
    .find((m) => m.role === "assistant");

  return (
    <div
      ref={containerRef}
      onScroll={handleScroll}
      className="flex-1 overflow-y-auto px-4 py-4 chat-scrollbar"
    >
      {messages.map((msg) => (
        <MessageBubble
          key={msg.id}
          message={msg}
          statusText={msg === lastAssistant && isStreaming ? statusText : null}
          onFollowUp={sendMessage}
        />
      ))}

      {lastAssistant &&
        !isStreaming &&
        lastAssistant.suggestions &&
        lastAssistant.suggestions.length > 0 && (
          <div className="flex justify-start mb-3">
            <div className="max-w-[85%] sm:max-w-[75%]">
              <QuickReplyButtons
                options={lastAssistant.suggestions}
                onSelect={sendMessage}
                disabled={isStreaming}
              />
            </div>
          </div>
        )}
    </div>
  );
}
