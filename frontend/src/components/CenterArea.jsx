import React from 'react';
import { Send, Paperclip, ChevronRight, Activity, Zap, Brain, Sparkles, BookOpen } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

function NewChatHero() {
  const suggestions = [
    "Summarize this PDF",
    "Quiz me on Chapter 3",
    "Explain simply",
    "Find key arguments"
  ];

  return (
    <div className="flex flex-col items-center justify-center h-full px-4 w-full max-w-3xl mx-auto">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="text-center mb-12"
      >
        <div className="inline-flex items-center justify-center p-4 bg-accent/10 text-accent rounded-2xl mb-6 shadow-xl shadow-accent/5">
          <Brain size={48} />
        </div>
        <h1 className="text-4xl font-bold mb-4 tracking-tight">MentorOS</h1>
        <p className="text-xl text-gray-600 dark:text-gray-400">Upload your notes. Ask anything. Learn with evidence.</p>
      </motion.div>

      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.1 }}
        className="w-full flex flex-wrap justify-center gap-3 mt-8"
      >
        {suggestions.map((sug, i) => (
          <button key={i} className="px-4 py-2 bg-white dark:bg-gray-800/50 hover:bg-gray-50 dark:hover:bg-gray-800 border border-gray-200 dark:border-gray-700/50 hover:border-gray-300 dark:hover:border-gray-600 rounded-full text-sm text-gray-700 dark:text-gray-300 transition-colors flex items-center gap-2">
            <Sparkles size={14} className="text-accent" />
            {sug}
          </button>
        ))}
      </motion.div>
    </div>
  );
}

function AnswerPanel({ answer }) {
  return (
    <div className="flex flex-col gap-4 mt-2">
      <div className="prose dark:prose-invert max-w-none text-gray-800 dark:text-gray-200">
        <p>{answer.text}</p>
      </div>
      
      {/* Evidence Accordion / Timeline */}
      <div className="bg-white dark:bg-gray-900/50 border border-gray-200 dark:border-gray-800 rounded-xl overflow-hidden mt-2">
        <details className="group">
          <summary className="flex items-center justify-between p-3 cursor-pointer select-none">
            <div className="flex items-center gap-3">
              <Activity size={16} className="text-accent" />
              <span className="text-sm font-medium text-gray-800 dark:text-gray-300">AI Thinking Process & Evidence</span>
            </div>
            <div className="flex items-center gap-3">
              <span className="text-xs px-2 py-1 bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-400 rounded-full">
                {answer.sources.length} sources
              </span>
              <ChevronRight size={16} className="text-gray-500 transition-transform group-open:rotate-90" />
            </div>
          </summary>
          <div className="p-4 border-t border-gray-200 dark:border-gray-800 bg-gray-50 dark:bg-black/20 text-sm text-gray-600 dark:text-gray-400">
            <ul className="space-y-3">
              <li className="flex gap-2"><span className="text-green-400">✓</span> Planning search strategy</li>
              <li className="flex gap-2"><span className="text-green-400">✓</span> Retrieved from <strong>{answer.sources[0]}</strong> (pg. {answer.pages[0]})</li>
              <li className="flex gap-2"><span className="text-green-400">✓</span> Generating synthesized response</li>
            </ul>
          </div>
        </details>
      </div>

      {/* Quick Actions */}
      <div className="flex flex-wrap gap-2 mt-2">
        {["Explain Simpler", "Give Example", "Generate Quiz"].map((action, i) => (
          <button key={i} className="text-xs px-3 py-1.5 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 rounded-md text-gray-700 dark:text-gray-300 transition-colors">
            {action}
          </button>
        ))}
      </div>
    </div>
  );
}

function ChatThread({ chat }) {
  const messages = [
    { id: 1, role: 'user', content: `Explain the concept of memory paging as discussed in the notes.` },
    { 
      id: 2, 
      role: 'ai', 
      content: {
        text: `Memory paging is a memory management scheme that eliminates the need for contiguous allocation of physical memory. In this scheme, the operating system retrieves data from secondary storage in same-size blocks called pages.\n\nAccording to your notes, paging helps avoid external fragmentation and the need for compaction.`,
        sources: ['OS_Chapter4.pdf'],
        pages: ['12']
      },
      confidence: 92
    }
  ];

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-8 scroll-smooth pb-32 w-full max-w-4xl mx-auto">
      {messages.map(msg => (
        <div key={msg.id} className={`flex gap-4 mb-8 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
          {msg.role === 'ai' && (
            <div className="w-8 h-8 rounded-full bg-accent/20 flex items-center justify-center flex-shrink-0 mt-1 text-accent border border-accent/30">
              <Brain size={16} />
            </div>
          )}
          
          <div className={`max-w-[85%] ${msg.role === 'user' ? 'bg-gray-100 dark:bg-gray-800/80 p-4 rounded-2xl rounded-tr-sm border border-gray-200 dark:border-gray-700/50 text-gray-900 dark:text-gray-100' : ''}`}>
            {msg.role === 'user' ? (
              <p>{msg.content}</p>
            ) : (
              <AnswerPanel answer={msg.content} />
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

export default function CenterArea({ activeChat }) {
  return (
    <div className="flex flex-col h-full w-full relative">
      {activeChat ? <ChatThread chat={activeChat} /> : <NewChatHero />}
      
      {/* Sticky Input Bar */}
      <div className="absolute bottom-0 left-0 w-full p-4 md:p-6 bg-gradient-to-t from-background via-background to-transparent backdrop-blur-sm">
        <div className="max-w-3xl mx-auto relative">
          <div className="bg-white/80 dark:bg-gray-900/80 border border-gray-200 dark:border-gray-700/60 rounded-2xl p-2 shadow-2xl focus-within:border-accent/50 focus-within:ring-1 focus-within:ring-accent/50 transition-all backdrop-blur-md">
            <textarea 
              rows="1"
              placeholder="Ask a question about your uploaded documents..."
              className="w-full bg-transparent text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 resize-none outline-none px-3 py-2 max-h-32"
            />
            <div className="flex justify-between items-center mt-2 px-2">
              <div className="flex items-center gap-3">
                <button className="text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800">
                  <Paperclip size={20} />
                </button>
                <span className="text-[10px] uppercase font-bold tracking-wider text-gray-500 bg-gray-100 dark:bg-gray-800/50 px-2 py-1 rounded-full border border-gray-200 dark:border-gray-700/50">
                  Ollama · Qwen2.5
                </span>
              </div>
              <button className="bg-gray-900 dark:bg-white text-white dark:text-black p-2 rounded-xl hover:bg-gray-800 dark:hover:bg-gray-200 transition-colors flex items-center justify-center shadow-lg">
                <Send size={18} />
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
