import React, { useState, useEffect, useCallback } from 'react';
import { Menu, FileText } from 'lucide-react';
import Sidebar from './components/Sidebar';
import CenterArea from './components/CenterArea';
import FilePanel from './components/FilePanel';
import MemoryPanel from './components/MemoryPanel';
import { useSession } from './useSession';
import { useChatStore } from './useChatStore';
import { getStatus } from './api';

function App() {
  const [isSidebarOpen, setSidebarOpen] = useState(false);
  const [isFilePanelOpen, setFilePanelOpen] = useState(false);
  const [isMemoryOpen, setMemoryOpen] = useState(false);
  const [isDarkMode, setIsDarkMode] = useState(true);
  const [modelName, setModelName] = useState('');
  const [sidebarRefresh, setSidebarRefresh] = useState(0);

  const { sessionId, rotate: rotateSession } = useSession();
  const { messages, isLoading, sendMessage, clearMessages } = useChatStore(sessionId);

  // Apply dark mode class
  useEffect(() => {
    document.documentElement.classList.toggle('dark', isDarkMode);
  }, [isDarkMode]);

  // Fetch model name on mount
  useEffect(() => {
    getStatus()
      .then(s => setModelName(s.ollama_model || ''))
      .catch(() => {});
  }, []);

  // After each message exchange, refresh sidebar history
  useEffect(() => {
    if (!isLoading && messages.length > 0) {
      setSidebarRefresh(n => n + 1);
    }
  }, [isLoading, messages.length]);

  const handleNewChat = useCallback(() => {
    rotateSession();
    clearMessages();
    setSidebarOpen(false);
    setSidebarRefresh(n => n + 1);
  }, [rotateSession, clearMessages]);

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Mobile top bar */}
      <div className="md:hidden flex items-center justify-between p-4 bg-panel border-b border-gray-200 dark:border-gray-800 absolute top-0 w-full z-20">
        <button id="mobile-sidebar-btn" onClick={() => setSidebarOpen(!isSidebarOpen)} className="p-2 text-textMuted hover:text-white">
          <Menu size={24} />
        </button>
        <div className="font-semibold text-lg tracking-wide">MentorOS</div>
        <button id="mobile-filepanel-btn" onClick={() => setFilePanelOpen(!isFilePanelOpen)} className="p-2 text-textMuted hover:text-white">
          <FileText size={24} />
        </button>
      </div>

      {/* Sidebar */}
      <div className={`fixed inset-y-0 left-0 z-10 transform ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'} md:relative md:translate-x-0 transition duration-200 ease-in-out md:flex md:w-[260px] md:flex-shrink-0 bg-panel border-r border-gray-200 dark:border-gray-800`}>
        <Sidebar
          sessionId={sessionId}
          onNewChat={handleNewChat}
          isDarkMode={isDarkMode}
          toggleDarkMode={() => setIsDarkMode(d => !d)}
          onOpenMemory={() => { setMemoryOpen(true); setSidebarOpen(false); }}
          refreshTrigger={sidebarRefresh}
        />
      </div>

      {/* Mobile overlay */}
      {(isSidebarOpen || isFilePanelOpen) && (
        <div
          className="fixed inset-0 bg-black/50 z-0 md:hidden"
          onClick={() => { setSidebarOpen(false); setFilePanelOpen(false); }}
        />
      )}

      {/* Center area */}
      <div className="flex-1 flex flex-col min-w-0 md:pt-0 pt-16 h-full relative">
        <CenterArea
          messages={messages}
          isLoading={isLoading}
          sendMessage={sendMessage}
          onOpenFilePanel={() => setFilePanelOpen(true)}
          modelName={modelName}
        />
      </div>

      {/* File panel */}
      <div className={`fixed inset-y-0 right-0 z-10 transform ${isFilePanelOpen ? 'translate-x-0' : 'translate-x-full'} md:relative md:translate-x-0 transition duration-200 ease-in-out md:flex md:w-[300px] md:flex-shrink-0 bg-panel border-l border-gray-200 dark:border-gray-800`}>
        <FilePanel sessionId={sessionId} />
      </div>

      {/* Memory/Progress drawer (global) */}
      <MemoryPanel
        sessionId={sessionId}
        isOpen={isMemoryOpen}
        onClose={() => setMemoryOpen(false)}
      />
    </div>
  );
}

export default App;
