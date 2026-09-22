import React, { useEffect, useState, useCallback } from 'react';
import { Plus, MessageSquare, Sun, Moon, MoreHorizontal, BarChart2 } from 'lucide-react';
import { getHistory } from '../api';

function ConfidenceBadge({ score }) {
  const pct = Math.round((score ?? 1) * 100);
  let color = 'bg-red-500/20 text-red-700 dark:text-red-400 border-red-500/30';
  if (pct >= 70) color = 'bg-emerald-500/20 text-emerald-700 dark:text-emerald-400 border-emerald-500/30';
  else if (pct >= 40) color = 'bg-amber-500/20 text-amber-700 dark:text-amber-400 border-amber-500/30';
  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-full border ${color} inline-block`}>
      {pct}%
    </span>
  );
}

function SessionCard({ session, isActive, onSelect }) {
  const confidence = session.confidence;
  let barColor = 'bg-red-500';
  if (confidence >= 0.7) barColor = 'bg-emerald-500';
  else if (confidence >= 0.4) barColor = 'bg-amber-500';

  return (
    <div
      id={`session-${session.id}`}
      onClick={() => onSelect(session)}
      className={`group p-3 mb-2 rounded-xl border cursor-pointer transition-all duration-200 ${
        isActive
          ? 'border-accent/40 bg-accent/5'
          : 'border-transparent hover:border-gray-300 dark:hover:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800/50'
      }`}
    >
      <div className="flex justify-between items-start mb-1">
        <h4 className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate pr-2 flex-1 leading-snug">
          {session.title}
        </h4>
        <ConfidenceBadge score={confidence} />
      </div>
      <div className="text-xs text-gray-500 mb-2">{session.time}</div>
      <div className="w-full h-1 bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
        <div
          className={`h-full ${barColor} transition-all duration-500`}
          style={{ width: `${Math.round(confidence * 100)}%` }}
        />
      </div>
    </div>
  );
}

export default function Sidebar({
  sessionId,
  onNewChat,
  isDarkMode,
  toggleDarkMode,
  onOpenMemory,
  refreshTrigger,
}) {
  const [sessions, setSessions] = useState([]);
  const [activeSessionId, setActiveSessionId] = useState(sessionId);

  const loadHistory = useCallback(async () => {
    try {
      const data = await getHistory(sessionId, 200);
      // Group messages into conversation pairs and compute per-session confidence
      const pairs = [];
      const msgs = data.messages || [];
      for (let i = 0; i < msgs.length; i++) {
        if (msgs[i].role === 'user') {
          const ai = msgs[i + 1];
          const meta = ai?.metadata || {};
          pairs.push({
            id: msgs[i].id,
            title: msgs[i].content.slice(0, 60) + (msgs[i].content.length > 60 ? '…' : ''),
            time: new Date(msgs[i].timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
            confidence: typeof meta.confidence_score === 'number' ? meta.confidence_score : 0.75,
          });
        }
      }
      setSessions(pairs.reverse()); // newest first
    } catch {
      // API may not be reachable; leave sessions empty
    }
  }, [sessionId, refreshTrigger]);

  useEffect(() => { loadHistory(); }, [loadHistory]);
  useEffect(() => { setActiveSessionId(sessionId); }, [sessionId]);

  return (
    <div className="flex flex-col h-full w-full p-4">
      {/* New Chat */}
      <button
        id="new-chat-btn"
        onClick={onNewChat}
        className="flex items-center justify-center gap-2 w-full bg-accent hover:bg-accent/90 text-white rounded-lg py-3 px-4 font-medium transition-colors shadow-lg shadow-accent/20 mb-6 flex-shrink-0"
      >
        <Plus size={18} />
        <span>New Chat</span>
      </button>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto pr-1 -mr-1">
        {sessions.length === 0 ? (
          <div className="text-center text-xs text-gray-500 mt-8 px-4 leading-relaxed">
            <MessageSquare size={24} className="mx-auto mb-3 opacity-30" />
            No conversations yet.<br />Ask a question to get started.
          </div>
        ) : (
          <>
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 px-2">
              This Session
            </h3>
            {sessions.map(s => (
              <SessionCard
                key={s.id}
                session={s}
                isActive={false}
                onSelect={() => {}}
              />
            ))}
          </>
        )}
      </div>

      {/* Footer */}
      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-800 flex-shrink-0 space-y-1">
        <button
          id="memory-btn"
          onClick={onOpenMemory}
          className="flex items-center gap-3 w-full p-2 rounded-lg text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
        >
          <BarChart2 size={18} />
          <span className="text-sm font-medium">Learning Progress</span>
        </button>
        <button
          id="dark-mode-btn"
          onClick={toggleDarkMode}
          className="flex items-center gap-3 w-full p-2 rounded-lg text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
        >
          {isDarkMode ? <Sun size={18} /> : <Moon size={18} />}
          <span className="text-sm font-medium">{isDarkMode ? 'Light Mode' : 'Dark Mode'}</span>
        </button>
      </div>
    </div>
  );
}
