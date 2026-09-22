import React, { useEffect } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import AppShell from './components/shell/AppShell';
import ChatPage from './pages/ChatPage';
import DashboardPage from './pages/DashboardPage';
import DocumentsPage from './pages/DocumentsPage';
import PodcastPage from './pages/PodcastPage';
import SettingsPage from './pages/SettingsPage';
import ConfirmDialog from './components/ui/ConfirmDialog';
import PodcastModal from './components/PodcastModal';
import { useUI } from './stores/ui';
import { useStatus } from './stores/status';
import { useChat } from './stores/chat';
import { useFiles } from './stores/files';

export default function App() {
  const confirmState = useUI((s) => s.confirmState);
  const closeConfirm = useUI((s) => s.closeConfirm);
  const podcastModalOpen = useUI((s) => s.podcastModalOpen);
  const closePodcastModal = useUI((s) => s.closePodcastModal);
  const startPolling = useStatus((s) => s.startPolling);
  const loadSessions = useChat((s) => s.loadSessions);
  const loadFiles = useFiles((s) => s.load);

  useEffect(() => {
    const stop = startPolling();
    loadSessions();
    loadFiles();
    return () => stop?.();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <>
      <AppShell>
        <AnimatePresence mode="wait">
          <Routes>
            <Route path="/" element={<ChatPage />} />
            <Route path="/podcast" element={<PodcastPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/documents" element={<DocumentsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </AnimatePresence>
      </AppShell>
      <ConfirmDialog state={confirmState} onClose={closeConfirm} />
      <PodcastModal isOpen={podcastModalOpen} onClose={closePodcastModal} />
    </>
  );
}