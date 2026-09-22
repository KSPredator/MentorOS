import React, { useState, useCallback, useEffect } from 'react';
import { X, BarChart2, Loader2, Sparkles, AlertTriangle, TrendingUp, TrendingDown, BookOpen } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { getMemory, getReflection } from '../api';

function TopicBar({ topic, confidence }) {
  const pct = Math.round(confidence * 100);
  const color = pct >= 70 ? 'bg-emerald-500' : pct >= 40 ? 'bg-amber-500' : 'bg-red-500';
  return (
    <div className="mb-3">
      <div className="flex justify-between items-center mb-1">
        <span className="text-sm text-gray-800 dark:text-gray-200 capitalize">{topic}</span>
        <span className="text-xs text-gray-500 tabular-nums">{pct}%</span>
      </div>
      <div className="w-full h-2 bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
        <motion.div
          className={`h-full rounded-full ${color}`}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        />
      </div>
    </div>
  );
}

export default function MemoryPanel({ sessionId, isOpen, onClose }) {
  const [memory, setMemory] = useState(null);
  const [reflection, setReflection] = useState(null);
  const [loadingMemory, setLoadingMemory] = useState(false);
  const [loadingReflection, setLoadingReflection] = useState(false);
  const [reflectionError, setReflectionError] = useState('');

  const loadMemory = useCallback(async () => {
    if (!isOpen) return;
    setLoadingMemory(true);
    try {
      const data = await getMemory(sessionId);
      setMemory(data);
    } catch { /* silent */ }
    finally { setLoadingMemory(false); }
  }, [sessionId, isOpen]);

  useEffect(() => { loadMemory(); }, [loadMemory]);

  const handleReflection = useCallback(async () => {
    setLoadingReflection(true);
    setReflectionError('');
    setReflection(null);
    try {
      const data = await getReflection(sessionId);
      setReflection(data);
    } catch (e) {
      setReflectionError(e.message);
    } finally {
      setLoadingReflection(false);
    }
  }, [sessionId]);

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/50 z-30"
          />

          {/* Drawer */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', stiffness: 320, damping: 35 }}
            className="fixed right-0 top-0 bottom-0 w-full max-w-md bg-white dark:bg-gray-950 border-l border-gray-200 dark:border-gray-800 z-40 flex flex-col shadow-2xl"
          >
            {/* Header */}
            <div className="flex items-center justify-between p-5 border-b border-gray-200 dark:border-gray-800 flex-shrink-0">
              <div className="flex items-center gap-2">
                <BarChart2 size={20} className="text-accent" />
                <h2 className="font-semibold text-lg">Learning Progress</h2>
              </div>
              <button
                id="close-memory-btn"
                onClick={onClose}
                className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-500 transition-colors"
              >
                <X size={18} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-6">
              {loadingMemory ? (
                <div className="flex items-center justify-center h-32 text-gray-400">
                  <Loader2 size={24} className="animate-spin" />
                </div>
              ) : !memory || memory.topic_count === 0 ? (
                <div className="text-center text-sm text-gray-500 py-12">
                  <BookOpen size={32} className="mx-auto mb-3 opacity-30" />
                  No topics tracked yet.<br />Ask some questions to see your progress.
                </div>
              ) : (
                <>
                  {/* Stats row */}
                  <div className="grid grid-cols-3 gap-3">
                    {[
                      { label: 'Topics', value: memory.topic_count },
                      { label: 'Strong', value: memory.strong_topics?.length ?? 0, color: 'text-emerald-500' },
                      { label: 'Weak', value: memory.weak_topics?.length ?? 0, color: 'text-red-400' },
                    ].map(({ label, value, color }) => (
                      <div key={label} className="bg-gray-50 dark:bg-gray-900 rounded-xl p-3 text-center border border-gray-200 dark:border-gray-800">
                        <p className={`text-2xl font-bold ${color || ''}`}>{value}</p>
                        <p className="text-xs text-gray-500 mt-0.5">{label}</p>
                      </div>
                    ))}
                  </div>

                  {/* Strong topics */}
                  {memory.strong_topics?.length > 0 && (
                    <div>
                      <div className="flex items-center gap-2 mb-3">
                        <TrendingUp size={14} className="text-emerald-500" />
                        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500">Strong Topics</h3>
                      </div>
                      {memory.topics
                        .filter(t => memory.strong_topics.includes(t.topic))
                        .map(t => <TopicBar key={t.topic} topic={t.topic} confidence={t.confidence} />)}
                    </div>
                  )}

                  {/* Weak topics */}
                  {memory.weak_topics?.length > 0 && (
                    <div>
                      <div className="flex items-center gap-2 mb-3">
                        <TrendingDown size={14} className="text-red-400" />
                        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500">Needs Revision</h3>
                      </div>
                      {memory.topics
                        .filter(t => memory.weak_topics.includes(t.topic))
                        .map(t => <TopicBar key={t.topic} topic={t.topic} confidence={t.confidence} />)}
                    </div>
                  )}

                  {/* All other topics */}
                  {(() => {
                    const tracked = new Set([...(memory.strong_topics || []), ...(memory.weak_topics || [])]);
                    const rest = memory.topics.filter(t => !tracked.has(t.topic));
                    if (!rest.length) return null;
                    return (
                      <div>
                        <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-500 mb-3">All Topics</h3>
                        {rest.map(t => <TopicBar key={t.topic} topic={t.topic} confidence={t.confidence} />)}
                      </div>
                    );
                  })()}
                </>
              )}

              {/* Reflection */}
              <div className="border-t border-gray-200 dark:border-gray-800 pt-5">
                <button
                  id="generate-reflection-btn"
                  onClick={handleReflection}
                  disabled={loadingReflection}
                  className="flex items-center justify-center gap-2 w-full bg-accent hover:bg-accent/90 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-xl py-3 px-4 font-medium transition-colors shadow-lg shadow-accent/20"
                >
                  {loadingReflection
                    ? <><Loader2 size={16} className="animate-spin" /> Generating reflection…</>
                    : <><Sparkles size={16} /> Generate Session Reflection</>
                  }
                </button>

                {reflectionError && (
                  <div className="mt-3 flex gap-2 text-xs text-red-500 bg-red-500/10 rounded-lg p-3">
                    <AlertTriangle size={13} className="mt-0.5 flex-shrink-0" />
                    {reflectionError}
                  </div>
                )}

                {reflection && (
                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="mt-4 space-y-4"
                  >
                    <div className="bg-gray-50 dark:bg-gray-900/80 border border-gray-200 dark:border-gray-800 rounded-xl p-4">
                      <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{reflection.full_summary}</p>
                    </div>

                    {reflection.needs_revision?.length > 0 && (
                      <div>
                        <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Focus next session on:</p>
                        <ul className="space-y-1">
                          {reflection.needs_revision.map(t => (
                            <li key={t} className="text-sm text-amber-600 dark:text-amber-400 flex items-center gap-2">
                              <span className="w-1.5 h-1.5 rounded-full bg-amber-400 flex-shrink-0" />
                              {t}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    <div className="bg-accent/5 border border-accent/20 rounded-xl p-4">
                      <p className="text-xs font-semibold text-accent mb-1">Recommended Next Session</p>
                      <p className="text-sm text-gray-700 dark:text-gray-300 leading-relaxed">{reflection.recommended_session}</p>
                    </div>
                  </motion.div>
                )}
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
