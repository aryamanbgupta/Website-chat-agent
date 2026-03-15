"use client";

import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message } from "@/lib/types";
import { ProductCard } from "@/components/cards/ProductCard";
import { CompatibilityBadge } from "@/components/cards/CompatibilityBadge";
import { DiagnosisCard } from "@/components/cards/DiagnosisCard";
import { StreamingIndicator } from "./StreamingIndicator";

interface MessageBubbleProps {
  message: Message;
  statusText?: string | null;
  onFollowUp?: (question: string) => void;
}

export function MessageBubble({
  message,
  statusText,
  onFollowUp,
}: MessageBubbleProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={`flex ${isUser ? "justify-end" : "justify-start"} mb-3 animate-fade-in`}
    >
      <div
        className={`max-w-[85%] sm:max-w-[75%] ${
          isUser
            ? "bg-primary-teal text-white rounded-[2px] px-4 py-2.5"
            : "bg-white"
        }`}
      >
        {message.content.map((block, i) => {
          switch (block.type) {
            case "text":
              return isUser ? (
                <p key={i} className="text-sm whitespace-pre-wrap">
                  {block.text}
                </p>
              ) : (
                <div
                  key={i}
                  className="text-sm text-body-text chat-markdown px-1"
                >
                  <Markdown remarkPlugins={[remarkGfm]}>{block.text}</Markdown>
                </div>
              );
            case "product_card":
              return <ProductCard key={i} data={block.data} />;
            case "compatibility_result":
              return <CompatibilityBadge key={i} data={block.data} />;
            case "diagnosis":
              return (
                <DiagnosisCard
                  key={i}
                  data={block.data}
                  onFollowUp={onFollowUp}
                />
              );
            case "status":
              return null;
            default:
              return null;
          }
        })}

        {message.isStreaming &&
          message.content.length === 0 && (
            <StreamingIndicator statusText={statusText} />
          )}

        {message.isStreaming &&
          message.content.length > 0 && statusText && (
            <StreamingIndicator statusText={statusText} />
          )}
      </div>
    </div>
  );
}
