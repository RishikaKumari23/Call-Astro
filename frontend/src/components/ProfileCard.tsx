import React from 'react';
import { Calendar, Clock, MapPin, Globe, RotateCcw } from 'lucide-react';

interface ProfileCardProps {
  dob: string | null;
  birthTime: string | null;
  birthPlace: string | null;
  language: string;
  onReset: () => void;
  isResetting: boolean;
}

export const ProfileCard: React.FC<ProfileCardProps> = ({
  dob,
  birthTime,
  birthPlace,
  language,
  onReset,
  isResetting
}) => {
  return (
    <div className="w-full bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
      <div className="flex justify-between items-center mb-6">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-slate-400">
          Kundali Details
        </h3>
        <button
          onClick={onReset}
          disabled={isResetting}
          className="text-xs flex items-center gap-1.5 text-rose-600 hover:text-rose-700 bg-rose-50 hover:bg-rose-100 disabled:opacity-50 px-2.5 py-1.5 rounded-lg font-medium transition"
          title="Clear session data to start new reading"
        >
          <RotateCcw size={12} className={isResetting ? "animate-spin" : ""} />
          Reset Chat
        </button>
      </div>

      <div className="space-y-4">
        {/* Date of Birth */}
        <div className="flex items-start gap-3">
          <div className="p-2 bg-indigo-50 text-indigo-600 rounded-lg mt-0.5">
            <Calendar size={16} />
          </div>
          <div>
            <div className="text-xs text-slate-400 font-medium">Date of Birth</div>
            <div className={`text-sm font-medium mt-0.5 ${dob ? 'text-slate-800' : 'text-slate-400 italic'}`}>
              {dob || 'Pending...'}
            </div>
          </div>
        </div>

        {/* Birth Time */}
        <div className="flex items-start gap-3">
          <div className="p-2 bg-amber-50 text-amber-600 rounded-lg mt-0.5">
            <Clock size={16} />
          </div>
          <div>
            <div className="text-xs text-slate-400 font-medium">Time of Birth</div>
            <div className={`text-sm font-medium mt-0.5 ${birthTime ? 'text-slate-800' : 'text-slate-400 italic'}`}>
              {birthTime || 'Pending...'}
            </div>
          </div>
        </div>

        {/* Birth Place */}
        <div className="flex items-start gap-3">
          <div className="p-2 bg-emerald-50 text-emerald-600 rounded-lg mt-0.5">
            <MapPin size={16} />
          </div>
          <div>
            <div className="text-xs text-slate-400 font-medium">Place of Birth</div>
            <div className={`text-sm font-medium mt-0.5 ${birthPlace ? 'text-slate-800' : 'text-slate-400 italic'}`}>
              {birthPlace || 'Pending...'}
            </div>
          </div>
        </div>

        {/* Language */}
        <div className="flex items-start gap-3">
          <div className="p-2 bg-sky-50 text-sky-600 rounded-lg mt-0.5">
            <Globe size={16} />
          </div>
          <div>
            <div className="text-xs text-slate-400 font-medium">Detected Language</div>
            <div className="text-sm font-medium mt-0.5 text-slate-800 capitalize">
              {language}
            </div>
          </div>
        </div>
      </div>

      <div className="mt-6 pt-4 border-t border-slate-100">
        <p className="text-xs text-slate-400 leading-relaxed">
          ✨ Astrologer stores your birth details in memory. You don't have to provide them again in this session.
        </p>
      </div>
    </div>
  );
};
