import React from 'react';
import { motion } from 'framer-motion';
import { FileText, Quote } from 'lucide-react';
import { useUI } from '../../stores/ui';

/**
 * Citation chips from RAG retrieval. Each citation is
 * { source_file, page_number, chunk_id, score } (CitationOut).
 * Click opens the chunk modal for source verification.
 */
export default function CitationList({ citations = [] }) {
  const openChunk = useUI((s) => s.openChunk);
  if (!citations.length) return null;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-1.5 text-[11px] font-medium text-textFaint uppercase tracking-wider">
        <Quote size={11} />
        Sources · {citations.length}
      </div>
      <div className="flex flex-wrap gap-1.5">
        {citations.map((c, i) => (
          <motion.button
            key={`${c.source_file ?? 'doc'}-${c.chunk_id ?? i}`}
            whileHover={{ scale: 1.03 }}
            whileTap={{ scale: 0.97 }}
            onClick={() => c.chunk_id != null && openChunk(c.chunk_id)}
            disabled={c.chunk_id == null}
            className="group flex items-center gap-1.5 max-w-full px-2.5 py-1.5 rounded-lg
              bg-panel border border-border text-[11px] text-textMuted
              hover:border-accent/45 hover:text-textMain hover:bg-accentSoft
              transition-all disabled:opacity-60 disabled:pointer-events-none"
            title="Open source chunk"
          >
            <span className="w-4 h-4 rounded bg-accentSoft text-accent flex items-center justify-center font-mono text-[9px] font-bold flex-shrink-0">
              {i + 1}
            </span>
            <FileText size={11} className="flex-shrink-0 text-textFaint group-hover:text-accent" />
            <span className="truncate max-w-[160px] font-medium">
              {c.source_file || 'document'}
            </span>
            {c.page_number != null && (
              <span className="font-mono text-textFaint flex-shrink-0">p.{c.page_number}</span>
            )}
            {c.score != null && (
              <span className="font-mono text-textFaint flex-shrink-0">
                {(c.score * 100).toFixed(0)}%
              </span>
            )}
          </motion.button>
        ))}
      </div>
    </div>
  );
}