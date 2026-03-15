"use client";

import { ChatProvider } from "@/context/ChatContext";
import { ChatContainer } from "@/components/chat/ChatContainer";

export default function Home() {
  return (
    <ChatProvider>
      <ChatContainer />
    </ChatProvider>
  );
}
