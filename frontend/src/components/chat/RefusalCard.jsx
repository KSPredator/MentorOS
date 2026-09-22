import React from 'react';
import { ShieldAlert, RefreshCw, BookOpen, AlertTriangle } from 'lucide-react';
import { motion } from 'framer-motion';
import { useChat } from '../../stores/chat';
import Button from '../ui/Button';

/**
 * Gate-refusal card: shown when evaluation is withheld to prevent hallucination.
 * Explains reasons and offers refine + fallback recall actions.
 */
export default function RefusalCard({ message }) {
  const content = message?.content || '';
  const meta = message?.meta || {};
  const evaluation = meta.evaluation;
  const sendMessage = useChat((s) => s.sendMessage);

  const suggestions = meta.refusal_suggestions || [
    'Explain this more simply',
    'What DO my documents say about this?',
    'Quiz me on related topics instead',
  ];

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="rounded-2xl border border-warning/40 bg-warningSoft/50 backdrop-blur-md overflow-hidden shadow-card"
    >
      <div className="flex items-start gap-3.5 p-4.5">
        <div className="w-9 h-9 rounded-xl bg-warning/20 text-warning flex items-center justify-center flex-shrink-0 shadow-sm">
          <ShieldAlert size={18} strokeWidth={1.8} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1.5 flex-wrap">
            <span className="text-[13.5px] font-bold text-warning">
              Answer withheld — hallucination guard triggered
            </span>
            {evaluation?.score != null && (
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-background/80 border border-warning/35 text-warning font-semibold">
                Confidence {Math.round(evaluation.score * 100)}%
                {evaluation.threshold != null
                  ? ` < ${Math.round(evaluation.threshold * 100)}% min`
                  : ''}
              </span>
            )}
          </div>

          <div className="answer-md text-[13.5px] text-textMain/90 leading-relaxed mb-2">
            {content}
          </div>

          {evaluation?.issues && evaluation.issues.length > 0 && (
            <div className="mt-2.5 p-3 rounded-xl bg-panel/70 border border-warning/20 text-[12px] text-textMuted space-y-1">
              <div className="flex items-center gap-1.5 font-semibold text-warning text-[11px] uppercase tracking-wider">
                <AlertTriangle size={12} />
                Verification Findings
              </div>
              <ul className="list-disc pl-4 space-y-0.5">
                {evaluation.issues.slice(0, 4).map((issue, i) => (
                  <li key={i}>{typeof issue === 'string' ? issue : issue.message}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="flex flex-wrap gap-2 mt-3.5">
            {suggestions.map((s) => (
              <Button
                key={s}
                size="sm"
                variant="secondary"
                onClick={() => sendMessage(s)}
              >
                {s.toLowerCase().includes('quiz') ? (
                  <BookOpen size={12} />
                ) : (
                  <RefreshCw size={12} />
                )}
                {s}
              </Button>
            ))}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
