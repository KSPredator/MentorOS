import React from 'react';

/**
 * Lightweight, high-performance ambient watercolor atmosphere background.
 * Provides subtle, soft color fields with zero GPU/CPU lag or frame drops.
 */
export default function WatercolorBackground({
  variant = 'default',
  className = '',
}) {
  const isSubtle = variant === 'subtle';

  return (
    <div
      aria-hidden="true"
      className={`pointer-events-none fixed inset-0 z-0 overflow-hidden select-none ${className}`}
    >
      <div className="relative w-full h-full">
        {/* Sky Cyan & Blue Ambient Glow */}
        <div
          className="absolute rounded-full opacity-65 dark:opacity-25"
          style={{
            top: isSubtle ? '-8%' : '-2%',
            left: isSubtle ? '6%' : '3%',
            width: isSubtle ? '45vw' : '52vw',
            height: isSubtle ? '45vw' : '52vw',
            maxWidth: '650px',
            maxHeight: '650px',
            background:
              'radial-gradient(circle, rgba(14, 165, 233, 0.15) 0%, rgba(56, 189, 248, 0.06) 45%, transparent 70%)',
          }}
        />

        {/* Mint / Emerald Ambient Glow */}
        <div
          className="absolute rounded-full opacity-60 dark:opacity-20"
          style={{
            top: isSubtle ? '-4%' : '2%',
            right: isSubtle ? '4%' : '2%',
            width: isSubtle ? '40vw' : '48vw',
            height: isSubtle ? '40vw' : '48vw',
            maxWidth: '600px',
            maxHeight: '600px',
            background:
              'radial-gradient(circle, rgba(52, 211, 153, 0.13) 0%, rgba(16, 185, 129, 0.05) 45%, transparent 70%)',
          }}
        />

        {/* Lavender / Violet Ambient Glow */}
        {!isSubtle && (
          <div
            className="absolute rounded-full opacity-60 dark:opacity-20"
            style={{
              bottom: '0%',
              left: '5%',
              width: '46vw',
              height: '46vw',
              maxWidth: '580px',
              maxHeight: '580px',
              background:
                'radial-gradient(circle, rgba(167, 139, 250, 0.14) 0%, rgba(139, 92, 246, 0.05) 45%, transparent 70%)',
            }}
          />
        )}

        {/* Warm Amber / Peach Ambient Glow */}
        <div
          className="absolute rounded-full opacity-55 dark:opacity-15"
          style={{
            bottom: isSubtle ? '-5%' : '0%',
            right: isSubtle ? '6%' : '4%',
            width: isSubtle ? '38vw' : '44vw',
            height: isSubtle ? '38vw' : '44vw',
            maxWidth: '550px',
            maxHeight: '550px',
            background:
              'radial-gradient(circle, rgba(251, 146, 60, 0.12) 0%, rgba(244, 114, 182, 0.04) 45%, transparent 70%)',
          }}
        />
      </div>
    </div>
  );
}
