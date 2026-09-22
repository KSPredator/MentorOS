import React from 'react';
import { useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import Sidebar from './Sidebar';
import FilePanel from './FilePanel';
import MobileNav from './MobileNav';
import WatercolorBackground from '../ui/WatercolorBackground';
import { useUI } from '../../stores/ui';
import { useStatus } from '../../stores/status';

/** Three-column app frame: Sidebar | main | FilePanel. Mobile gets a top bar + drawer. */
export default function AppShell({ children }) {
  const sidebarOpen = useUI((s) => s.sidebarOpen);
  const setSidebar = useUI((s) => s.setSidebar);
  const apiReachable = useStatus((s) => s.apiReachable);
  const location = useLocation();

  const isRichBackground =
    location.pathname === '/' ||
    location.pathname.startsWith('/chat') ||
    location.pathname === '/dashboard';

  return (
    <div className="h-screen w-screen overflow-hidden flex flex-col bg-background text-textMain relative">
      <WatercolorBackground variant={isRichBackground ? 'default' : 'subtle'} />
      {!apiReachable && <OfflineBanner />}
      <MobileNav />
      <div className="flex flex-1 min-h-0">
        <Sidebar />

        {/* Mobile sidebar drawer */}
        {sidebarOpen && (
          <>
            <div
              className="fixed inset-0 z-40 bg-black/50 backdrop-blur-sm md:hidden"
              onClick={() => setSidebar(false)}
              aria-hidden
            />
            <motion.div
              initial={{ x: -260 }}
              animate={{ x: 0 }}
              transition={{ type: 'spring', stiffness: 380, damping: 34 }}
              className="fixed inset-y-0 left-0 z-50 md:hidden shadow-pop"
            >
              <Sidebar />
            </motion.div>
          </>
        )}

        <main
          key={location.pathname}
          className="flex-1 min-w-0 h-full overflow-hidden flex flex-col relative z-0"
        >
          {children}
        </main>

        <FilePanel />
      </div>
    </div>
  );
}

function OfflineBanner() {
  return (
    <div className="bg-dangerSoft border-b border-danger/30 text-danger text-xs px-4 py-2 text-center font-medium">
      Backend unreachable — start it with{' '}
      <code className="font-mono bg-danger/10 px-1.5 py-0.5 rounded">
        uvicorn api.main:app --reload --port 8000
      </code>
    </div>
  );
}
