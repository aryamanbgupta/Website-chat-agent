"use client";

import { useState, useEffect, useCallback } from "react";
import { generateId } from "@/lib/utils";

const SESSION_KEY = "partselect_session_id";

export function useSession() {
  const [sessionId, setSessionId] = useState<string>("");

  useEffect(() => {
    const stored = localStorage.getItem(SESSION_KEY);
    if (stored) {
      setSessionId(stored);
    } else {
      const newId = generateId();
      localStorage.setItem(SESSION_KEY, newId);
      setSessionId(newId);
    }
  }, []);

  const resetSession = useCallback(() => {
    const newId = generateId();
    localStorage.setItem(SESSION_KEY, newId);
    setSessionId(newId);
  }, []);

  return { sessionId, resetSession };
}
