"use client";

import { useReducer, useCallback, useRef } from "react";
import { useSSE } from "./useSSE";
import { useSession } from "./useSession";
import type {
  ChatState,
  ChatAction,
  Message,
  ContentBlock,
  ProductCardData,
  CompatibilityResultData,
  DiagnosisData,
} from "@/lib/types";
import { generateId } from "@/lib/utils";
import { API_PATHS } from "@/lib/constants";

export const initialState: ChatState = {
  messages: [],
  isStreaming: false,
  error: null,
  statusText: null,
};

export function chatReducer(state: ChatState, action: ChatAction): ChatState {
  switch (action.type) {
    case "ADD_USER_MESSAGE":
      return {
        ...state,
        messages: [...state.messages, action.message],
        isStreaming: true,
        error: null,
        statusText: null,
      };

    case "ADD_ASSISTANT_MESSAGE":
      return {
        ...state,
        messages: [...state.messages, action.message],
      };

    case "APPEND_TEXT_DELTA": {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (!last || last.role !== "assistant") return state;

      const content = [...last.content];
      const lastBlock = content[content.length - 1];

      if (lastBlock && lastBlock.type === "text") {
        content[content.length - 1] = {
          type: "text",
          text: lastBlock.text + action.text,
        };
      } else {
        content.push({ type: "text", text: action.text });
      }

      msgs[msgs.length - 1] = { ...last, content };
      return { ...state, messages: msgs, statusText: null };
    }

    case "ADD_CONTENT_BLOCK": {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (!last || last.role !== "assistant") return state;

      msgs[msgs.length - 1] = {
        ...last,
        content: [...last.content, action.block],
      };
      return { ...state, messages: msgs };
    }

    case "SET_STATUS":
      return { ...state, statusText: action.text };

    case "SET_SUGGESTIONS": {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (!last || last.role !== "assistant") return state;

      msgs[msgs.length - 1] = { ...last, suggestions: action.options };
      return { ...state, messages: msgs };
    }

    case "SET_ERROR":
      return { ...state, error: action.error, isStreaming: false, statusText: null };

    case "FINALIZE_STREAM": {
      const msgs = [...state.messages];
      const last = msgs[msgs.length - 1];
      if (last && last.role === "assistant") {
        msgs[msgs.length - 1] = { ...last, isStreaming: false };
      }
      return { ...state, messages: msgs, isStreaming: false, statusText: null };
    }

    case "CLEAR_MESSAGES":
      return { ...initialState };

    default:
      return state;
  }
}

export function useChat() {
  const [state, dispatch] = useReducer(chatReducer, initialState);
  const { send, abort } = useSSE();
  const { sessionId, resetSession } = useSession();
  const dispatchRef = useRef(dispatch);
  dispatchRef.current = dispatch;

  // Buffer card blocks during streaming so they only appear after text is done
  const pendingBlocksRef = useRef<ContentBlock[]>([]);

  const flushPendingBlocks = useCallback(() => {
    for (const block of pendingBlocksRef.current) {
      dispatchRef.current({ type: "ADD_CONTENT_BLOCK", block });
    }
    pendingBlocksRef.current = [];
  }, []);

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || !sessionId) return;

      pendingBlocksRef.current = [];

      const userMsg: Message = {
        id: generateId(),
        role: "user",
        content: [{ type: "text", text: text.trim() }],
        timestamp: Date.now(),
      };

      dispatch({ type: "ADD_USER_MESSAGE", message: userMsg });

      const assistantMsg: Message = {
        id: generateId(),
        role: "assistant",
        content: [],
        timestamp: Date.now(),
        isStreaming: true,
      };

      dispatch({ type: "ADD_ASSISTANT_MESSAGE", message: assistantMsg });

      try {
        await send(API_PATHS.chat, { message: text.trim(), session_id: sessionId }, {
          onTextDelta: (t) => dispatchRef.current({ type: "APPEND_TEXT_DELTA", text: t }),
          onProductCard: (data) =>
            pendingBlocksRef.current.push({
              type: "product_card",
              data: data as ProductCardData,
            }),
          onCompatibilityResult: (data) =>
            pendingBlocksRef.current.push({
              type: "compatibility_result",
              data: data as CompatibilityResultData,
            }),
          onDiagnosis: (data) =>
            pendingBlocksRef.current.push({
              type: "diagnosis",
              data: data as DiagnosisData,
            }),
          onStatus: (t) => dispatchRef.current({ type: "SET_STATUS", text: t }),
          onSuggestions: (opts) => dispatchRef.current({ type: "SET_SUGGESTIONS", options: opts }),
          onError: (e) => dispatchRef.current({ type: "SET_ERROR", error: e }),
          onDone: () => {
            flushPendingBlocks();
            dispatchRef.current({ type: "FINALIZE_STREAM" });
          },
        });
      } catch {
        flushPendingBlocks();
        dispatchRef.current({ type: "FINALIZE_STREAM" });
      }
    },
    [sessionId, send, flushPendingBlocks]
  );

  const stopStreaming = useCallback(() => {
    abort();
    flushPendingBlocks();
    dispatch({ type: "FINALIZE_STREAM" });
  }, [abort, flushPendingBlocks]);

  const clearMessages = useCallback(() => {
    abort();
    pendingBlocksRef.current = [];
    dispatch({ type: "CLEAR_MESSAGES" });
    resetSession();
  }, [abort, resetSession]);

  return {
    messages: state.messages,
    isStreaming: state.isStreaming,
    error: state.error,
    statusText: state.statusText,
    sendMessage,
    stopStreaming,
    clearMessages,
  };
}
