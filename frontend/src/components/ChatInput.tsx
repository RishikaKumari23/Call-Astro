import React, { useState, useRef, useEffect } from 'react';
import { Send } from 'lucide-react';

interface ChatInputProps {
  onSendMessage: (message: string) => void;
  disabled: boolean;
}

export const ChatInput: React.FC<ChatInputProps> = ({ onSendMessage, disabled }) => {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || disabled) return;
    onSendMessage(input.trim());
    setInput('');
  };

  // Handle Enter (send) and Shift+Enter (new line)
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  // Auto-resize input height based on text lines
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [input]);

  return (
    <form onSubmit={handleSubmit} className="border-t border-slate-200 bg-white px-4 py-4 md:py-6">
      <div className="max-w-2xl mx-auto flex items-end gap-3 bg-slate-50 border border-slate-200 rounded-2xl p-2 focus-within:border-slate-400 focus-within:ring-1 focus-within:ring-slate-400 transition duration-150">
        <textarea
          ref={textareaRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about marriage, career, finance, planets..."
          rows={1}
          disabled={disabled}
          className="flex-1 resize-none bg-transparent outline-none max-h-32 text-sm py-2 px-3 text-slate-800 placeholder-slate-400 disabled:opacity-50"
        />
        <button
          type="submit"
          disabled={!input.trim() || disabled}
          className="p-2.5 bg-slate-900 hover:bg-slate-800 disabled:bg-slate-100 text-white disabled:text-slate-400 rounded-xl transition shrink-0 shadow-sm"
        >
          <Send size={16} />
        </button>
      </div>
      <p className="max-w-2xl mx-auto text-center text-[10px] text-slate-400 mt-2">
        Vedic astrology readings are context-guided. Provide accurate DOB, Time, and Place for correct charts.
      </p>
    </form>
  );
};
