import { useState, useCallback } from 'react';

const STORAGE_KEY = 'mentoros_session_id';

function generateUUID() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) {
    return crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

function getOrCreateSessionId() {
  let id = localStorage.getItem(STORAGE_KEY);
  if (!id) {
    id = generateUUID();
    localStorage.setItem(STORAGE_KEY, id);
  }
  return id;
}

/**
 * Manages the current session ID.
 * - Persists across page refreshes via localStorage.
 * - `rotate()` generates a new UUID for "New Chat".
 */
export function useSession() {
  const [sessionId, setSessionId] = useState(() => getOrCreateSessionId());

  const rotate = useCallback(() => {
    const newId = generateUUID();
    localStorage.setItem(STORAGE_KEY, newId);
    setSessionId(newId);
    return newId;
  }, []);

  return { sessionId, rotate };
}

