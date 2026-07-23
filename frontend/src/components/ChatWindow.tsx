import React, { useEffect, useRef } from 'react';
import { User } from 'lucide-react';
import { SuggestionChips } from './SuggestionChips';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

interface ChatWindowProps {
  messages: Message[];
  isTyping: boolean;
  suggestions: string[];
  onSuggestionSelect: (text: string) => void;
}

export const ChatWindow: React.FC<ChatWindowProps> = ({ messages, isTyping, suggestions, onSuggestionSelect }) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  // Scroll to bottom whenever messages or typing state changes
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  return (
    <div className="flex-1 overflow-y-auto px-4 py-6 space-y-6">
      {/* Greeting message if no history */}
      {messages.length === 0 && (
        <div className="flex justify-start max-w-2xl mx-auto">
          <div className="flex gap-4">
            <div className="w-9 h-9 rounded-full bg-amber-500 flex items-center justify-center text-white text-base shadow-sm shrink-0">
              🔮
            </div>
            <div className="bg-white border border-slate-200 text-slate-800 rounded-2xl px-5 py-3.5 shadow-sm leading-relaxed">
              🙏 Namaste! Main aapki kya seva kar sakta hoon?
            </div>
          </div>
        </div>
      )}

      {/* Render messages */}
      <div className="max-w-2xl mx-auto space-y-6">
        {messages.map((msg, index) => {
          const isUser = msg.role === 'user';
          return (
            <div
              key={index}
              className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
            >
              <div className={`flex gap-3 max-w-[85%] ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
                {/* Avatar */}
                <div className={`w-9 h-9 rounded-full flex items-center justify-center text-sm shadow-sm shrink-0 ${
                  isUser 
                    ? 'bg-slate-200 text-slate-600' 
                    : 'bg-amber-500 text-white'
                }`}>
                  {isUser ? <User size={16} /> : '🔮'}
                </div>

                {/* Message Bubble */}
                <div>
                  <div className={`rounded-2xl px-5 py-3.5 shadow-sm leading-relaxed ${
                    isUser
                      ? 'bg-slate-900 text-white rounded-tr-none'
                      : 'bg-white border border-slate-200 text-slate-800 rounded-tl-none'
                  }`}>
                    <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
                  </div>
                  {msg.timestamp && (
                    <div className={`text-[10px] text-slate-400 mt-1 px-1 ${isUser ? 'text-right' : 'text-left'}`}>
                      {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  )}
                </div>
              </div>
            </div>
          );
        })}

        {/* Follow-up suggestion chips */}
        {!isTyping && suggestions.length > 0 && (
          <SuggestionChips
            suggestions={suggestions}
            onSelect={onSuggestionSelect}
            disabled={isTyping}
          />
        )}

        {/* Typing indicator */}
        {isTyping && (
          <div className="flex justify-start">
            <div className="flex gap-3">
              <div className="w-9 h-9 rounded-full bg-amber-500 flex items-center justify-center text-white text-sm shadow-sm shrink-0">
                🔮
              </div>
              <div className="bg-white border border-slate-200 rounded-2xl rounded-tl-none px-5 py-4 shadow-sm flex items-center gap-1">
                <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    </div>
  );
};
