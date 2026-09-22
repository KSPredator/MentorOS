import React from 'react';
import { motion } from 'framer-motion';
import { Brain, Sparkles, TrendingDown } from 'lucide-react';

/**
 * Memory card. `updates` is a list of { topic, confidence } memory nudges;
 * `stats` is a memory snapshot with topics/strong_topics/weak_topics.
 */
export default function MemoryCard({ stats, updates }) {
  if (!updates?.length && !stats) return null;

  const nUpdated = updates?.length || 0;
  const strongN = Array.isArray(stats?.strong_topics) ? stats.strong_topics.length : null;
  const weakN = Array.isArray(stats?.weak_topics) ? stats.weak_topics.length : null;
  const totalN = stats?.topic_count ?? null;

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card rounded-2xl overflow-hidden shadow-card"
    >
      <div className="flex items-center gap-2.5 px-4.5 py-3.5 bg-successSoft/60 border-b border-border/80">
        <div className="w-8 h-8 rounded-xl bg-success text-white flex items-center justify-center shadow-sm">
          <Brain size={16} />
        </div>
        <div className="text-[13.5px] font-bold text-textMain">Learning Memory State</div>
        <Sparkles size={14} className="text-success ml-auto" />
      </div>

      <div className="p-4.5 space-y-3.5">
        {nUpdated > 0 && (
          <div>
            <div className="text-[11px] font-semibold text-textMuted uppercase tracking-wider mb-2">
              Updated This Interaction
            </div>
            <div className="space-y-1.5">
              {updates.map((u, i) => {
                const conf = u.confidence ?? 0;
                const isStrong = conf >= 0.7;
                const isWeak = conf < 0.5;
                const color = isStrong
                  ? 'var(--color-success)'
                  : isWeak
                    ? 'var(--color-danger)'
                    : 'var(--color-warning)';
                return (
                  <div
                    key={i}
                    className="flex items-center gap-2 text-[12.5px] rounded-xl bg-panel border border-border/80 px-3 py-2 shadow-subtle"
                  >
                    <span className="capitalize font-medium text-textMain truncate flex-1">
                      {u.topic || 'topic'}
                    </span>
                    <span
                      className="font-mono font-bold text-xs"
                      style={{ color }}
                    >
                      {Math.round(conf * 100)}%
                    </span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {stats && totalN != null && (
          <div className="grid grid-cols-3 gap-2.5 pt-1">
            <BigStat label="Total Topics" value={totalN} />
            <BigStat label="Mastered" value={strongN ?? 0} color="var(--color-success)" />
            <BigStat label="Review Needed" value={weakN ?? 0} color="var(--color-warning)" />
          </div>
        )}

        {stats && strongN === 0 && weakN === 0 && totalN === 0 && (
          <p className="text-[12px] text-textMuted leading-relaxed flex items-start gap-2 bg-panel/60 p-3 rounded-xl border border-border/70">
            <TrendingDown size={14} className="text-textFaint mt-0.5 flex-shrink-0" />
            <span>No topics tracked yet in this session. Questions and quiz scores will teach MentorOS what you know.</span>
          </p>
        )}
      </div>
    </motion.div>
  );
}

function BigStat({ label, value, color }) {
  return (
    <div className="rounded-xl bg-panel border border-border/80 px-3 py-2.5 text-center shadow-subtle">
      <div
        className="font-display font-extrabold text-xl"
        style={{ color: color || 'var(--color-textMain)' }}
      >
        {value}
      </div>
      <div className="text-[10.5px] font-semibold text-textFaint uppercase tracking-wider mt-0.5">{label}</div>
    </div>
  );
}
