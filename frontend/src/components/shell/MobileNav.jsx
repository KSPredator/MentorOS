import React from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Menu,
  MessageSquareText,
  LayoutDashboard,
  FolderOpen,
  Settings,
  Plus,
  Sun,
  Moon,
  Radio,
} from 'lucide-react';
import { useUI } from '../../stores/ui';
import { useChat } from '../../stores/chat';
import { useFiles } from '../../stores/files';
import Logo from '../ui/Logo';

const TABS = [
  { to: '/', icon: MessageSquareText, label: 'Chat' },
  { to: '/podcast', icon: Radio, label: 'Podcast' },
  { to: '/dashboard', icon: LayoutDashboard, label: 'Dash' },
  { to: '/documents', icon: FolderOpen, label: 'Docs' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

/** Mobile top bar + bottom tab bar with glass styling. */
export default function MobileNav() {
  const navigate = useNavigate();
  const location = useLocation();
  const setSidebar = useUI((s) => s.setSidebar);
  const dark = useUI((s) => s.dark);
  const toggleDark = useUI((s) => s.toggleDark);
  const newChat = useChat((s) => s.newChat);
  const files = useFiles((s) => s.files);

  return (
    <>
      {/* Top bar */}
      <header className="md:hidden flex items-center justify-between h-13 px-3.5 border-b border-border/80 bg-background/80 backdrop-blur-md flex-shrink-0 z-20">
        <button
          onClick={() => setSidebar(true)}
          aria-label="Open menu"
          className="p-2 rounded-xl text-textMuted hover:text-textMain hover:bg-panel transition-colors cursor-pointer"
        >
          <Menu size={18} />
        </button>
        <Logo size="sm" />
        <div className="flex items-center gap-1">
          <button
            onClick={toggleDark}
            aria-label={dark ? 'Switch to light mode' : 'Switch to dark mode'}
            className="p-2 rounded-xl text-textMuted hover:text-textMain hover:bg-panel transition-colors cursor-pointer"
          >
            {dark ? <Sun size={17} className="text-amber-400" /> : <Moon size={17} className="text-sky-500" />}
          </button>
          <button
            onClick={() => {
              newChat();
              navigate('/');
            }}
            aria-label="New chat"
            className="p-2 rounded-xl text-accent hover:bg-accentSoft transition-colors cursor-pointer"
          >
            <Plus size={18} />
          </button>
        </div>
      </header>

      {/* Bottom tabs */}
      <nav
        className="md:hidden fixed bottom-0 inset-x-0 z-30 flex glass-panel border-t border-border/80 pb-[env(safe-area-inset-bottom)] shadow-card"
        aria-label="Primary navigation"
      >
        {TABS.map((t) => {
          const active = location.pathname === t.to;
          const Icon = t.icon;
          return (
            <button
              key={t.to}
              onClick={() => navigate(t.to)}
              className={`flex-1 flex flex-col items-center justify-center gap-0.5 py-2.5 text-[10.5px] font-medium transition-colors cursor-pointer relative ${
                active ? 'text-accent font-semibold' : 'text-textFaint hover:text-textMuted'
              }`}
              aria-current={active ? 'page' : undefined}
            >
              {active && (
                <span className="absolute top-0 w-8 h-0.5 bg-accent rounded-full" />
              )}
              <Icon size={18} strokeWidth={active ? 2.2 : 1.7} />
              <span>{t.label === 'Docs' && files.length > 0 ? `Docs (${files.length})` : t.label}</span>
            </button>
          );
        })}
      </nav>
    </>
  );
}
