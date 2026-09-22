import React, { useId } from 'react';

/** Animated confidence arc (SVG) with gradient stroke and glow. `score` is 0..1. */
export default function ConfidenceMeter({ score = 0, size = 64, showLabel = true }) {
  const clamped = Math.max(0, Math.min(1, score || 0));
  const gradientId = useId();
  const r = size / 2 - 6;
  const circumference = 2 * Math.PI * r;
  // 270° arc (3/4 circle) for a gauge look
  const arcLen = circumference * 0.75;
  const offset = arcLen * (1 - clamped);

  const isHigh = clamped >= 0.7;
  const isMed = clamped >= 0.4 && clamped < 0.7;

  const colorStart = isHigh ? '#10b981' : isMed ? '#f59e0b' : '#ef4444';
  const colorEnd = isHigh ? '#34d399' : isMed ? '#fbbf24' : '#f87171';
  const glowColor = isHigh
    ? 'rgba(16, 185, 129, 0.25)'
    : isMed
      ? 'rgba(245, 158, 11, 0.25)'
      : 'rgba(239, 68, 68, 0.25)';

  const pctStr = `${Math.round(clamped * 100)}%`;

  return (
    <div
      className="relative inline-flex items-center justify-center flex-shrink-0"
      style={{ width: size, height: size }}
    >
      <svg width={size} height={size} style={{ transform: 'rotate(135deg)' }} aria-hidden="true">
        <defs>
          <linearGradient id={gradientId} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={colorStart} />
            <stop offset="100%" stopColor={colorEnd} />
          </linearGradient>
        </defs>

        {/* Track */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="var(--color-borderStrong)"
          strokeWidth={5}
          strokeDasharray={`${arcLen} ${circumference}`}
          strokeLinecap="round"
          opacity={0.35}
        />

        {/* Active Arc */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={`url(#${gradientId})`}
          strokeWidth={5}
          strokeDasharray={`${arcLen} ${circumference}`}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{
            transition: 'stroke-dashoffset 0.9s cubic-bezier(0.22,1,0.36,1), stroke 0.4s',
            filter: `drop-shadow(0 0 6px ${glowColor})`,
          }}
        />
      </svg>
      {showLabel && (
        <span
          className="absolute font-display text-[13px] font-bold tracking-tight"
          style={{ color: colorStart }}
        >
          {pctStr}
        </span>
      )}
    </div>
  );
}
