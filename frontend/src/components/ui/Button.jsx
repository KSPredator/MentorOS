import React from 'react';
import { motion } from 'framer-motion';
import { hoverTap } from '../../lib/variants';

const variants = {
  primary:
    'bg-accent text-white hover:bg-accentDim shadow-md shadow-accent/25 hover:shadow-lg hover:shadow-accent/35 border border-transparent',
  secondary:
    'bg-panel text-textMain border border-border/80 hover:border-accent/40 hover:bg-panelHover shadow-subtle',
  ghost:
    'bg-transparent text-textMuted border border-transparent hover:text-textMain hover:bg-panelHover',
  danger:
    'bg-dangerSoft text-danger border border-danger/30 hover:bg-danger/20 shadow-subtle',
};

/**
 * Minimal button with micro-interactions and smooth spring states.
 */
export default function Button({
  variant = 'secondary',
  size = 'md',
  className = '',
  children,
  ...props
}) {
  const sizes = {
    sm: 'text-xs px-3 py-1.5 rounded-lg gap-1.5',
    md: 'text-[13px] font-semibold px-4 py-2 rounded-xl gap-2',
    lg: 'text-sm font-semibold px-5 py-2.5 rounded-xl gap-2',
    icon: 'p-2 rounded-lg',
  };
  return (
    <motion.button
      {...hoverTap}
      className={`inline-flex items-center justify-center transition-all duration-150 cursor-pointer
        disabled:opacity-40 disabled:pointer-events-none select-none
        ${variants[variant] || variants.secondary} ${sizes[size] || sizes.md} ${className}`}
      {...props}
    >
      {children}
    </motion.button>
  );
}
