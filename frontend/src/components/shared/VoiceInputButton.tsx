"use client";

import { Mic, MicOff } from "lucide-react";
import { cn } from "@/lib/utils";

interface VoiceInputButtonProps {
  isListening: boolean;
  isSupported: boolean;
  onToggle: () => void;
}

export function VoiceInputButton({
  isListening,
  isSupported,
  onToggle,
}: VoiceInputButtonProps) {
  if (!isSupported) return null;

  return (
    <button
      type="button"
      onClick={onToggle}
      className={cn(
        "flex items-center justify-center w-9 h-9 rounded-full transition-colors",
        isListening
          ? "bg-error-red text-white mic-pulse"
          : "text-muted-text hover:text-body-text hover:bg-bg-light"
      )}
      aria-label={isListening ? "Stop listening" : "Start voice input"}
    >
      {isListening ? <MicOff size={18} /> : <Mic size={18} />}
    </button>
  );
}
