import React from 'react';
import { motion } from 'framer-motion';
import { fadeInUp } from '../../lib/variants';

/**
 * Empty state with an abstract SVG illustration slot, heading, body, CTA.
 * Deliberately custom-drawn to avoid generic clipart look.
 */
export default function EmptyState({ title, body, action, icon: Icon, compact = false }) {
  return (
    <motion.div
      {...fadeInUp}
      className={`flex flex-col items-center justify-center text-center px-6 ${
        compact ? 'py-8' : 'py-14'
      }`}
    >
      <div className="relative mb-4">
        <div className="absolute inset-0 bg-accent/20 blur-2xl rounded-full" aria-hidden="true" />
        <div className="relative w-15 h-15 rounded-2xl bg-panel border border-border/80 flex items-center justify-center text-accent shadow-sm">
          {Icon ? <Icon size={24} strokeWidth={1.75} /> : <DefaultGlyph />}
        </div>
      </div>
      <h3 className="font-display font-bold text-[16px] text-textMain mb-1.5">{title}</h3>
      {body && (
        <p className="text-sm text-textMuted max-w-sm leading-relaxed mb-4">{body}</p>
      )}
      {action}
    </motion.div>
  );
}

function DefaultGlyph() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden="true">
      <circle cx="12" cy="12" r="3" stroke="currentColor" strokeWidth="1.6" />
      <circle cx="12" cy="4" r="1.6" fill="currentColor" opacity="0.8" />
      <circle cx="12" cy="20" r="1.6" fill="currentColor" opacity="0.8" />
      <circle cx="4" cy="8" r="1.6" fill="currentColor" opacity="0.6" />
      <circle cx="20" cy="8" r="1.6" fill="currentColor" opacity="0.6" />
      <path d="M12 9V5.6M12 14.4V18M9.4 10.5 5.8 8.7M14.6 10.5l3.6-1.8" stroke="currentColor" strokeWidth="1.2" opacity="0.5" />
    </svg>
  );
}
