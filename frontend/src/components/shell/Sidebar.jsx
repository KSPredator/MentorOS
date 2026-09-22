import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  MessageSquareText,
  LayoutDashboard,
  FolderOpen,
  Settings,
  Plus,
  Trash2,
  PanelLeftClose,
  PanelLeft,
  ChevronDown,
  Sun,
  Moon,
  Radio,
} from 'lucide-react';
import { useChat } from '../../stores/chat';
import { useUI } from '../../stores/ui';
import { useStatus } from '../../stores/status';
import { useFiles } from '../../stores/files';
import NavPill from '../ui/NavPill';
import Logo from '../ui/Logo';
import { dateGroup, relativeTime } from '../../lib/format';
import { toast } from 'sonner';

const NAV = [
  { to: '/', icon: MessageSquareText, label: 'Chat' },
  { to: '/podcast', icon: Radio, label: 'Podcast Studio' },
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dashboard' },
  { to: '/documents', icon: FolderOpen, label: 'Documents' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

export default function Sidebar() {
  const navigate = useNavigate();
  const location = useLocation();
  const sessions = useChat((s) => s.sessions);
  const activeId = useChat((s) => s.activeId);
  const newChat = useChat((s) => s.newChat);
  const setActive = useChat((s) => s.setActive);
  const deleteSession = useChat((s) => s.deleteSession);
  const filePanelOpen = useUI((s) => s.filePanelOpen);
  const toggleFilePanel = useUI((s) => s.toggleFilePanel);
  const dark = useUI((s) => s.dark);
  const toggleDark = useUI((s) => s.toggleDark);
  const confirm = useUI((s) => s.confirm);
  const fileCount = useFiles((s) => s.files.length);
  const ollama = useStatus((s) => s.ollama_available);
  const [historyOpen, setHistoryOpen] = useState(true);

  const grouped = groupSessions(sessions);

  const onNew = () => {
    newChat();
    navigate('/');
  };

  const onOpen = (id) => {
    navigate('/');
    setActive(id);
  };

  const onDelete = (id, title) => {
    confirm({
      title: 'Delete chat',
      message: `Delete "${title}" and all of its messages? This cannot be undone.`,
      confirmLabel: 'Delete',
      onConfirm: async () => {
        try {
          await deleteSession(id);
          toast.success('Chat deleted');
        } catch {
          toast.error('Failed to delete chat');
        }
      },
    });
  };

  return (
    <aside
      className="w-64 h-full flex flex-col border-r border-border/80 bg-panel/80 backdrop-blur-xl flex-shrink-0 z-10"
      aria-label="Sidebar"
    >
      {/* Brand / header */}
      <div className="flex items-center justify-between h-14 px-3.5 border-b border-border/80">
        <Logo size="md" />
        <div className="flex items-center gap-1">
          <button
            onClick={toggleDark}
            aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
            className="p-1.5 rounded-lg text-textMuted hover:text-textMain hover:bg-panelHover transition-colors cursor-pointer"
          >
            {dark ? <Sun size={15} className="text-amber-400" /> : <Moon size={15} className="text-sky-500" />}
          </button>
          <button
            onClick={toggleFilePanel}
            aria-label={filePanelOpen ? 'Hide file panel' : 'Show file panel'}
            className="p-1.5 rounded-lg text-textMuted hover:text-textMain hover:bg-panelHover transition-colors cursor-pointer"
          >
            {filePanelOpen ? <PanelLeftClose size={15} /> : <PanelLeft size={15} />}
          </button>
        </div>
      </div>

      {/* New chat */}
      <div className="px-3 pt-3">
        <button
          onClick={onNew}
          className="w-full flex items-center justify-center gap-2 text-sm font-semibold px-3 py-2.5 rounded-xl
            bg-accent text-white hover:bg-accentDim transition-all duration-150 shadow-md shadow-accent/20 hover:shadow-accent/30 cursor-pointer"
        >
          <Plus size={15} />
          <span>New session</span>
        </button>
      </div>

      {/* Nav */}
      <nav className="px-3 pt-3 space-y-0.5" aria-label="Primary">
        {NAV.map((item) => (
          <NavPill
            key={item.to}
            icon={item.icon}
            label={item.label}
            active={location.pathname === item.to}
            onClick={() => navigate(item.to)}
            badge={item.to === '/documents' ? fileCount : undefined}
          />
        ))}
      </nav>

      {/* History */}
      <div className="mt-3.5 flex-1 overflow-y-auto px-3 pb-3">
        <button
          onClick={() => setHistoryOpen((o) => !o)}
          className="flex items-center gap-1.5 px-2 py-1.5 w-full text-[10.5px] font-bold uppercase tracking-wider text-textFaint hover:text-textMuted transition-colors cursor-pointer"
          aria-expanded={historyOpen}
        >
          <ChevronDown
            size={12}
            className={`transition-transform duration-150 ${historyOpen ? '' : '-rotate-90'}`}
          />
          <span>History</span>
        </button>

        <AnimatePresence initial={false}>
          {historyOpen && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="overflow-hidden"
            >
              {sessions.length === 0 ? (
                <p className="text-xs text-textFaint px-2 py-3 leading-relaxed">
                  No conversations yet. Ask your notes a question to begin.
                </p>
              ) : (
                <div className="space-y-3 pt-1">
                  {grouped.map(([label, items]) => (
                    <div key={label}>
                      <div className="text-[10px] font-semibold uppercase tracking-wider text-textFaint px-2 mb-1">
                        {label}
                      </div>
                      <div className="space-y-0.5">
                        {items.map((s) => (
                          <SessionRow
                            key={s.id}
                            session={s}
                            active={s.id === activeId}
                            onOpen={() => onOpen(s.id)}
                            onDelete={() => onDelete(s.id, s.title || 'Untitled')}
                          />
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Status pill */}
      <div className="px-3 py-3 border-t border-border/70">
        <div className="flex items-center gap-2.5 px-3 py-2 rounded-xl bg-panel/80 border border-border/70 shadow-subtle">
          <span className="relative flex h-2 w-2 flex-shrink-0">
            <span
              className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                ollama ? 'bg-success' : 'bg-warning'
              }`}
            />
            <span
              className={`relative inline-flex rounded-full h-2 w-2 ${
                ollama ? 'bg-success' : 'bg-warning'
              }`}
            />
          </span>
          <div className="min-w-0 flex-1">
            <div className="text-[11.5px] font-semibold leading-tight text-textMain">
              {ollama ? 'Ollama Online' : 'Model Offline'}
            </div>
            <div className="text-[10px] text-textFaint leading-tight truncate mt-0.5">
              {ollama ? 'Local runtime connected' : 'Run `ollama serve`'}
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
}

function SessionRow({ session, active, onOpen, onDelete }) {
  return (
    <div
      className={`group relative flex items-center rounded-xl transition-all duration-150 ${
        active
          ? 'bg-accentSoft text-accent font-medium border border-accent/25'
          : 'hover:bg-panelHover/80 text-textMuted hover:text-textMain'
      }`}
    >
      <button
        onClick={onOpen}
        className="flex-1 min-w-0 text-left px-2.5 py-2 rounded-xl transition-colors cursor-pointer"
        title={session.title || 'Untitled'}
      >
        <div className="text-[12.5px] truncate font-medium">
          {session.title || 'Untitled'}
        </div>
        <div className="text-[10px] text-textFaint">
          {relativeTime(session.updated_at)}
          {session.message_count != null ? ` · ${session.message_count} msgs` : ''}
        </div>
      </button>
      <button
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        aria-label="Delete chat"
        className="opacity-0 group-hover:opacity-100 p-1.5 mr-1.5 rounded-lg text-textFaint
          hover:text-danger hover:bg-dangerSoft transition-all flex-shrink-0 cursor-pointer"
      >
        <Trash2 size={13} />
      </button>
    </div>
  );
}

function groupSessions(sessions) {
  const groups = {};
  sessions.forEach((s) => {
    const g = dateGroup(s.updated_at);
    if (!groups[g]) groups[g] = [];
    groups[g].push(s);
  });
  return Object.entries(groups);
}
