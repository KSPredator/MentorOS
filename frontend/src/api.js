/**
 * MentorOS API service layer.
 * All calls go to the FastAPI backend at http://localhost:8000.
 */

const BASE_URL = 'http://localhost:8000';

async function req(method, path, body, signal) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
    signal,
  };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const res = await fetch(`${BASE_URL}${path}`, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `API error ${res.status}`);
  }
  return res.json();
}

// ── Status ──────────────────────────────────────────────────────────────────
export const getStatus = () => req('GET', '/status');

// ── Upload ───────────────────────────────────────────────────────────────────
export async function uploadFile(file, sessionId = 'default') {
  const form = new FormData();
  form.append('file', file);
  form.append('session_id', sessionId);
  const res = await fetch(`${BASE_URL}/upload`, { method: 'POST', body: form });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Upload error ${res.status}`);
  }
  return res.json();
}

// ── Ask (JSON) ────────────────────────────────────────────────────────────────
export const ask = (question, sessionId = 'default', topK = 5) =>
  req('POST', '/ask', { question, session_id: sessionId, top_k: topK });

// ── Ask (SSE stream) ─────────────────────────────────────────────────────────
/**
 * Returns a ReadableStream of parsed SSE events.
 * Each event is one of:
 *   { type: 'planner', action, reasoning }
 *   { type: 'token',   token }
 *   { type: 'done',    session_id }
 */
export async function askStream(question, sessionId = 'default', signal) {
  const res = await fetch(`${BASE_URL}/ask/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, session_id: sessionId }),
    signal,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `Stream error ${res.status}`);
  }
  return res.body; // ReadableStream<Uint8Array>
}

// ── History ───────────────────────────────────────────────────────────────────
export const getHistory = (sessionId = 'default', limit = 100) =>
  req('GET', `/history?session_id=${encodeURIComponent(sessionId)}&limit=${limit}`);

export const deleteHistory = (sessionId = 'default') =>
  req('DELETE', `/history?session_id=${encodeURIComponent(sessionId)}`);

// ── Memory ────────────────────────────────────────────────────────────────────
export const getMemory = (sessionId = 'default') =>
  req('GET', `/memory?session_id=${encodeURIComponent(sessionId)}`);

export const getWeakTopics = (sessionId = 'default', n = 5) =>
  req('GET', `/memory/weak?session_id=${encodeURIComponent(sessionId)}&n=${n}`);

// ── Reflection ────────────────────────────────────────────────────────────────
export const getReflection = (sessionId = 'default') =>
  req('GET', `/reflection?session_id=${encodeURIComponent(sessionId)}`);
