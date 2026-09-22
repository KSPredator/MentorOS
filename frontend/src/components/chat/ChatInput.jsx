import React, { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { Send, Square, Paperclip, Sparkles, CornerDownLeft } from 'lucide-react';
import { useChat } from '../../stores/chat';
import { useUI } from '../../stores/ui';
import { useStatus } from '../../stores/status';
import { useFiles } from '../../stores/files';

const QUICK_STARTS = [
  'Summarize my uploaded notes',
  'Generate a 2-voice podcast on my notes',
  'Quiz me on the hardest topic in my materials',
  'What are the key themes across my documents?',
];

/** Chat composer: auto-grow textarea, Enter to send, Shift+Enter newline, stop button while streaming. */
export default function ChatInput({ autoFocus }) {
  const [text, setText] = useState('');
  const textareaRef = useRef(null);
  const streaming = useChat((s) => s.streaming);
  const sendMessage = useChat((s) => s.sendMessage);
  const resetStream = useChat((s) => s.resetStream);
  const filePanelOpen = useUI((s) => s.filePanelOpen);
  const toggleFilePanel = useUI((s) => s.toggleFilePanel);
  const fileCount = useFiles((s) => s.files.length);
  const ollama = useStatus((s) => s.ollama_available);

  useEffect(() => {
    if (autoFocus) textareaRef.current?.focus();
  }, [autoFocus]);

  // Auto-grow textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = '0px';
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, [text]);

  const submit = () => {
    if (!text.trim() || streaming) return;
    sendMessage(text);
    setText('');
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const showQuickStarts = !streaming && text.length === 0;

  return (
    <div className="w-full max-w-3xl mx-auto px-4 pb-4 pt-2">
      {showQuickStarts && <QuickStarts onPick={(q) => setText(q)} />}

      <div className="relative rounded-2xl glass-card border border-border/80 shadow-card focus-within:border-accent/60 focus-within:shadow-glow transition-all duration-200">
        <textarea
          ref={textareaRef}
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={onKeyDown}
          placeholder={
            ollama
              ? 'Ask anything about your notes or study materials…'
              : 'Model offline — start Ollama to ask questions'
          }
          disabled={!ollama}
          className="w-full bg-transparent resize-none outline-none text-[15px] leading-relaxed
            px-4 pt-3.5 pb-2 placeholder:text-textFaint disabled:opacity-50 text-textMain"
          aria-label="Chat message"
        />
        <div className="flex items-center justify-between px-3 pb-2.5">
          <div className="flex items-center gap-1.5">
            <button
              onClick={toggleFilePanel}
              aria-label="Knowledge base files"
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11.5px] font-medium transition-all duration-150 cursor-pointer
                ${filePanelOpen ? 'text-accent bg-accentSoft border border-accent/25' : 'text-textFaint hover:text-textMain hover:bg-panelHover'}`}
            >
              <Paperclip size={13} />
              <span>{fileCount > 0 ? `${fileCount} docs indexed` : 'Add documents'}</span>
            </button>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[10.5px] text-textFaint hidden sm:flex items-center gap-1 font-mono">
              <CornerDownLeft size={10} /> Enter to send
            </span>
            {streaming ? (
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.94 }}
                onClick={resetStream}
                aria-label="Stop generating"
                className="w-8.5 h-8.5 rounded-xl bg-danger text-white flex items-center justify-center
                  hover:bg-danger/90 transition-colors shadow-sm cursor-pointer"
              >
                <Square size={13} fill="currentColor" />
              </motion.button>
            ) : (
              <motion.button
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.94 }}
                onClick={submit}
                disabled={!text.trim() || !ollama}
                aria-label="Send message"
                className="w-8.5 h-8.5 rounded-xl bg-accent text-white flex items-center justify-center
                  hover:bg-accentDim transition-all duration-150 shadow-md shadow-accent/20
                  disabled:opacity-30 disabled:pointer-events-none cursor-pointer"
              >
                <Send size={14} />
              </motion.button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function QuickStarts({ onPick }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.15 }}
      className="flex flex-wrap gap-1.5 sm:gap-2 justify-center mb-3"
    >
      {QUICK_STARTS.map((q) => (
        <button
          key={q}
          onClick={() => onPick(q)}
          className="flex items-center gap-1.5 text-[11.5px] px-3 py-1.5 rounded-full
            border border-border/80 glass-panel text-textMuted hover:text-accent
            hover:border-accent/40 hover:bg-accentSoft transition-all duration-150 hover:-translate-y-0.5 cursor-pointer shadow-subtle"
        >
          <Sparkles size={11} className="text-accent flex-shrink-0" />
          <span>{q}</span>
        </button>
      ))}
    </motion.div>
  );
}
