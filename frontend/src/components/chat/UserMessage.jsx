import React from 'react';
import { motion } from 'framer-motion';

export default function UserMessage({ message }) {
  return (
    <div className="flex justify-end">
      <motion.div
        initial={{ opacity: 0, y: 8, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.2 }}
        className="max-w-[82%] sm:max-w-[76%] px-4 py-2.5 rounded-2xl rounded-br-md
          bg-gradient-to-br from-accent via-accent to-sky-600 text-white
          text-[14.5px] sm:text-[15px] leading-relaxed whitespace-pre-wrap break-words
          shadow-md shadow-accent/20 border border-white/15"
      >
        {message?.content || ''}
      </motion.div>
    </div>
  );
}
