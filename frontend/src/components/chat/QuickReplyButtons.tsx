"use client";

interface QuickReplyButtonsProps {
  options: string[];
  onSelect: (option: string) => void;
  disabled?: boolean;
}

export function QuickReplyButtons({
  options,
  onSelect,
  disabled,
}: QuickReplyButtonsProps) {
  if (!options.length) return null;

  return (
    <div className="flex flex-wrap gap-1.5 mt-2 animate-fade-in">
      {options.map((option) => (
        <button
          key={option}
          onClick={() => onSelect(option)}
          disabled={disabled}
          className="text-xs px-3 py-1.5 border border-primary-teal text-primary-teal hover:bg-primary-teal hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {option}
        </button>
      ))}
    </div>
  );
}
