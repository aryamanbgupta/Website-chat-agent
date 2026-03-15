"use client";

interface StreamingIndicatorProps {
  statusText?: string | null;
}

export function StreamingIndicator({ statusText }: StreamingIndicatorProps) {
  return (
    <div className="flex items-center gap-2 py-1">
      <div className="flex items-center gap-1">
        <span className="w-1.5 h-1.5 bg-primary-teal rounded-full bounce-dot-1" />
        <span className="w-1.5 h-1.5 bg-primary-teal rounded-full bounce-dot-2" />
        <span className="w-1.5 h-1.5 bg-primary-teal rounded-full bounce-dot-3" />
      </div>
      {statusText && (
        <span className="text-xs text-muted-text italic">{statusText}</span>
      )}
    </div>
  );
}
