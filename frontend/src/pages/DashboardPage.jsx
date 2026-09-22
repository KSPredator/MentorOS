import React, { useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Brain,
  Sparkles,
  Loader2,
  RotateCcw,
  TrendingUp,
  FileText,
  MessageSquareText,
  ListChecks,
  Activity,
  Award,
} from 'lucide-react';
import { useMemory } from '../stores/memory';
import { useChat } from '../stores/chat';
import { useStatus } from '../stores/status';
import { useCountUp } from '../lib/useCountUp';
import Button from '../components/ui/Button';
import ConfidenceMeter from '../components/ui/ConfidenceMeter';
import { SkeletonCards } from '../components/ui/Skeleton';
import EmptyState from '../components/ui/EmptyState';
import { stagger, staggerItem } from '../lib/variants';
import { toast } from 'sonner';

/** Learning dashboard: memory stats, reflection, and knowledge-base activity. */
export default function DashboardPage() {
  const snapshot = useMemory((s) => s.snapshot);
  const reflection = useMemory((s) => s.reflection);
  const loading = useMemory((s) => s.loading);
  const reflecting = useMemory((s) => s.reflecting);
  const loadMemory = useMemory((s) => s.load);
  const reflect = useMemory((s) => s.reflect);
  const sessions = useChat((s) => s.sessions);
  const activeId = useChat((s) => s.activeId);
  const status = useStatus();

  useEffect(() => {
    loadMemory(activeId || undefined);
  }, [activeId, loadMemory]);

  const onReflect = async () => {
    try {
      await reflect(activeId || undefined);
      toast.success('Study reflection generated');
    } catch (e) {
      toast.error(e?.message || 'Reflection failed');
    }
  };

  if (loading && !snapshot) {
    return (
      <div className="h-full overflow-y-auto p-6">
        <PageHeader title="Learning Dashboard" />
        <SkeletonCards count={6} />
      </div>
    );
  }

  const topics = snapshot?.topics || [];
  const topicCount = snapshot?.topic_count ?? topics.length;
  const strongN =
    snapshot?.strong_topics?.length ?? topics.filter((t) => (t.confidence ?? 0) >= 0.7).length;
  const weakN =
    snapshot?.weak_topics?.length ?? topics.filter((t) => (t.confidence ?? 0) < 0.6).length;
  const strongPct = topicCount ? strongN / topicCount : 0;
  const allMessages = sessions.reduce((a, s) => a + (s.message_count || 0), 0);

  return (
    <div className="h-full overflow-y-auto relative z-0">
      <div className="max-w-5xl mx-auto px-5 py-7 pb-24">
        <PageHeader
          title="Learning Dashboard"
          subtitle="Your personal knowledge retention computed from real interactions."
        />

        {/* Stat cards */}
        <motion.div
          variants={stagger}
          initial="initial"
          animate="animate"
          className="grid grid-cols-2 lg:grid-cols-4 gap-3.5 mb-6"
        >
          <StatCard
            icon={Brain}
            label="Topics in memory"
            value={topicCount}
            hint={`${strongN} strong · ${weakN} weak`}
            color="accent"
          />
          <StatCard
            icon={MessageSquareText}
            label="Conversations"
            value={sessions.length}
            hint={`${allMessages} messages total`}
            color="success"
          />
          <StatCard
            icon={FileText}
            label="Documents indexed"
            value={status.files_indexed ?? 0}
            hint={
              status.vector_store_chunks != null
                ? `${status.vector_store_chunks} knowledge chunks`
                : 'Chunks embedded'
            }
            color="warning"
          />
          <StatCard
            icon={ListChecks}
            label="Gate threshold"
            value={Math.round((status.eval_threshold ?? 0.6) * 100)}
            suffix="%"
            hint="Min confidence required"
            color="danger"
          />
        </motion.div>

        <div className="grid lg:grid-cols-3 gap-4.5">
          {/* Memory strength */}
          <motion.div {...staggerItem} className="glass-card rounded-2xl p-5 shadow-card">
            <SectionTitle icon={Activity} title="Memory Strength" />
            <div className="flex items-center gap-5 mt-5">
              <ConfidenceMeter score={strongPct} size={88} />
              <div className="space-y-2.5 text-sm min-w-0 flex-1">
                <Line label="Strong (mastered)" value={`${strongN}`} color="var(--color-success)" />
                <Line label="Weak (needs review)" value={`${weakN}`} color="var(--color-warning)" />
                <Line label="Total topics" value={`${topicCount}`} />
              </div>
            </div>
            <div className="mt-5 pt-4 border-t border-border/70 text-[12px] text-textMuted leading-relaxed flex items-center gap-2">
              <Award size={14} className="text-accent flex-shrink-0" />
              <span>Topics you answer accurately grow stronger; mistakes fade for active recall.</span>
            </div>
          </motion.div>

          {/* Reflection */}
          <motion.div {...staggerItem} className="lg:col-span-2 glass-card rounded-2xl p-5 shadow-card">
            <div className="flex items-center justify-between flex-wrap gap-2">
              <SectionTitle icon={Sparkles} title="AI Study Reflection" />
              <div className="flex items-center gap-2">
                {reflection && (
                  <Button size="sm" variant="ghost" onClick={() => useMemory.getState().clearReflection()}>
                    Clear
                  </Button>
                )}
                <Button size="sm" variant="primary" onClick={onReflect} disabled={reflecting}>
                  {reflecting ? (
                    <>
                      <Loader2 size={13} className="animate-spin" />
                      Reflecting…
                    </>
                  ) : (
                    <>
                      <Sparkles size={13} />
                      Generate reflection
                    </>
                  )}
                </Button>
              </div>
            </div>

            <div className="mt-4">
              {reflection ? (
                <div className="space-y-4">
                  {reflection.full_summary && (
                    <p className="text-[14px] leading-relaxed text-textMain/90 bg-panel/70 p-3.5 rounded-xl border border-border/70">
                      {reflection.full_summary}
                    </p>
                  )}
                  <div className="grid sm:grid-cols-2 gap-3">
                    {reflection.learned_well?.length > 0 && (
                      <InsightList
                        title="Learned Well"
                        items={reflection.learned_well}
                        color="var(--color-success)"
                        icon={TrendingUp}
                      />
                    )}
                    {reflection.needs_revision?.length > 0 && (
                      <InsightList
                        title="Needs Revision"
                        items={reflection.needs_revision}
                        color="var(--color-warning)"
                        icon={RotateCcw}
                      />
                    )}
                  </div>
                  {reflection.recommended_session && (
                    <div className="rounded-xl bg-accentSoft/60 border border-accent/30 p-3.5 shadow-sm">
                      <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-accent mb-1">
                        <Sparkles size={12} />
                        Recommended next session
                      </div>
                      <p className="text-[13px] text-textMain/90 leading-relaxed font-medium">
                        {reflection.recommended_session}
                      </p>
                    </div>
                  )}
                </div>
              ) : (
                <EmptyState
                  compact
                  icon={Sparkles}
                  title="No reflection yet"
                  body="Generate a reflection to see an AI diagnostic of what you've mastered and what needs revision."
                />
              )}
            </div>
          </motion.div>
        </div>

        {/* Topic bars from snapshot */}
        {topics.length > 0 && (
          <motion.div
            {...staggerItem}
            className="glass-card rounded-2xl p-5 mt-4.5 shadow-card"
          >
            <SectionTitle icon={FileText} title="Topic Mastery by Confidence" />
            <div className="space-y-3 mt-4">
              {topics.slice(0, 8).map((t) => {
                const conf = t.confidence ?? 0;
                const isStrong = conf >= 0.7;
                const isWeak = conf < 0.5;
                const barColor = isStrong
                  ? 'var(--color-success)'
                  : isWeak
                    ? 'var(--color-danger)'
                    : 'var(--color-warning)';
                return (
                  <div key={t.topic} className="group">
                    <div className="flex justify-between items-center text-[13px] mb-1.5">
                      <span className="capitalize font-medium text-textMain truncate pr-3 group-hover:text-accent transition-colors">
                        {t.topic}
                      </span>
                      <span className="font-mono text-xs text-textFaint flex items-center gap-2">
                        <span
                          className="px-1.5 py-0.5 rounded text-[10px] font-semibold"
                          style={{
                            background: isStrong
                              ? 'var(--color-successSoft)'
                              : isWeak
                                ? 'var(--color-dangerSoft)'
                                : 'var(--color-warningSoft)',
                            color: barColor,
                          }}
                        >
                          {Math.round(conf * 100)}%
                        </span>
                        <span>{t.interaction_count ?? 0} reviews</span>
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-background/80 overflow-hidden border border-border/40">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${Math.max(4, conf * 100)}%` }}
                        transition={{ duration: 0.85, ease: [0.22, 1, 0.36, 1] }}
                        className="h-full rounded-full"
                        style={{ background: barColor }}
                      />
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}

function PageHeader({ title, subtitle }) {
  return (
    <motion.div {...staggerItem} className="mb-6">
      <h1 className="font-display text-2xl sm:text-3xl font-extrabold tracking-tight text-textMain">{title}</h1>
      {subtitle && <p className="text-sm text-textMuted mt-1">{subtitle}</p>}
    </motion.div>
  );
}

function StatCard({ icon: Icon, label, value, suffix, hint, color }) {
  const animated = useCountUp(value);
  return (
    <motion.div
      variants={staggerItem}
      className="glass-card rounded-2xl p-4.5 hover:border-accent/40 hover:-translate-y-0.5 transition-all duration-200 shadow-card"
    >
      <div
        className="w-8.5 h-8.5 rounded-xl flex items-center justify-center mb-3"
        style={{
          background: `var(--color-${color}Soft)`,
          color: `var(--color-${color})`,
        }}
      >
        <Icon size={16} strokeWidth={2} />
      </div>
      <div className="font-display text-2xl font-bold tracking-tight text-textMain">
        {Math.round(animated)}
        {suffix || ''}
      </div>
      <div className="text-[12.5px] font-semibold text-textMain/85 mt-0.5">{label}</div>
      {hint && <div className="text-[11px] text-textFaint mt-0.5 truncate">{hint}</div>}
    </motion.div>
  );
}

function SectionTitle({ icon: Icon, title }) {
  return (
    <div className="flex items-center gap-2">
      <div className="w-6 h-6 rounded-lg bg-accentSoft text-accent flex items-center justify-center">
        <Icon size={14} />
      </div>
      <h2 className="text-[14px] font-bold text-textMain">{title}</h2>
    </div>
  );
}

function Line({ label, value, color }) {
  return (
    <div className="flex items-center gap-2">
      {color && <span className="w-2.5 h-2.5 rounded-full" style={{ background: color }} />}
      <span className="text-textMuted text-[13px]">{label}</span>
      <span className="font-mono font-bold text-textMain ml-auto">{value}</span>
    </div>
  );
}

function InsightList({ title, items, color, icon: Icon }) {
  return (
    <div className="p-3.5 rounded-xl bg-panel/70 border border-border/70">
      <div className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider mb-2" style={{ color }}>
        <Icon size={12} />
        {title}
      </div>
      <ul className="space-y-1.5">
        {items.map((item, i) => (
          <li key={i} className="text-[12.5px] text-textMain/90 flex gap-2">
            <span style={{ color }}>•</span>
            <span>{typeof item === 'string' ? item : item.text || JSON.stringify(item)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
