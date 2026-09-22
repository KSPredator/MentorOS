import React from 'react';
import { motion } from 'framer-motion';
import { ShieldCheck, ShieldAlert, Loader2, Info, CheckCircle2 } from 'lucide-react';

/**
 * Hallucination-gate result chip. Server evaluation shape:
 * { passed_gate, confidence_score, faithfulness_score,
 *   semantic_similarity, reasoning, threshold_used }
 */
export default function EvaluationBadge({ evaluation, live = false }) {
  if (!evaluation) return null;
  const {
    passed_gate,
    confidence_score,
    faithfulness_score,
    threshold_used,
    reasoning,
  } = evaluation;

  if (live || passed_gate == null) {
    return (
      <div className="flex items-center gap-2 px-3 py-2 rounded-xl bg-warningSoft border border-warning/30 text-[12px] text-warning">
        <Loader2 size={13} className="animate-spin" />
        Running hallucination check…
      </div>
    );
  }

  const pass = Boolean(passed_gate);
  const Icon = pass ? ShieldCheck : ShieldAlert;
  const color = pass ? 'var(--color-success)' : 'var(--color-danger)';
  const bg = pass ? 'var(--color-successSoft)' : 'var(--color-dangerSoft)';

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.97 }}
      animate={{ opacity: 1, scale: 1 }}
      className="rounded-xl border px-3 py-2.5"
      style={{ background: bg, borderColor: `${color}55` }}
    >
      <div className="flex items-center gap-2 text-[12px] font-medium" style={{ color }}>
        <Icon size={14} />
        <span>
          {pass
            ? 'Verified against sources'
            : 'Not verified — answer withheld'}
        </span>
        <span className="font-mono ml-auto opacity-80">
          {typeof confidence_score === 'number' && `${Math.round(confidence_score * 100)}%`}
          {threshold_used != null &&
            ` / ${Math.round(threshold_used * 100)}% gate`}
        </span>
      </div>
      <div className="flex items-center gap-1.5 mt-1 text-[11px] text-textMuted">
        <Info size={11} className="text-textFaint" />
        Faithfulness:{' '}
        {typeof faithfulness_score === 'number'
          ? `${Math.round(faithfulness_score * 100)}%`
          : '—'}
        {reasoning && <span className="truncate opacity-80">· {reasoning}</span>}
      </div>
      {pass && (
        <div className="flex items-center gap-1 mt-1.5 text-[11px] text-success font-medium">
          <CheckCircle2 size={11} />
          Shown after passing the hallucination gate.
        </div>
      )}
    </motion.div>
  );
}