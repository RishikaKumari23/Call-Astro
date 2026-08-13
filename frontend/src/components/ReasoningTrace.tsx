import { useEffect, useState } from 'react';
import { API_BASE } from '../api';
import { Sparkles, ChevronDown, ChevronUp } from 'lucide-react';

interface TraceStep {
  step: number;
  title: string;
  detail: string;
}

interface ReasoningTraceProps {
  sessionId: string;
  refreshKey: number; // pass messages.length so it refetches after each reply
  language: string;
}

const STRINGS: Record<string, { title: string; empty: string; collapse: string; expand: string }> = {
  English: {
    title: 'How I Reached This',
    empty: 'Ask a question to see the reasoning behind the reading.',
    collapse: 'Collapse',
    expand: 'Expand',
  },
  Hindi: {
    title: 'यह निष्कर्ष कैसे निकला',
    empty: 'तर्क देखने के लिए एक प्रश्न पूछें।',
    collapse: 'छोटा करें',
    expand: 'बड़ा करें',
  },
  Hinglish: {
    title: 'Yeh Reading Kaise Bani',
    empty: 'Reasoning dekhne ke liye ek sawaal poochein.',
    collapse: 'Chota karein',
    expand: 'Bada karein',
  },
};

export default function ReasoningTrace({ sessionId, refreshKey, language }: ReasoningTraceProps) {
  const [steps, setSteps] = useState<TraceStep[]>([]);
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(true);
  const t = STRINGS[language] || STRINGS.Hinglish;

  useEffect(() => {
    if (!sessionId) return;
    setLoading(true);
    fetch(`${API_BASE}/session/${sessionId}/reasoning-trace`)
      .then((res) => res.json())
      .then((data) => setSteps(data.available ? data.steps : []))
      .catch(() => setSteps([]))
      .finally(() => setLoading(false));
  }, [sessionId, refreshKey]);

  return (
    <div className="bg-white border border-slate-200 rounded-2xl shadow-sm overflow-hidden">
      <button
        onClick={() => setExpanded((e) => !e)}
        className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-50 transition"
      >
        <div className="flex items-center gap-2">
          <Sparkles size={14} className="text-amber-500" />
          <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
            {t.title}
          </h3>
        </div>
        {expanded ? <ChevronUp size={14} className="text-slate-400" /> : <ChevronDown size={14} className="text-slate-400" />}
      </button>

      {expanded && (
        <div className="px-5 pb-5">
          {loading ? (
            <div className="space-y-2 animate-pulse">
              <div className="h-3 bg-slate-100 rounded w-3/4" />
              <div className="h-3 bg-slate-100 rounded w-1/2" />
              <div className="h-3 bg-slate-100 rounded w-2/3" />
            </div>
          ) : steps.length === 0 ? (
            <p className="text-xs text-slate-400 italic">{t.empty}</p>
          ) : (
            <ol className="space-y-3">
              {steps.map((s) => (
                <li key={s.step} className="flex gap-3">
                  <div className="shrink-0 w-5 h-5 rounded-full bg-slate-900 text-white text-[10px] font-semibold flex items-center justify-center mt-0.5">
                    {s.step}
                  </div>
                  <div className="min-w-0">
                    <div className="text-xs font-semibold text-slate-700">{s.title}</div>
                    <div className="text-xs text-slate-500 mt-0.5 leading-relaxed">{s.detail}</div>
                  </div>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </div>
  );
}