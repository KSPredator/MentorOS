import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import CenterArea from './components/CenterArea';
import FilePanel from './components/FilePanel';
import { Menu, FileText } from 'lucide-react';

function App() {
  const [isSidebarOpen, setSidebarOpen] = useState(false);
  const [isFilePanelOpen, setFilePanelOpen] = useState(false);
  const [activeChat, setActiveChat] = useState(null); // null means "New Chat"
  const [isDarkMode, setIsDarkMode] = useState(true);

  useEffect(() => {
    if (isDarkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDarkMode]);

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Mobile Top Bar */}
      <div className="md:hidden flex items-center justify-between p-4 bg-panel border-b border-gray-200 dark:border-gray-800 absolute top-0 w-full z-20">
        <button onClick={() => setSidebarOpen(!isSidebarOpen)} className="p-2 text-textMuted hover:text-white">
          <Menu size={24} />
        </button>
        <div className="font-semibold text-lg tracking-wide">MentorOS</div>
        <button onClick={() => setFilePanelOpen(!isFilePanelOpen)} className="p-2 text-textMuted hover:text-white">
          <FileText size={24} />
        </button>
      </div>

      {/* Sidebar */}
      <div className={`fixed inset-y-0 left-0 z-10 transform ${isSidebarOpen ? 'translate-x-0' : '-translate-x-full'} md:relative md:translate-x-0 transition duration-200 ease-in-out md:flex md:w-[260px] md:flex-shrink-0 bg-panel border-r border-gray-200 dark:border-gray-800`}>
        <Sidebar 
          onNewChat={() => { setActiveChat(null); setSidebarOpen(false); }} 
          onSelectChat={(chat) => { setActiveChat(chat); setSidebarOpen(false); }} 
          isDarkMode={isDarkMode}
          toggleDarkMode={() => setIsDarkMode(!isDarkMode)}
        />
      </div>

      {/* Overlay for mobile */}
      {(isSidebarOpen || isFilePanelOpen) && (
        <div 
          className="fixed inset-0 bg-black/50 z-0 md:hidden" 
          onClick={() => { setSidebarOpen(false); setFilePanelOpen(false); }}
        />
      )}

      {/* Center Area */}
      <div className="flex-1 flex flex-col min-w-0 md:pt-0 pt-16 h-full relative">
        <CenterArea activeChat={activeChat} />
      </div>

      {/* File Panel */}
      <div className={`fixed inset-y-0 right-0 z-10 transform ${isFilePanelOpen ? 'translate-x-0' : 'translate-x-full'} md:relative md:translate-x-0 transition duration-200 ease-in-out md:flex md:w-[300px] md:flex-shrink-0 bg-panel border-l border-gray-200 dark:border-gray-800`}>
        <FilePanel />
      </div>
    </div>
  );
}

export default App;
