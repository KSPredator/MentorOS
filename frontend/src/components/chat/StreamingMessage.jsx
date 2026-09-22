import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Brain, Search, PenLine, ShieldCheck, Check } from 'lucide-react';
import { useChat } from '../../stores/chat';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import EvaluationBadge from './EvaluationBadge';

const STAGES = [
  { key: 'planning', label: 'Routing intent', icon: Brain },
  { key: 'retrieving', label: 'Searching notes', icon: Search },
  { key: 'generating', label: 'Drafting answer', icon: PenLine },
  { key: 'evaluating', label: 'Verifying citations', icon: ShieldCheck },
];

/**
 * Live streaming bubble with stage timeline and tokens.
 */
export default function StreamingMessage() {
  const stage = useChat((s) => s.streamStage);
  const action = useChat((s) => s.streamAction);
  const route = useChat((s) => s.streamRoute);
  const text = useChat((s) => s.streamText);
  const evaluation = useChat((s) => s.streamEvaluation);

  // Which stages to show: memory/quiz/podcast skip retrieval
  const showRetrieval =
    route?.route_method !== 'memory' &&
    route?.action !== 'quiz' &&
    route?.action !== 'podcast';
  const stages = STAGES.filter((s) => s.key !== 'retrieving' || showRetrieval);
  const stageIdx = stages.findIndex((s) => s.key === stage);
  const generating =
    stage === 'generating' || stage === 'evaluating' || (text.length > 0 && stage !== 'done');

  return (
    <div className="flex gap-3.5">
      <div
        className="w-8 h-8 rounded-full bg-panel border border-border flex items-center justify-center flex-shrink-0 text-accent mt-0.5 shadow-sm"
        style={{ boxShadow: '0 0 12px rgba(14, 165, 233, 0.15)' }}
      >
        <BotGlyph />
      </div>
      <div className="min-w-0 flex-1">
        {/* Stage timeline */}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 mb-3">
          {stages.map((s, i) => {
            const done = stageIdx > i || stage === 'done';
            const active = stageIdx === i && stage !== 'done';
            const skipped = stageIdx > -1 && stageIdx < i && !showRetrieval && s.key === 'retrieving';
            const Icon = s.icon;
            if (skipped) return null;
            return (
              <div
                key={s.key}
                className={`flex items-center gap-1.5 text-[11px] font-medium transition-colors ${
                  done ? 'text-success' : active ? 'text-accent' : 'text-textFaint'
                }`}
              >
                <motion.span
                  animate={active ? { scale: [1, 1.15, 1] } : { scale: 1 }}
                  transition={active ? { repeat: Infinity, duration: 1.2 } : undefined}
                  className="w-5 h-5 rounded-md flex items-center justify-center border shadow-subtle"
                  style={{
                    borderColor: done
                      ? 'var(--color-success)'
                      : active
                        ? 'var(--color-accent)'
                        : 'var(--color-border)',
                    background: done
                      ? 'var(--color-successSoft)'
                      : active
                        ? 'var(--color-accentSoft)'
                        : 'transparent',
                  }}
                >
                  {done ? <Check size={11} /> : <Icon size={11} />}
                </motion.span>
                <span className="hidden sm:inline">{s.label}</span>
              </div>
            );
          })}
        </div>

        {/* Action chip */}
        <AnimatePresence>
          {action && (
            <motion.div
              initial={{ opacity: 0, y: -4 }}
              animate={{ opacity: 1, y: 0 }}
              className="inline-flex items-center gap-1.5 text-[11px] font-mono px-2.5 py-1 rounded-lg
                bg-accentSoft text-accent border border-accent/25 mb-2.5 shadow-subtle"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-accent animate-pulse" />
              {route?.route_method || action}
              {route?.route_confidence != null &&
                ` · ${(route.route_confidence * 100).toFixed(0)}% confidence`}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Tokens */}
        {generating && (
          <div
            className={`answer-md text-textMain break-words ${
              stage === 'evaluating' ? 'opacity-80' : ''
            }`}
          >
            {text ? (
              <>
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
                <span className="streaming-cursor" aria-hidden="true" />
              </>
            ) : (
              <TypingDots />
            )}
            {stage === 'evaluating' && text && (
              <div className="mt-2.5 flex items-center gap-2 text-[11.5px] text-textMuted bg-warningSoft/50 p-2 rounded-lg border border-warning/20">
                <ShieldCheck size={13} className="text-warning animate-pulse" />
                <span>Checking claims and verifying evidence against your documents…</span>
              </div>
            )}
          </div>
        )}

        {/* Live evaluation preview */}
        {evaluation && (
          <div className="mt-3">
            <EvaluationBadge evaluation={evaluation} live />
          </div>
        )}
      </div>
    </div>
  );
}

function TypingDots() {
  return (
    <div className="flex items-center gap-1.5 py-1.5" aria-label="Generating">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-accent"
          animate={{ opacity: [0.3, 1, 0.3], y: [0, -3, 0] }}
          transition={{ repeat: Infinity, duration: 1, delay: i * 0.15 }}
        />
      ))}
    </div>
  );
}

function BotGlyph() {
  return (
    <svg width="15" height="15" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="3.2" stroke="currentColor" strokeWidth="1.7" />
      <circle cx="12" cy="4.5" r="1.5" fill="currentColor" />
      <circle cx="12" cy="19.5" r="1.5" fill="currentColor" opacity="0.7" />
      <path d="M12 8.8V6M12 18v-2.8" stroke="currentColor" strokeWidth="1.4" />
    </svg>
  );
}
