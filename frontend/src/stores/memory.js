import { create } from 'zustand';
import { api } from '../api/client';

/** Memory + reflection store for the dashboard. */
export const useMemory = create((set, get) => ({
  snapshot: null,
  reflection: null,
  loading: false,
  reflecting: false,
  error: null,

  load: async (sessionId) => {
    set({ loading: true, error: null });
    try {
      const qs = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : '';
      const snapshot = await api.get(`/api/memory${qs}`);
      set({ snapshot, loading: false });
    } catch (e) {
      set({ loading: false, error: e.detail || 'Failed to load memory' });
    }
  },

  reflect: async (sessionId) => {
    set({ reflecting: true, error: null });
    try {
      const reflection = await api.post('/api/reflection', {
        session_id: sessionId || null,
      });
      set({ reflection, reflecting: false });
      return reflection;
    } catch (e) {
      set({ reflecting: false, error: e.detail || 'Reflection failed' });
      throw e;
    }
  },

  reset: async (sessionId) => {
    if (!sessionId) throw new Error('session_id required');
    await api.del(`/api/memory?session_id=${encodeURIComponent(sessionId)}`);
    await get().load(sessionId);
  },

  clearReflection: () => set({ reflection: null }),
}));
