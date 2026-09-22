import { useEffect, useState } from 'react';

const KEY = 'mentoros.motion';

function readPref() {
  if (typeof window === 'undefined' || !window.localStorage) return false;
  return window.localStorage.getItem(KEY) === 'off';
}

/**
 * Animations are enabled unless the user explicitly turns them off in
 * Settings ("Motion"), which overrides the OS `prefers-reduced-motion`
 * preference (this app ships animation-first by design).
 */
export default function useReducedMotion() {
  const [reduced, setReduced] = useState(readPref);

  useEffect(() => {
    const sync = () => setReduced(readPref());
    window.addEventListener('mentoros:motion', sync);
    window.addEventListener('storage', sync);
    return () => {
      window.removeEventListener('mentoros:motion', sync);
      window.removeEventListener('storage', sync);
    };
  }, []);

  return reduced;
}

export function getMotionPreference() {
  if (typeof window === 'undefined' || !window.localStorage) return true;
  return window.localStorage.getItem(KEY) !== 'off';
}

export function setMotionPreference(enabled) {
  if (typeof window === 'undefined' || !window.localStorage) return;
  window.localStorage.setItem(KEY, enabled ? 'on' : 'off');
  window.dispatchEvent(new Event('mentoros:motion'));
}