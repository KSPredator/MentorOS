import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Sun,
  Moon,
  Server,
  Cpu,
  Database,
  Info,
  ExternalLink,
  RefreshCw,
  ShieldCheck,
  Sparkles,
  Monitor,
} from 'lucide-react';
import { useUI } from '../stores/ui';
import { useStatus } from '../stores/status';
import Button from '../components/ui/Button';
import { stagger, staggerItem } from '../lib/variants';
import { getMotionPreference, setMotionPreference } from '../lib/useReducedMotion';

/** Settings: theme/motion, backend/model status, pipeline diagnostics. */
export default function SettingsPage() {
  const dark = useUI((s) => s.dark);
  const toggleDark = useUI((s) => s.toggleDark);
  const [motionOn, setMotionOn] = useState(getMotionPreference());
  const status = useStatus();
  const refresh = useStatus((s) => s.refresh);
  const [refreshing, setRefreshing] = useState(false);

  const onRefresh = async () => {
    setRefreshing(true);
    await refresh();
    setTimeout(() => setRefreshing(false), 400);
  };

  const onToggleMotion = (on) => {
    setMotionOn(on);
    setMotionPreference(on);
  };

  return (
    <div className="h-full overflow-y-auto relative z-0">
      <div className="max-w-3xl mx-auto px-5 py-7 pb-24">
        <motion.div {...staggerItem} className="mb-6">
          <h1 className="font-display text-2xl sm:text-3xl font-extrabold tracking-tight text-textMain">
            Settings & Diagnostics
          </h1>
          <p className="text-sm text-textMuted mt-1">
            Visual preferences and local system runtime telemetry.
          </p>
        </motion.div>

        <motion.div variants={stagger} initial="initial" animate="animate" className="space-y-4.5">
          {/* Appearance Card */}
          <Card title="Appearance & Animation" icon={dark ? Moon : Sun}>
            {/* Theme Toggle */}
            <div className="flex items-center justify-between flex-wrap gap-3">
              <div>
                <div className="text-[14px] font-semibold text-textMain">Color Theme</div>
                <div className="text-xs text-textMuted mt-0.5">
                  Light features dynamic watercolor atmosphere; Dark offers deep contrast.
                </div>
              </div>
              <div className="flex rounded-xl p-1 bg-panel border border-border/80 shadow-subtle">
                <button
                  onClick={() => dark && toggleDark()}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 cursor-pointer ${
                    !dark
                      ? 'bg-elevated text-accent shadow-sm border border-border/60'
                      : 'text-textMuted hover:text-textMain'
                  }`}
                  aria-pressed={!dark}
                >
                  <Sun size={13} />
                  Light
                </button>
                <button
                  onClick={() => !dark && toggleDark()}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 cursor-pointer ${
                    dark
                      ? 'bg-elevated text-accent shadow-sm border border-border/60'
                      : 'text-textMuted hover:text-textMain'
                  }`}
                  aria-pressed={dark}
                >
                  <Moon size={13} />
                  Dark
                </button>
              </div>
            </div>

            {/* Motion Toggle */}
            <div className="flex items-center justify-between flex-wrap gap-3 mt-5 pt-5 border-t border-border/70">
              <div>
                <div className="text-[14px] font-semibold text-textMain flex items-center gap-1.5">
                  Interface Motion
                  <Sparkles size={13} className="text-accent" />
                </div>
                <div className="text-xs text-textMuted mt-0.5">
                  3D hero scene, page transitions, and watercolor ink drifts.
                </div>
              </div>
              <div className="flex rounded-xl p-1 bg-panel border border-border/80 shadow-subtle">
                <button
                  onClick={() => onToggleMotion(true)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 cursor-pointer ${
                    motionOn
                      ? 'bg-elevated text-accent shadow-sm border border-border/60'
                      : 'text-textMuted hover:text-textMain'
                  }`}
                  aria-pressed={motionOn}
                >
                  <Sparkles size={13} />
                  On
                </button>
                <button
                  onClick={() => onToggleMotion(false)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-150 cursor-pointer ${
                    !motionOn
                      ? 'bg-elevated text-accent shadow-sm border border-border/60'
                      : 'text-textMuted hover:text-textMain'
                  }`}
                  aria-pressed={!motionOn}
                >
                  Off
                </button>
              </div>
            </div>
          </Card>

          {/* Runtime Status Card */}
          <Card
            title="Runtime Diagnostics"
            icon={Server}
            action={
              <Button size="sm" variant="secondary" onClick={onRefresh} disabled={refreshing}>
                <RefreshCw size={12} className={refreshing ? 'animate-spin' : ''} />
                Refresh
              </Button>
            }
          >
            <div className="space-y-3">
              <Row
                label="API Server"
                value={status.apiReachable ? 'Connected (:8000)' : 'Unreachable'}
                ok={status.apiReachable}
              />
              <Row
                label="Ollama Engine"
                value={
                  status.ollama_available
                    ? `Online · ${status.model_name || 'Active'}`
                    : 'Not detected — run `ollama serve`'
                }
                ok={status.ollama_available}
              />
              <Row
                label="RAG Pipeline"
                value={
                  status.pipeline_ready
                    ? 'Active (Embeddings + ChromaDB)'
                    : 'Not fully configured'
                }
                ok={status.pipeline_ready}
              />
              <Row
                label="Vector Store Index"
                value={
                  status.vector_store_chunks != null
                    ? `${status.vector_store_chunks} chunks indexed across ${status.files_indexed} documents`
                    : 'No documents indexed yet'
                }
                ok={Boolean(status.vector_store_chunks && status.vector_store_chunks > 0)}
              />
              <Row
                label="Hallucination Gate"
                value={`Threshold ${Math.round((status.eval_threshold ?? 0.6) * 100)}% · Claim-level source verification`}
                ok
              />
            </div>

            {status.missing_packages && status.missing_packages.length > 0 && (
              <div className="mt-4 rounded-xl border border-warning/35 bg-warningSoft/60 p-4 shadow-sm">
                <div className="flex items-center gap-2 text-[13px] font-semibold text-warning mb-1.5">
                  <Info size={14} />
                  Missing Optional Pipeline Packages
                </div>
                <p className="text-xs text-textMuted leading-relaxed mb-2.5">
                  Install requirements to enable full local RAG embeddings and chunking.
                </p>
                <div className="flex flex-wrap gap-1.5 mb-2.5">
                  {status.missing_packages.map((p) => (
                    <code
                      key={p}
                      className="text-[11px] font-mono px-2 py-0.5 rounded-md bg-background/80 border border-warning/30 text-textMain font-semibold"
                    >
                      {p}
                    </code>
                  ))}
                </div>
                <pre className="text-[11px] font-mono text-textMuted bg-background/80 border border-border/80 rounded-lg p-2.5 overflow-x-auto">
                  pip install -r requirements.txt
                </pre>
              </div>
            )}
          </Card>

          {/* Architecture info */}
          <Card title="System Architecture" icon={Info}>
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3 text-sm">
              <InfoLine icon={Cpu} label="Model runtime" value="Ollama (local on-device)" />
              <InfoLine icon={Database} label="Vector store" value="ChromaDB (local SQLite/HNSW)" />
              <InfoLine icon={ShieldCheck} label="Hallucination gate" value="Faithfulness score validation" />
              <InfoLine icon={Server} label="API layer" value="FastAPI + SSE streaming" />
              <InfoLine icon={ExternalLink} label="Frontend UI" value="React 19 + Vite 8 + Tailwind CSS v4" />
              <InfoLine icon={Monitor} label="Data privacy" value="100% local (data/ directory)" />
            </dl>
            <p className="text-xs text-textFaint mt-4 pt-3.5 border-t border-border/70 leading-relaxed">
              MentorOS is a private, single-user study tutor. No telemetry, no accounts, and no
              data is ever transmitted to cloud servers.
            </p>
          </Card>
        </motion.div>
      </div>
    </div>
  );
}

function Card({ title, icon: Icon, action, children }) {
  return (
    <motion.section
      variants={staggerItem}
      className="glass-card rounded-2xl overflow-hidden shadow-card"
    >
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-border/70 bg-panel/40">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-accentSoft text-accent flex items-center justify-center">
            <Icon size={14} />
          </div>
          <h2 className="text-[14px] font-bold text-textMain">{title}</h2>
        </div>
        {action}
      </div>
      <div className="p-5">{children}</div>
    </motion.section>
  );
}

function Row({ label, value, ok }) {
  return (
    <div className="flex items-center justify-between py-1 text-sm">
      <span className="text-textMuted font-medium text-[13px]">{label}</span>
      <div className="flex items-center gap-2">
        <span
          className="w-2 h-2 rounded-full"
          style={{
            background: ok ? 'var(--color-success)' : 'var(--color-warning)',
            boxShadow: `0 0 6px ${ok ? 'var(--color-success)' : 'var(--color-warning)'}`,
          }}
        />
        <span className="font-mono text-xs text-textMain font-medium">{value}</span>
      </div>
    </div>
  );
}

function InfoLine({ icon: Icon, label, value }) {
  return (
    <div className="flex items-start gap-2.5">
      <Icon size={15} className="text-accent flex-shrink-0 mt-0.5" />
      <div>
        <div className="text-[11.5px] font-medium text-textFaint uppercase tracking-wider">{label}</div>
        <div className="text-[13px] font-semibold text-textMain mt-0.5">{value}</div>
      </div>
    </div>
  );
}
