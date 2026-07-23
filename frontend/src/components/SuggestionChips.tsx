import React from 'react';

interface SuggestionChipsProps {
  suggestions: string[];
  onSelect: (text: string) => void;
  disabled: boolean;
}

export const SuggestionChips: React.FC<SuggestionChipsProps> = ({ suggestions, onSelect, disabled }) => {
  if (!suggestions || suggestions.length === 0) return null;

  return (
    <div className="flex flex-wrap gap-2 mt-3 ml-12">
      {suggestions.map((suggestion, index) => (
        <button
          key={index}
          onClick={() => onSelect(suggestion)}
          disabled={disabled}
          className={`
            px-4 py-2 rounded-full text-sm font-medium
            border border-amber-200 bg-amber-50 text-amber-800
            transition-all duration-200 ease-in-out
            hover:bg-amber-100 hover:border-amber-300 hover:shadow-sm hover:scale-[1.02]
            active:scale-95
            disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:scale-100
          `}
        >
          {suggestion}
        </button>
      ))}
    </div>
  );
};
