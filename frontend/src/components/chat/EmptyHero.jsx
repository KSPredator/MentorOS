import React from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import {
  MessageSquareText,
  FolderOpen,
  ShieldCheck,
  Brain,
  ListChecks,
  Mic,
  ArrowRight,
  Sparkles,
} from 'lucide-react';
import { useFiles } from '../../stores/files';
import { useStatus } from '../../stores/status';
import { useChat } from '../../stores/chat';

const FEATURES = [
  {
    icon: ShieldCheck,
    title: 'Verified answers',
    body: 'Every response passes a hallucination gate before you see it.',
    color: 'var(--color-success)',
    bg: 'var(--color-successSoft)',
  },
  {
    icon: MessageSquareText,
    title: 'Cited responses',
    body: 'Click any source chip to jump directly to the exact chunk.',
    color: 'var(--color-accent)',
    bg: 'var(--color-accentSoft)',
  },
  {
    icon: Brain,
    title: 'Learns with you',
    body: 'Strong answers stick; forgotten topics surface automatically.',
    color: '#a78bfa',
    bg: 'rgba(167, 139, 250, 0.12)',
  },
  {
    icon: ListChecks,
    title: 'Active recall',
    body: 'Generate interactive quizzes from your materials in one click.',
    color: 'var(--color-warning)',
    bg: 'var(--color-warningSoft)',
  },
  {
    icon: Mic,
    title: 'Podcast mode',
    body: 'Turn dense topics into a conversational two-host study script.',
    color: '#f472b6',
    bg: 'rgba(244, 114, 182, 0.12)',
  },
  {
    icon: FolderOpen,
    title: 'Local-first',
    body: 'Documents never leave your machine — embedded and run on-device.',
    color: '#38bdf8',
    bg: 'rgba(56, 189, 248, 0.12)',
  },
];

const SUGGESTIONS = [
  'Summarize the core themes in my uploaded notes',
  'Quiz me on the most important concepts',
  'Generate a 2-host podcast study script',
  'What are my weakest topics right now?',
];

/**
 * Empty-state hero: 3D constellation scene over value prop,
 * starter prompts, and interactive feature cards.
 */
export default function EmptyHero() {
  const files = useFiles((s) => s.files);
  const loaded = useFiles((s) => s.loaded);
  const pipelineReady = useStatus((s) => s.pipeline_ready);
  const sendMessage = useChat((s) => s.sendMessage);
  const navigate = useNavigate();

  return (
    <div className="min-h-full flex flex-col items-center justify-center px-4 py-8 sm:py-12 relative z-0">
      <HeroScene />

      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        className="text-center max-w-2xl -mt-2"
      >
        {/* Status Pill */}
        <div className="inline-flex items-center gap-2 text-[11px] font-mono px-3.5 py-1.5 rounded-full border border-border/80 bg-panel/85 backdrop-blur-md text-textMuted mb-5 shadow-sm">
          <span className="w-2 h-2 rounded-full bg-accent animate-pulse" />
          {pipelineReady
            ? 'Knowledge base active & ready'
            : loaded && files.length === 0
              ? 'Add your first document to start'
              : 'Warming up knowledge base…'}
        </div>

        {/* Hero Headline */}
        <h1 className="font-display text-4xl sm:text-5xl font-extrabold tracking-tight leading-[1.12] mb-4 text-textMain">
          Study your documents.
          <br />
          <span className="bg-gradient-to-r from-accent via-sky-400 to-indigo-500 bg-clip-text text-transparent">
            Ask anything.
          </span>
          <br />
          Learn with evidence.
        </h1>

        <p className="text-[14.5px] sm:text-[15.5px] text-textMuted leading-relaxed max-w-lg mx-auto mb-7">
          MentorOS is a private, local AI study companion. Every answer is grounded in
          <span className="text-textMain font-medium"> your uploaded notes</span>, verified
          against hallucinations, and cited.
        </p>

        {/* Action Button */}
        {(!loaded || files.length === 0) ? (
          <button
            onClick={() => navigate('/documents')}
            className="inline-flex items-center gap-2.5 text-sm font-semibold px-6 py-3 rounded-xl
              bg-accent text-white hover:bg-accentDim transition-all duration-200 shadow-lg shadow-accent/25 hover:shadow-accent/35 hover:-translate-y-0.5 cursor-pointer"
          >
            <FolderOpen size={16} />
            <span>Upload your study notes</span>
            <ArrowRight size={14} />
          </button>
        ) : (
          /* Suggestion Quick Chips */
          <div className="flex flex-wrap items-center justify-center gap-2 max-w-xl mx-auto">
            {SUGGESTIONS.map((text) => (
              <button
                key={text}
                onClick={() => sendMessage(text)}
                className="inline-flex items-center gap-1.5 text-xs px-3.5 py-2 rounded-xl
                  border border-border/80 bg-panel/80 hover:bg-panel hover:border-accent/40
                  text-textMain/90 hover:text-accent backdrop-blur transition-all duration-150 hover:-translate-y-0.5 shadow-sm cursor-pointer"
              >
                <Sparkles size={11} className="text-accent" />
                <span>{text}</span>
              </button>
            ))}
          </div>
        )}
      </motion.div>

      {/* Feature Grid */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.35, duration: 0.55 }}
        className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3.5 mt-10 w-full max-w-3xl"
      >
        {FEATURES.map((f) => (
          <div
            key={f.title}
            className="glass-card rounded-2xl p-4.5 hover:border-accent/40 hover:-translate-y-0.5 transition-all duration-200 group relative overflow-hidden"
          >
            <div
              className="w-8 h-8 rounded-xl flex items-center justify-center mb-2.5 transition-transform duration-200 group-hover:scale-110"
              style={{ background: f.bg, color: f.color }}
            >
              <f.icon size={16} strokeWidth={2} />
            </div>
            <div className="text-[13.5px] font-semibold text-textMain mb-1">{f.title}</div>
            <div className="text-[12px] text-textMuted leading-relaxed">{f.body}</div>
          </div>
        ))}
      </motion.div>
    </div>
  );
}

function HeroScene() {
  const [Scene, setScene] = React.useState(null);
  const [failed, setFailed] = React.useState(false);

  React.useEffect(() => {
    let alive = true;
    import('./HeroScene')
      .then((m) => {
        if (alive) setScene(() => m.default);
      })
      .catch(() => {
        if (alive) setFailed(true);
      });
    return () => {
      alive = false;
    };
  }, []);

  if (failed) return null;
  if (!Scene) {
    return (
      <div
        className="w-full max-w-lg h-48 mb-2 rounded-3xl skeleton"
        aria-hidden
      />
    );
  }
  return <Scene />;
}
