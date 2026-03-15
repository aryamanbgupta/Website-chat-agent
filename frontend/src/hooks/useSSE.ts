"use client";

import { useRef, useCallback } from "react";
import { fetchEventSource } from "@microsoft/fetch-event-source";

export interface SSEHandlers {
  onTextDelta: (text: string) => void;
  onProductCard: (data: unknown) => void;
  onCompatibilityResult: (data: unknown) => void;
  onDiagnosis: (data: unknown) => void;
  onStatus: (text: string) => void;
  onSuggestions: (options: string[]) => void;
  onError: (error: string) => void;
  onDone: () => void;
}

export function useSSE() {
  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(
    async (
      url: string,
      body: { message: string; session_id: string },
      handlers: SSEHandlers
    ) => {
      abortRef.current?.abort();
      const ctrl = new AbortController();
      abortRef.current = ctrl;

      await fetchEventSource(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
        signal: ctrl.signal,
        openWhenHidden: true,

        onmessage(ev) {
          const { event, data } = ev;
          switch (event) {
            case "text_delta":
              handlers.onTextDelta(data);
              break;
            case "product_card":
              try { handlers.onProductCard(JSON.parse(data)); } catch { /* skip malformed */ }
              break;
            case "compatibility_result":
              try { handlers.onCompatibilityResult(JSON.parse(data)); } catch { /* skip */ }
              break;
            case "diagnosis":
              try { handlers.onDiagnosis(JSON.parse(data)); } catch { /* skip */ }
              break;
            case "status":
              handlers.onStatus(data);
              break;
            case "suggestions":
              try {
                const parsed = JSON.parse(data);
                handlers.onSuggestions(parsed.options || parsed);
              } catch { /* skip */ }
              break;
            case "error":
              handlers.onError(data);
              break;
            case "done":
              handlers.onDone();
              break;
          }
        },

        onclose() {
          handlers.onDone();
        },

        onerror(err) {
          if (ctrl.signal.aborted) return;
          handlers.onError(
            err instanceof Error ? err.message : "Connection error"
          );
          throw err; // stop retrying
        },
      });
    },
    []
  );

  const abort = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
  }, []);

  return { send, abort };
}
