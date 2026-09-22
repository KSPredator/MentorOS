import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Mic, Copy, Check, Clock, Radio, Volume2 } from 'lucide-react';
import { toast } from 'sonner';

/**
 * Enhanced podcast preview card with simulated audio wave visualizer and speaker turns.
 */
export default function PodcastCard({ script }) {
  const [copied, setCopied] = useState(false);
  const text = typeof script === 'string' ? script : script?.script || JSON.stringify(script, null, 2);
  const title = script?.title || 'Study Podcast Script';
  const minutes = Math.max(1, Math.round(text.split(/\s+/).length / 140));

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      toast.success('Script copied to clipboard');
      setTimeout(() => setCopied(false), 1500);
    } catch {
      toast.error('Copy failed');
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      className="glass-card rounded-2xl overflow-hidden shadow-card"
    >
      <div className="flex items-center gap-3 px-4.5 py-3.5 bg-accentSoft/60 border-b border-border/80">
        <div className="w-8.5 h-8.5 rounded-xl bg-gradient-to-tr from-accent to-sky-400 text-white flex items-center justify-center shadow-md shadow-accent/25">
          <Radio size={16} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="text-[13.5px] font-bold text-textMain truncate">{title}</div>
          <div className="flex items-center gap-2 text-[11px] text-textMuted mt-0.5">
            <span className="flex items-center gap-1">
              <Clock size={11} />
              ~{minutes} min discussion
            </span>
            <span>·</span>
            <span className="flex items-center gap-1 text-accent font-medium">
              <Volume2 size={11} />
              Two-host dialogue
            </span>
          </div>
        </div>

        {/* Animated wave bars mock */}
        <div className="hidden sm:flex items-center gap-1 px-2.5 py-1 rounded-lg bg-panel/60 border border-border/50">
          {[12, 20, 16, 24, 14, 22, 10].map((h, i) => (
            <motion.span
              key={i}
              className="w-1 bg-accent rounded-full"
              style={{ height: h }}
              animate={{ height: [h * 0.4, h, h * 0.5] }}
              transition={{ repeat: Infinity, duration: 1 + (i % 3) * 0.2, ease: 'easeInOut' }}
            />
          ))}
        </div>

        <button
          onClick={copy}
          className="flex items-center gap-1.5 text-[11.5px] font-medium px-3 py-1.5 rounded-lg
            border border-border/80 glass-panel text-textMuted hover:text-textMain hover:bg-panelHover transition-all cursor-pointer shadow-subtle"
        >
          {copied ? <Check size={12} className="text-success" /> : <Copy size={12} />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>

      <div className="p-4.5">
        <div className="text-[13.5px] leading-relaxed text-textMain/90 whitespace-pre-wrap max-h-80 overflow-y-auto answer-md pr-1">
          {text}
        </div>
        <div className="mt-3.5 pt-3 border-t border-border/70 flex items-center justify-between text-[11px] text-textFaint">
          <span className="flex items-center gap-1.5">
            <Mic size={11} className="text-accent" />
            Generated from your local knowledge documents
          </span>
          <span className="font-mono text-[10px]">Phase 12a</span>
        </div>
      </div>
    </motion.div>
  );
}
