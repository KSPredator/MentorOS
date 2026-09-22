import React from 'react';

/**
 * Animated count-up number hook.
 * Triggers whenever `value` changes; uses rAF for smooth interpolation.
 */
import { useEffect, useRef, useState } from 'react';

export function useCountUp(value, duration = 700) {
  const [display, setDisplay] = useState(0);
  const fromRef = useRef(0);
  const rafRef = useRef(0);

  useEffect(() => {
    const from = fromRef.current;
    const to = typeof value === 'number' && !Number.isNaN(value) ? value : 0;
    if (from === to) return undefined;
    const start = performance.now();
    const step = (now) => {
      const t = Math.min(1, (now - start) / duration);
      const eased = 1 - Math.pow(1 - t, 3);
      const current = from + (to - from) * eased;
      setDisplay(current);
      if (t < 1) {
        rafRef.current = requestAnimationFrame(step);
      } else {
        fromRef.current = to;
      }
    };
    rafRef.current = requestAnimationFrame(step);
    return () => cancelAnimationFrame(rafRef.current);
  }, [value, duration]);

  return display;
}

export default useCountUp;
