import React, { useRef, useEffect, useState, useCallback } from 'react';
import {
  Send, Paperclip, ChevronRight, Activity, Zap, Brain,
  Sparkles, AlertTriangle, CheckCircle2, Loader2, BarChart2
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

// ── Planner Badge ────────────────────────────────────────────────────────────
const PLANNER_COLORS = {
  RETRIEVE: 'bg-sky-500/15 text-sky-400 border-sky-500/30',
  QUIZ:     'bg-violet-500/15 text-violet-400 border-violet-500/30',
  MEMORY:   'bg-amber-500/15 text-amber-400 border-amber-500/30',
  PODCAST:  'bg-pink-500/15 text-pink-400 border-pink-500/30',
  GENERAL:  'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
};

function PlannerBadge({ action }) {
  const color = PLANNER_COLORS[action] || PLANNER_COLORS.GENERAL;
  return (
    <span className={`text-[10px] font-bold uppercase tracking-widest px-2 py-0.5 rounded-full border ${color}`}>
      {action}
    </span>
  );
}

// ── Confidence Gauge ─────────────────────────────────────────────────────────
function ConfidenceGauge({ score }) {
  const pct = Math.round((score ?? 1) * 100);
  const color = pct >= 70 ? 'bg-emerald-500' : pct >= 50 ? 'bg-amber-500' : 'bg-red-500';
  return (
    <div className="flex items-center gap-2 mt-1">
      <div className="flex-1 h-1.5 bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${color}`}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
        />
      </div>
      <span className="text-[10px] text-gray-500 dark:text-gray-400 tabular-nums">{pct}%</span>
    </div>
  );
}

// ── Evidence Accordion ────────────────────────────────────────────────────────
function EvidenceAccordion({ citations, planner, confidence, evaluation }) {
  const citCount = citations?.length ?? 0;
  const passed = evaluation?.passed_gate ?? true;

  return (
    <div className="bg-white dark:bg-gray-900/50 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden mt-3">
      <details className="group">
        <summary className="flex items-center justify-between p-3 cursor-pointer select-none list-none">
          <div className="flex items-center gap-2">
            <Activity size={14} className="text-accent flex-shrink-0" />
            <span className="text-xs font-medium text-gray-700 dark:text-gray-300">AI Thinking & Evidence</span>
          </div>
          <div className="flex items-center gap-2">
            {planner && <PlannerBadge action={planner.action} />}
            {citCount > 0 && (
              <span className="text-[10px] px-2 py-0.5 bg-gray-100 dark:bg-gray-800 text-gray-500 rounded-full">
                {citCount} source{citCount !== 1 ? 's' : ''}
              </span>
            )}
            {!passed && (
              <AlertTriangle size={12} className="text-amber-400" />
            )}
            <ChevronRight size={14} className="text-gray-400 transition-transform group-open:rotate-90" />
          </div>
        </summary>

        <div className="p-4 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-black/20 space-y-3">
          {/* Planner step */}
          {planner && (
            <div className="flex gap-2 text-xs text-gray-600 dark:text-gray-400">
              <CheckCircle2 size={12} className="text-emerald-400 mt-0.5 flex-shrink-0" />
              <span>Planner routed to <strong className="text-gray-800 dark:text-gray-200">{planner.action}</strong> — {planner.reasoning}</span>
            </div>
          )}

          {/* Citations */}
          {citations?.map((c, i) => (
            <div key={i} className="flex gap-2 text-xs text-gray-600 dark:text-gray-400">
              <CheckCircle2 size={12} className="text-emerald-400 mt-0.5 flex-shrink-0" />
              <span>Retrieved from <strong className="text-gray-800 dark:text-gray-200">{c.source_file}</strong> (pg. {c.page_number}) — score {(c.score * 100).toFixed(0)}%</span>
            </div>
          ))}

          {/* Confidence */}
          {confidence !== undefined && (
            <div>
              <p className="text-[10px] uppercase font-semibold tracking-wider text-gray-500 mb-1">Confidence</p>
              <ConfidenceGauge score={confidence} />
            </div>
          )}

          {/* Evaluation reasoning */}
          {evaluation?.reasoning && (
            <p className="text-[10px] text-gray-500 italic leading-relaxed">{evaluation.reasoning}</p>
          )}

          {/* Gate blocked */}
          {!passed && (
            <div className="flex gap-2 text-xs text-amber-600 dark:text-amber-400">
              <AlertTriangle size={12} className="mt-0.5 flex-shrink-0" />
              <span>Hallucination gate blocked this answer (confidence below threshold).</span>
            </div>
          )}
        </div>
      </details>
    </div>
  );
}

// ── Quick Actions ─────────────────────────────────────────────────────────────
function QuickActions({ onAction }) {
  const actions = ['Explain Simpler', 'Give Example', 'Generate Quiz'];
  return (
    <div className="flex flex-wrap gap-2 mt-3">
      {actions.map((a) => (
        <button
          key={a}
          onClick={() => onAction(a)}
          className="text-xs px-3 py-1.5 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-md text-gray-700 dark:text-gray-300 transition-colors"
        >
          {a}
        </button>
      ))}
    </div>
  );
}

// ── AI Message ────────────────────────────────────────────────────────────────
function AIMessage({ msg, onQuickAction }) {
  const text = msg.content || '';
  const isStreaming = msg.isStreaming;

  return (
    <div className="flex gap-3 mb-8 justify-start">
      <div className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center flex-shrink-0 mt-1 text-accent border border-accent/30">
        {isStreaming ? (
          <Loader2 size={14} className="animate-spin" />
        ) : (
          <Brain size={14} />
        )}
      </div>

      <div className="max-w-[85%] min-w-0">
        <div className="prose dark:prose-invert max-w-none text-gray-800 dark:text-gray-200 text-sm leading-relaxed whitespace-pre-wrap">
          {text}
          {isStreaming && <span className="ml-0.5 inline-block w-0.5 h-4 bg-accent animate-pulse align-middle" />}
        </div>

        {!isStreaming && !msg.isError && (
          <>
            <EvidenceAccordion
              citations={msg.citations}
              planner={msg.planner}
              confidence={msg.confidence}
              evaluation={msg.evaluation}
            />
            <QuickActions onAction={onQuickAction} />
          </>
        )}
      </div>
    </div>
  );
}

// ── User Message ──────────────────────────────────────────────────────────────
function UserMessage({ content }) {
  return (
    <div className="flex gap-3 mb-8 justify-end">
      <div className="max-w-[80%] bg-gray-100 dark:bg-gray-800/80 p-4 rounded-2xl rounded-tr-sm border border-gray-200 dark:border-gray-700/50 text-gray-900 dark:text-gray-100 text-sm">
        {content}
      </div>
    </div>
  );
}

// ── New Chat Hero ─────────────────────────────────────────────────────────────
function NewChatHero({ onSuggestion }) {
  const suggestions = [
    { label: 'Summarize this document', icon: Sparkles },
    { label: 'Quiz me on Chapter 3', icon: Zap },
    { label: 'Explain simply', icon: Brain },
    { label: 'What are my weak topics?', icon: BarChart2 },
  ];

  return (
    <div className="flex flex-col items-center justify-center h-full px-4 w-full max-w-3xl mx-auto">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-12"
      >
        <div className="inline-flex items-center justify-center p-4 bg-accent/10 text-accent rounded-2xl mb-6 shadow-xl shadow-accent/5">
          <Brain size={48} />
        </div>
        <h1 className="text-4xl font-bold mb-4 tracking-tight">MentorOS</h1>
        <p className="text-xl text-gray-600 dark:text-gray-400">Upload your notes. Ask anything. Learn with evidence.</p>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="w-full flex flex-wrap justify-center gap-3 mt-4"
      >
        {suggestions.map(({ label, icon: Icon }) => (
          <button
            key={label}
            onClick={() => onSuggestion(label)}
            className="px-4 py-2 bg-white dark:bg-gray-800/50 hover:bg-gray-50 dark:hover:bg-gray-800 border border-gray-200 dark:border-gray-700/50 hover:border-accent/40 rounded-full text-sm text-gray-700 dark:text-gray-300 transition-colors flex items-center gap-2"
          >
            <Icon size={13} className="text-accent" />
            {label}
          </button>
        ))}
      </motion.div>
    </div>
  );
}

// ── Main CenterArea ──────────────────────────────────────────────────────────
export default function CenterArea({ messages, isLoading, sendMessage, onOpenFilePanel, modelName }) {
  const [input, setInput] = useState('');
  const bottomRef = useRef(null);
  const textareaRef = useRef(null);

  // Auto-scroll on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Auto-resize textarea
  useEffect(() => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight, 128) + 'px';
  }, [input]);

  const handleSend = useCallback(() => {
    if (!input.trim() || isLoading) return;
    sendMessage(input.trim());
    setInput('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [input, isLoading, sendMessage]);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleQuickAction = useCallback((action) => {
    const lastUser = [...messages].reverse().find(m => m.role === 'user');
    const topic = lastUser?.content || 'the previous topic';
    if (action === 'Explain Simpler') sendMessage(`Explain simpler: ${topic}`);
    else if (action === 'Give Example') sendMessage(`Give a concrete example for: ${topic}`);
    else if (action === 'Generate Quiz') sendMessage(`Quiz me on: ${topic}`);
  }, [messages, sendMessage]);

  const isEmpty = messages.length === 0;

  return (
    <div className="flex flex-col h-full w-full relative">
      {/* Message thread */}
      <div className="flex-1 overflow-y-auto p-4 md:p-8 pb-36 w-full max-w-4xl mx-auto">
        <AnimatePresence>
          {isEmpty ? (
            <NewChatHero onSuggestion={(s) => { setInput(s); textareaRef.current?.focus(); }} />
          ) : (
            messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
              >
                {msg.role === 'user'
                  ? <UserMessage content={msg.content} />
                  : <AIMessage msg={msg} onQuickAction={handleQuickAction} />
                }
              </motion.div>
            ))
          )}
        </AnimatePresence>
        <div ref={bottomRef} />
      </div>

      {/* Sticky Input Bar */}
      <div className="absolute bottom-0 left-0 w-full p-4 md:p-6 bg-gradient-to-t from-background via-background/95 to-transparent">
        <div className="max-w-3xl mx-auto">
          <div className="bg-white/80 dark:bg-gray-900/80 border border-gray-200 dark:border-gray-700/60 rounded-2xl p-2 shadow-2xl focus-within:border-accent/50 focus-within:ring-1 focus-within:ring-accent/50 transition-all backdrop-blur-md">
            <textarea
              ref={textareaRef}
              id="chat-input"
              rows="1"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask a question about your uploaded documents..."
              disabled={isLoading}
              className="w-full bg-transparent text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 resize-none outline-none px-3 py-2 max-h-32 disabled:opacity-50"
            />
            <div className="flex justify-between items-center mt-1 px-2">
              <div className="flex items-center gap-3">
                <button
                  id="attach-file-btn"
                  onClick={onOpenFilePanel}
                  className="text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800"
                  title="Upload document"
                >
                  <Paperclip size={18} />
                </button>
                {modelName && (
                  <span className="text-[10px] uppercase font-bold tracking-wider text-gray-500 bg-gray-100 dark:bg-gray-800/50 px-2 py-1 rounded-full border border-gray-200 dark:border-gray-700/50">
                    {modelName}
                  </span>
                )}
              </div>
              <button
                id="send-btn"
                onClick={handleSend}
                disabled={isLoading || !input.trim()}
                className="bg-gray-900 dark:bg-white text-white dark:text-black p-2 rounded-xl hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors flex items-center justify-center shadow-lg disabled:opacity-40 disabled:cursor-not-allowed"
              >
                {isLoading
                  ? <Loader2 size={16} className="animate-spin" />
                  : <Send size={16} />
                }
              </button>
            </div>
          </div>
          <p className="text-center text-[10px] text-gray-400 mt-2">
            Shift+Enter for new line · Enter to send
          </p>
        </div>
      </div>
    </div>
  );
}
