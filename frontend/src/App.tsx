import React, { useState, useEffect } from 'react';
import { ChatWindow } from './components/ChatWindow';
import { ChatInput } from './components/ChatInput';
import { ProfileCard } from './components/ProfileCard';
import { FaqStarter } from './components/FaqStarter';
import { Sparkles, Database, CheckCircle } from 'lucide-react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

interface IngestStatus {
  indexing_completed: boolean;
  total_chunks: number;
  loading: boolean;
}

const API_BASE = '/api'; // Configured with Vite proxy

function App() {
  const [sessionId, setSessionId] = useState<string>('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [dob, setDob] = useState<string | null>(null);
  const [birthTime, setBirthTime] = useState<string | null>(null);
  const [birthPlace, setBirthPlace] = useState<string | null>(null);
  const [language, setLanguage] = useState<string>('Hinglish');
  
  const [isTyping, setIsTyping] = useState<boolean>(false);
  const [isResetting, setIsResetting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [suggestions, setSuggestions] = useState<string[]>([]);

  const [ingestStatus, setIngestStatus] = useState<IngestStatus>({
    indexing_completed: false,
    total_chunks: 0,
    loading: true
  });

  // 1. Initialise session on load
  useEffect(() => {
    let sid = localStorage.getItem('call-astro_session_id');
    if (!sid) {
      sid = 'session_' + Math.random().toString(36).substring(2, 15);
      localStorage.setItem('call-astro_session_id', sid);
    }
    setSessionId(sid);
  }, []);

  // 2. Fetch session data, history and vector index status once session ID is set
  useEffect(() => {
    if (!sessionId) return;
    
    const fetchSessionData = async () => {
      try {
        const profileRes = await fetch(`${API_BASE}/session/${sessionId}`);
        if (profileRes.ok) {
          const profile = await profileRes.json();
          setDob(profile.dob);
          setBirthTime(profile.birth_time);
          setBirthPlace(profile.birth_place);
          setLanguage(profile.language);
        }

        const historyRes = await fetch(`${API_BASE}/chat/history/${sessionId}`);
        if (historyRes.ok) {
          const history = await historyRes.json();
          setMessages(history.messages);
        }
      } catch (err) {
        console.error("Error fetching session data:", err);
        setError("Could not connect to the backend server. Please verify it is running.");
      }
    };

    fetchSessionData();
    checkIngestStatus();
  }, [sessionId]);

  const checkIngestStatus = async () => {
    try {
      const res = await fetch(`${API_BASE}/ingest/status`);
      if (res.ok) {
        const data = await res.json();
        setIngestStatus({
          indexing_completed: data.indexing_completed,
          total_chunks: data.total_chunks,
          loading: false
        });
      }
    } catch (err) {
      console.error("Error checking ingest status:", err);
      setIngestStatus(prev => ({ ...prev, loading: false }));
    }
  };

  // 3. Handle sending new chat message
  const handleSendMessage = async (text: string) => {
    // Optimistic UI update: append user message immediately
    const userMsg: Message = { role: 'user', content: text, timestamp: new Date().toISOString() };
    setMessages(prev => [...prev, userMsg]);
    setIsTyping(true);
    setError(null);
    setSuggestions([]);

    try {
      const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: text })
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Server error");
      }

      const data = await response.json();
      
      // Append bot response
      const botMsg: Message = { 
        role: 'assistant', 
        content: data.message, 
        timestamp: new Date().toISOString() 
      };
      setMessages(prev => [...prev, botMsg]);
      
      // Update extracted profile values
      setDob(data.dob);
      setBirthTime(data.birth_time);
      setBirthPlace(data.birth_place);
      setLanguage(data.language);
      setSuggestions(data.suggestions || []);

    } catch (err: any) {
      console.error("Failed to send message:", err);
      setError(err.message || "Something went wrong. Is Ollama running?");
    } finally {
      setIsTyping(false);
    }
  };

  // 4. Reset the current conversation session
  const handleResetSession = async () => {
    if (!sessionId) return;
    setIsResetting(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/session/${sessionId}`, { method: 'DELETE' });
      if (res.ok) {
        // Create new session ID
        const newSid = 'session_' + Math.random().toString(36).substring(2, 15);
        localStorage.setItem('astrotalk_session_id', newSid);
        setSessionId(newSid);
        
        // Reset states
        setMessages([]);
        setDob(null);
        setBirthTime(null);
        setBirthPlace(null);
        setLanguage('Hinglish');
      }
    } catch (err) {
      console.error("Reset failed:", err);
      setError("Failed to reset session data.");
    } finally {
      setIsResetting(false);
    }
  };



  return (
    <div className="flex flex-col h-full bg-slate-50">
      {/* Indexing Status Banner - shown when indexing is in progress or not completed */}
      {!ingestStatus.loading && !ingestStatus.indexing_completed && (
        <div className="bg-blue-50 border-b border-blue-200 px-4 py-2 text-sm text-blue-700 flex items-center gap-2">
          <Database size={16} className="text-blue-600 shrink-0 animate-pulse" />
          <span>
            <strong>Knowledge base indexing...</strong> Automatic indexing completed on server startup. Check server logs for details.
          </span>
        </div>
      )}

      {/* Main Navbar */}
      <header className="bg-white border-b border-slate-200 px-6 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="p-2 bg-amber-500 text-white rounded-xl shadow-sm">
            <Sparkles size={20} />
          </div>
          <div>
            <h1 className="text-lg font-bold text-slate-800 leading-none">AstroTalk</h1>
            <p className="text-[10px] text-slate-400 font-medium mt-0.5">Vedic RAG Assistant</p>
          </div>
        </div>

        {/* Index Status Badge - Display only, no manual re-indexing */}
        <div className="hidden sm:flex items-center gap-2">
          {ingestStatus.indexing_completed ? (
            <div className="flex items-center gap-1 text-emerald-600 bg-emerald-50 px-2.5 py-1 rounded-full text-xs font-medium border border-emerald-100">
              <CheckCircle size={12} />
              <span>RAG Active: {ingestStatus.total_chunks} Chunks</span>
            </div>
          ) : (
            <div className="flex items-center gap-1 text-slate-500 bg-slate-100 px-2.5 py-1 rounded-full text-xs font-medium border border-slate-200">
              <Database size={12} />
              <span>RAG: Initializing</span>
            </div>
          )}
        </div>
      </header>

      {/* Error Alert Display */}
      {error && (
        <div className="bg-rose-50 border-b border-rose-200 px-6 py-3 text-sm text-rose-700 flex items-center justify-between">
          <span>{error}</span>
          <button onClick={() => setError(null)} className="text-rose-400 hover:text-rose-600 font-semibold text-xs ml-4">
            Dismiss
          </button>
        </div>
      )}

      {/* Main Content Area */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Side: Chat Conversation */}
        <main className="flex-1 flex flex-col min-w-0 bg-slate-50">
          <ChatWindow messages={messages} isTyping={isTyping} suggestions={suggestions} onSuggestionSelect={handleSendMessage} />
          {/* Show FAQ starter when profile is incomplete and no LLM suggestions exist */}
          {(!dob || !birthTime || !birthPlace) && suggestions.length === 0 && (
            <FaqStarter onSelect={handleSendMessage} disabled={isTyping} />
          )}
          <ChatInput onSendMessage={handleSendMessage} disabled={isTyping} />
        </main>

        {/* Right Side: Profile Dashboard (Hidden on Mobile) */}
        <aside className="hidden md:block w-80 border-l border-slate-200 bg-slate-50 p-6 overflow-y-auto shrink-0">
          <ProfileCard
            dob={dob}
            birthTime={birthTime}
            birthPlace={birthPlace}
            language={language}
            onReset={handleResetSession}
            isResetting={isResetting}
          />
        </aside>
      </div>
    </div>
  );
}

export default App;
