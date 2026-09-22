import React, { useEffect, useState } from 'react';
import Modal from '../ui/Modal';
import { api } from '../../api/client';
import { SkeletonRows } from '../ui/Skeleton';

/**
 * Modal that fetches and displays the full text of a retrieved chunk,
 * so users can verify citations against source content.
 */
export default function ChunkModal({ open, chunkId, onClose }) {
  const [chunk, setChunk] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || chunkId == null) {
      setChunk(null);
      setError(null);
      return;
    }
    let alive = true;
    setLoading(true);
    setError(null);
    api
      .get(`/api/chunks/${chunkId}`)
      .then((data) => {
        if (alive) setChunk(data);
      })
      .catch((e) => {
        if (alive) setError(e.detail || 'Failed to load chunk');
      })
      .finally(() => {
        if (alive) setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, [open, chunkId]);

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={chunk ? `Source · ${chunk.source_file || 'document'}` : 'Source chunk'}
      maxWidth="max-w-2xl"
    >
      {loading ? (
        <SkeletonRows count={4} />
      ) : error ? (
        <div className="text-sm text-danger">{error}</div>
      ) : chunk ? (
        <div className="space-y-3">
          <div className="flex flex-wrap items-center gap-2 text-[11px] font-mono text-textMuted">
            <span className="px-2 py-0.5 rounded-md bg-panel border border-border">
              chunk {chunk.chunk_id ?? chunkId}
            </span>
            {chunk.page_number != null && (
              <span className="px-2 py-0.5 rounded-md bg-panel border border-border">
                page {chunk.page_number}
              </span>
            )}
            {chunk.score != null && (
              <span className="px-2 py-0.5 rounded-md bg-accentSoft text-accent border border-accent/25">
                similarity {(chunk.score * 100).toFixed(1)}%
              </span>
            )}
          </div>
          <div className="text-[13.5px] leading-relaxed whitespace-pre-wrap text-textMain/90 bg-panel border border-border rounded-xl p-4 max-h-[50vh] overflow-y-auto answer-md">
            {chunk.text || chunk.content || '(empty)'}
          </div>
        </div>
      ) : null}
    </Modal>
  );
}
