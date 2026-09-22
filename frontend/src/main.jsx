import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { Toaster } from 'sonner';
import App from './App.jsx';
import { getMotionPreference } from './lib/useReducedMotion';
import './index.css';

// Apply persisted theme before first paint
function getInitialDark() {
  try {
    const raw = localStorage.getItem('mentoros-ui');
    if (raw) {
      const parsed = JSON.parse(raw);
      if (typeof parsed?.state?.dark === 'boolean') return parsed.state.dark;
    }
  } catch {
    /* ignore */
  }
  return false;
}

function applyTheme(dark) {
  if (dark) document.documentElement.classList.add('dark');
  else document.documentElement.classList.remove('dark');
}

function applyMotion() {
  document.documentElement.classList.toggle('motion-off', !getMotionPreference());
}

applyTheme(getInitialDark());
applyMotion();
window.addEventListener('mentoros:motion', applyMotion);

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: 'var(--color-elevated)',
            border: '1px solid var(--color-border)',
            color: 'var(--color-textMain)',
          },
        }}
      />
    </BrowserRouter>
  </React.StrictMode>,
);