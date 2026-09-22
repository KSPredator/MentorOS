import React, { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { PanelRightOpen, Sparkles, BookOpen, Radio } from 'lucide-react';
import MessageList from '../components/chat/MessageList';
import ChatInput from '../components/chat/ChatInput';
import { useChat } from '../stores/chat';
import { useUI } from '../stores/ui';
import { useStatus } from '../stores/status';
import { toast } from 'sonner';

/** Main chat workspace: header + thread + composer. */
export default function ChatPage() {
  const navigate = useNavigate();
  const streaming = useChat((s) => s.streaming);
  const streamError = useChat((s) => s.streamError);
  const sessions = useChat((s) => s.sessions);
  const activeId = useChat((s) => s.activeId);
  const filePanelOpen = useUI((s) => s.filePanelOpen);
  const toggleFilePanel = useUI((s) => s.toggleFilePanel);
  const ollama = useStatus((s) => s.ollama_available);
  const pipelineReady = useStatus((s) => s.pipeline_ready);
  const missingPackages = useStatus((s) => s.missing_packages) || [];

  useEffect(() => {
    if (streamError) toast.error(streamError);
  }, [streamError]);

  const active = sessions.find((s) => s.id === activeId);

  return (
    <div className="flex flex-col h-full min-h-0 relative">
      {/* Header */}
      <header className="flex items-center gap-3 h-14 px-5 border-b border-border/80 bg-background/70 backdrop-blur-md flex-shrink-0 z-10">
        <div className="min-w-0 flex-1">
          <h1 className="font-display font-semibold text-[15px] truncate text-textMain flex items-center gap-2">
            <span>{active?.title || 'New conversation'}</span>
          </h1>
          <div className="flex items-center gap-2 text-[11px] text-textFaint">
            <StatusDot ok={ollama && pipelineReady} />
            {!ollama
              ? 'Model offline'
              : !pipelineReady && missingPackages.length
                ? `Pipeline warming up (${missingPackages.join(', ')})`
                : 'Grounded answers · citations on'}
          </div>
        </div>

        {/* Model chip */}
        <div className="hidden sm:flex items-center gap-1.5 text-[11px] font-mono px-3 py-1 rounded-full border border-border/80 bg-panel/70 backdrop-blur text-textMuted shadow-sm">
          <Sparkles size={11} className="text-accent" />
          <span>{ollama ? 'ollama · local' : 'offline'}</span>
        </div>

        {/* Podcast Studio button */}
        <button
          onClick={() => navigate('/podcast')}
          aria-label="Open Podcast Studio"
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-accent hover:text-accentDim bg-accentSoft/60 hover:bg-accentSoft border border-accent/25 transition-all text-xs font-medium cursor-pointer"
        >
          <Radio size={14} className="text-accent" />
          <span className="text-[11.5px] font-semibold">Podcast Studio</span>
        </button>

        {!filePanelOpen && (
          <button
            onClick={toggleFilePanel}
            aria-label="Open knowledge base"
            className="hidden lg:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-textFaint hover:text-textMain hover:bg-panelHover transition-all text-xs font-medium cursor-pointer"
          >
            <BookOpen size={14} />
            <span className="text-[11.5px]">Knowledge Base</span>
            <PanelRightOpen size={14} />
          </button>
        )}
      </header>

      {/* Thread */}
      <MessageList />

      {/* Composer */}
      <div className="flex-shrink-0 border-t border-border/80 bg-background/80 backdrop-blur-md pt-2">
        {streaming && (
          <div className="max-w-3xl mx-auto px-4 pb-1.5">
            <IndeterminateLine />
          </div>
        )}
        <ChatInput autoFocus />
      </div>
    </div>
  );
}

function StatusDot({ ok }) {
  return (
    <span className="relative flex h-2 w-2">
      <span
        className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
          ok ? 'bg-success' : 'bg-warning'
        }`}
      />
      <span
        className={`relative inline-flex rounded-full h-2 w-2 ${
          ok ? 'bg-success' : 'bg-warning'
        }`}
      />
    </span>
  );
}

function IndeterminateLine() {
  return (
    <div className="h-0.5 w-full overflow-hidden rounded-full bg-panelHover" aria-hidden="true">
      <div
        className="progress-indeterminate h-full w-1/4 rounded-full"
        style={{ background: 'var(--color-accent)' }}
      />
    </div>
  );
}
