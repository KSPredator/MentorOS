import { create } from 'zustand';
import { api } from '../api/client';
import { useStatus } from './status';

/** Files store: list, per-file upload progress, CRUD. */
export const useFiles = create((set, get) => ({
  files: [],
  loaded: false,
  /** filename -> 0..1 upload progress (only while uploading) */
  uploading: {},

  load: async () => {
    try {
      const files = await api.get('/api/files');
      set({ files, loaded: true });
    } catch {
      set({ loaded: true });
    }
  },

  upload: async (file) => {
    const name = file.name;
    set((s) => ({ uploading: { ...s.uploading, [name]: 0 } }));
    try {
      const result = await api.upload('/api/files/upload', file, (p) => {
        set((s) => ({ uploading: { ...s.uploading, [name]: p } }));
      });
      await get().load();
      useStatus.getState().refresh();
      return { ok: true, file: result };
    } catch (e) {
      await get().load(); // pick up a 'failed' row if server recorded one
      return { ok: false, error: e.detail || e.message || 'Upload failed' };
    } finally {
      set((s) => {
        const next = { ...s.uploading };
        delete next[name];
        return { uploading: next };
      });
    }
  },

  remove: async (filename) => {
    await api.del(`/api/files/${encodeURIComponent(filename)}`);
    await get().load();
    useStatus.getState().refresh();
  },

  removeAll: async () => {
    await api.del('/api/files');
    await get().load();
    useStatus.getState().refresh();
  },
}));
