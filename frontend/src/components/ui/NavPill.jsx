import React from 'react';
import { motion } from 'framer-motion';
import { hoverTap } from '../../lib/variants';

/** Pill-style navigation link for the sidebar. */
export default function NavPill({ icon: Icon, label, active, onClick, badge }) {
  return (
    <motion.button
      {...hoverTap}
      onClick={onClick}
      className={`relative w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-sm transition-colors text-left
        ${
          active
            ? 'text-accent font-medium'
            : 'text-textMuted hover:text-textMain hover:bg-panelHover'
        }`}
      aria-current={active ? 'page' : undefined}
    >
      {active && (
        <motion.span
          layoutId="nav-pill"
          className="absolute inset-0 rounded-xl bg-accentSoft border border-accent/25"
          transition={{ type: 'spring', stiffness: 400, damping: 32 }}
        />
      )}
      <span className="relative z-10 flex items-center gap-2.5 w-full">
        {Icon && <Icon size={16} strokeWidth={active ? 2.1 : 1.8} />}
        <span className="flex-1 truncate">{label}</span>
        {badge != null && badge > 0 && (
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-md bg-panelHover border border-border text-textMuted">
            {badge}
          </span>
        )}
      </span>
    </motion.button>
  );
}
