import { create } from 'zustand';
import { persist } from 'zustand/middleware';

/** UI store — theme, panels, modal state. Theme persisted to localStorage. */
export const useUI = create(
  persist(
    (set, get) => ({
      dark: false, // Default to clean, beautiful Light Mode
      sidebarOpen: false, // mobile
      filePanelOpen: false, // mobile + desktop collapsible
      chunkModalId: null,
      podcastModalOpen: false,
      confirmState: null, // { title, message, onConfirm }

      toggleDark: () => {
        const dark = !get().dark;
        set({ dark });
        applyTheme(dark);
      },

      setDark: (dark) => {
        set({ dark });
        applyTheme(dark);
      },

      setSidebar: (open) => set({ sidebarOpen: open }),
      toggleFilePanel: () => set((s) => ({ filePanelOpen: !s.filePanelOpen })),
      setFilePanel: (open) => set({ filePanelOpen: open }),

      openChunk: (chunkId) => set({ chunkModalId: chunkId }),
      closeChunk: () => set({ chunkModalId: null }),

      openPodcastModal: () => set({ podcastModalOpen: true }),
      closePodcastModal: () => set({ podcastModalOpen: false }),

      confirm: (opts) => set({ confirmState: opts }),
      closeConfirm: () => set({ confirmState: null }),
    }),
    {
      name: 'mentoros-ui',
      partialize: (s) => ({ dark: s.dark, filePanelOpen: s.filePanelOpen }),
    },
  ),
);

export function applyTheme(dark) {
  if (dark) document.documentElement.classList.add('dark');
  else document.documentElement.classList.remove('dark');
}
