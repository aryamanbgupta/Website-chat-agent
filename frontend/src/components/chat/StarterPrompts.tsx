"use client";

import { Snowflake, Search, CheckCircle, Droplets } from "lucide-react";
import { STARTER_PROMPTS } from "@/lib/constants";

const iconMap = {
  snowflake: Snowflake,
  search: Search,
  "check-circle": CheckCircle,
  droplets: Droplets,
} as const;

interface StarterPromptsProps {
  onSelect: (message: string) => void;
}

export function StarterPrompts({ onSelect }: StarterPromptsProps) {
  return (
    <div className="flex flex-col items-center justify-center h-full px-4 py-8">
      <div className="text-center mb-8">
        <div className="w-16 h-16 bg-teal-light rounded-full flex items-center justify-center mx-auto mb-4">
          <Search size={28} className="text-primary-teal" />
        </div>
        <h2 className="text-xl font-bold text-body-text mb-2">
          PartSelect Assistant
        </h2>
        <p className="text-sm text-muted-text max-w-md">
          I can help you find parts, check compatibility, diagnose appliance
          issues, and provide installation guidance for refrigerators and
          dishwashers.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
        {STARTER_PROMPTS.map((prompt) => {
          const Icon = iconMap[prompt.icon];
          return (
            <button
              key={prompt.label}
              onClick={() => onSelect(prompt.message)}
              className="flex items-center gap-3 text-left px-4 py-3 border border-border bg-white hover:bg-teal-light hover:border-primary-teal transition-colors group"
            >
              <Icon
                size={18}
                className="text-muted-text group-hover:text-primary-teal flex-shrink-0 transition-colors"
              />
              <div>
                <p className="text-sm font-medium text-body-text">
                  {prompt.label}
                </p>
                <p className="text-xs text-muted-text mt-0.5 line-clamp-1">
                  {prompt.message}
                </p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
