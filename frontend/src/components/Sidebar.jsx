import React from 'react';
import { Plus, MessageSquare, MoreHorizontal, Sun, Moon } from 'lucide-react';

const mockHistory = [
  { id: 1, title: 'Operating Systems – Memory Mgmt', time: '2h ago', confidence: 74, dateGroup: 'Today' },
  { id: 2, title: 'Data Structures - Trees', time: '5h ago', confidence: 92, dateGroup: 'Today' },
  { id: 3, title: 'React Hooks Deep Dive', time: 'Yesterday', confidence: 45, dateGroup: 'Yesterday' },
  { id: 4, title: 'System Design Interview Prep', time: '3d ago', confidence: 60, dateGroup: 'Previous 7 Days' },
];

function ConfidenceBadge({ score }) {
  let color = 'bg-red-500/20 text-red-700 dark:text-red-400 border-red-500/30';
  if (score >= 70) color = 'bg-green-500/20 text-green-700 dark:text-green-400 border-green-500/30';
  else if (score >= 40) color = 'bg-amber-500/20 text-amber-700 dark:text-amber-400 border-amber-500/30';

  return (
    <span className={`text-[10px] px-2 py-0.5 rounded-full border ${color} inline-block mt-1`}>
      Conf: {score}%
    </span>
  );
}

function ChatHistoryCard({ chat, onSelect }) {
  let progressColor = 'bg-red-500';
  if (chat.confidence >= 70) progressColor = 'bg-green-500';
  else if (chat.confidence >= 40) progressColor = 'bg-amber-500';

  return (
    <div 
      onClick={() => onSelect(chat)}
      className="group p-3 mb-2 rounded-xl border border-transparent hover:border-gray-300 dark:hover:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800/50 cursor-pointer transition-all duration-200"
    >
      <div className="flex justify-between items-start mb-1">
        <h4 className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate pr-2 flex-1">{chat.title}</h4>
        <button className="text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity">
          <MoreHorizontal size={16} />
        </button>
      </div>
      <div className="flex justify-between items-center text-xs text-gray-500 mb-2">
        <span>{chat.time}</span>
        <ConfidenceBadge score={chat.confidence} />
      </div>
      <div className="w-full h-1 bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
        <div className={`h-full ${progressColor}`} style={{ width: `${chat.confidence}%` }}></div>
      </div>
    </div>
  );
}

export default function Sidebar({ onNewChat, onSelectChat, isDarkMode, toggleDarkMode }) {
  const groupedHistory = mockHistory.reduce((acc, chat) => {
    acc[chat.dateGroup] = acc[chat.dateGroup] || [];
    acc[chat.dateGroup].push(chat);
    return acc;
  }, {});

  return (
    <div className="flex flex-col h-full w-full p-4">
      <button 
        onClick={onNewChat}
        className="flex items-center justify-center gap-2 w-full bg-accent hover:bg-accent/90 text-white rounded-lg py-3 px-4 font-medium transition-colors shadow-lg shadow-accent/20 mb-6 flex-shrink-0"
      >
        <Plus size={18} />
        <span>New Chat</span>
      </button>

      <div className="flex-1 overflow-y-auto pr-1 -mr-1">
        {Object.entries(groupedHistory).map(([group, chats]) => (
          <div key={group} className="mb-6">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 px-2">{group}</h3>
            {chats.map(chat => (
              <ChatHistoryCard key={chat.id} chat={chat} onSelect={onSelectChat} />
            ))}
          </div>
        ))}
      </div>

      <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-800 flex-shrink-0">
        <button 
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
