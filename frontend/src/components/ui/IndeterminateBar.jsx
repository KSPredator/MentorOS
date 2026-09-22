import React from 'react';

/** Indeterminate progress line (uploading / processing states). */
export default function IndeterminateBar({ color = 'var(--color-accent)', height = 3 }) {
  return (
    <div
      className="w-full overflow-hidden rounded-full bg-panelHover"
      style={{ height }}
      aria-hidden
    >
      <div
        className="progress-indeterminate h-full w-1/4 rounded-full"
        style={{ background: color }}
      />
    </div>
  );
}
