import React, { useState } from 'react';
import { FAQ_CATEGORIES } from '../data/faqs';

interface FaqStarterProps {
  onSelect: (question: string) => void;
  disabled: boolean;
}

export const FaqStarter: React.FC<FaqStarterProps> = ({ onSelect, disabled }) => {
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const activeCategory = FAQ_CATEGORIES.find(c => c.label === selectedCategory);

  return (
    <div className="px-4 py-4 border-t border-slate-100">
      {/* Title */}
      <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
        ✨ Popular Questions — Pick a topic
      </p>

      {/* Category Chips Row */}
      <div className="flex flex-wrap gap-2 mb-3">
        {FAQ_CATEGORIES.map((cat) => (
          <button
            key={cat.label}
            onClick={() => setSelectedCategory(
              selectedCategory === cat.label ? null : cat.label
            )}
            disabled={disabled}
            className={`
              px-3 py-1.5 rounded-full text-xs font-semibold
              border transition-all duration-200 ease-in-out
              ${selectedCategory === cat.label
                ? `${cat.color} ${cat.bgColor} shadow-sm scale-105`
                : 'border-slate-200 text-slate-500 bg-white hover:border-slate-300 hover:bg-slate-50'
              }
              disabled:opacity-40 disabled:cursor-not-allowed
            `}
          >
            {cat.emoji} {cat.label}
          </button>
        ))}
      </div>

      {/* Questions for selected category */}
      {activeCategory && (
        <div className="flex flex-wrap gap-2 mt-2 animate-fade-in">
          {activeCategory.questions.map((question, index) => (
            <button
              key={index}
              onClick={() => {
                onSelect(question);
                setSelectedCategory(null);
              }}
              disabled={disabled}
              className={`
                px-3 py-1.5 rounded-full text-xs font-medium
                border ${activeCategory.color} ${activeCategory.bgColor}
                transition-all duration-150 ease-in-out
                hover:shadow-sm hover:scale-[1.02] active:scale-95
                disabled:opacity-40 disabled:cursor-not-allowed
              `}
            >
              {question}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};
