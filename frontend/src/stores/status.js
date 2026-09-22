import { create } from 'zustand';
import { api } from '../api/client';

/** Global backend/system status — polled every 30s. */
export const useStatus = create((set, get) => ({
  loaded: false,
  ollama_available: false,
  model_name: null,
  pipeline_ready: false,
  missing_packages: [],
  vector_store_chunks: null,
  files_indexed: 0,
  eval_threshold: 0.6,
  api_version: '1.0',
  apiReachable: true,

  refresh: async () => {
    try {
      const s = await api.get('/api/status');
      set({ ...s, loaded: true, apiReachable: true });
      return s;
    } catch {
      set({ apiReachable: false, loaded: true, ollama_available: false });
      return null;
    }
  },

  startPolling: () => {
    const { refresh } = get();
    refresh();
    const id = setInterval(() => get().refresh(), 30000);
    return () => clearInterval(id);
  },
}));
