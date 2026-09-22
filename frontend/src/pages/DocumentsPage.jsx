import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { motion, AnimatePresence } from 'framer-motion';
import {
  UploadCloud,
  FileText,
  FileType2,
  Presentation,
  Trash2,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Inbox,
  Search,
  X,
  FileCode,
} from 'lucide-react';
import { useFiles } from '../stores/files';
import { useUI } from '../stores/ui';
import { useStatus } from '../stores/status';
import { formatBytes, relativeTime } from '../lib/format';
import EmptyState from '../components/ui/EmptyState';
import Button from '../components/ui/Button';
import IndeterminateBar from '../components/ui/IndeterminateBar';
import { SkeletonRows } from '../components/ui/Skeleton';
import { stagger, staggerItem } from '../lib/variants';
import { toast } from 'sonner';
import ChunkModal from '../components/files/ChunkModal';

const EXT_ICON = {
  pdf: FileText,
  docx: FileType2,
  doc: FileType2,
  pptx: Presentation,
  ppt: Presentation,
  txt: FileCode,
  md: FileCode,
};

/** Documents page: full-width upload + indexed file table + chunk viewer. */
export default function DocumentsPage() {
  const files = useFiles((s) => s.files);
  const uploading = useFiles((s) => s.uploading);
  const upload = useFiles((s) => s.upload);
  const remove = useFiles((s) => s.remove);
  const removeAll = useFiles((s) => s.removeAll);
  const loaded = useFiles((s) => s.loaded);
  const confirm = useUI((s) => s.confirm);
  const chunkModalId = useUI((s) => s.chunkModalId);
  const closeChunk = useUI((s) => s.closeChunk);
  const status = useStatus();
  const [query, setQuery] = useState('');

  const onDrop = useCallback(
    async (accepted) => {
      for (const file of accepted) {
        // eslint-disable-next-line no-await-in-loop
        const result = await upload(file);
        if (result.ok) toast.success(`Indexed ${file.name}`);
        else toast.error(`${file.name}: ${result.error}`);
      }
    },
    [upload],
  );

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    noClick: true,
    noKeyboard: true,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'application/msword': ['.doc'],
      'application/vnd.openxmlformats-officedocument.presentationml.presentation': ['.pptx'],
      'application/vnd.ms-powerpoint': ['.ppt'],
      'text/plain': ['.txt'],
      'text/markdown': ['.md'],
    },
  });

  const filtered = query
    ? files.filter((f) => f.filename.toLowerCase().includes(query.toLowerCase()))
    : files;

  const onRemoveAll = () => {
    confirm({
      title: 'Remove all files',
      message: `Delete all ${files.length} files and their indexed chunks from the knowledge base?`,
      confirmLabel: 'Remove all',
      onConfirm: async () => {
        try {
          await removeAll();
          toast.success('Knowledge base cleared');
        } catch {
          toast.error('Failed to clear files');
        }
      },
    });
  };

  const uploadingEntries = Object.entries(uploading);

  return (
    <div className="h-full overflow-y-auto relative z-0" {...getRootProps()}>
      <input {...getInputProps()} />
      <div className="max-w-4xl mx-auto px-5 py-7 pb-24">
        <motion.div {...staggerItem} className="mb-6">
          <div className="flex items-center justify-between flex-wrap gap-3">
            <div>
              <h1 className="font-display text-2xl sm:text-3xl font-extrabold tracking-tight text-textMain">
                Knowledge Documents
              </h1>
              <p className="text-sm text-textMuted mt-1">
                Parsed, chunked, and embedded locally on-device.{' '}
                {status.vector_store_chunks != null && (
                  <span className="font-mono text-textFaint">
                    ({status.vector_store_chunks} chunks · {status.files_indexed} files)
                  </span>
                )}
              </p>
            </div>
            <div className="flex items-center gap-2">
              <div className="relative">
                <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-textFaint" />
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Filter files…"
                  className="w-44 text-[13px] pl-8.5 pr-7 py-2 rounded-xl glass-panel text-textMain
                    outline-none focus:border-accent/60 transition-colors placeholder:text-textFaint"
                />
                {query && (
                  <button
                    onClick={() => setQuery('')}
                    className="absolute right-2 top-1/2 -translate-y-1/2 text-textFaint hover:text-textMain p-0.5 rounded cursor-pointer"
                  >
                    <X size={12} />
                  </button>
                )}
              </div>
              <Button variant="primary" size="md" onClick={open}>
                <UploadCloud size={14} />
                Upload
              </Button>
              {files.length > 0 && (
                <Button variant="danger" size="md" onClick={onRemoveAll}>
                  <Trash2 size={14} />
                  Clear All
                </Button>
              )}
            </div>
          </div>
        </motion.div>

        {/* Drop zone */}
        <motion.button
          {...staggerItem}
          onClick={open}
          className={`w-full rounded-2xl border-2 border-dashed p-8 sm:p-10 text-center mb-6 transition-all duration-200 cursor-pointer
            ${
              isDragActive
                ? 'border-accent bg-accentSoft shadow-glow scale-[1.01]'
                : 'border-border/80 glass-panel hover:border-accent/50 hover:shadow-card'
            }`}
        >
          <div className="w-12 h-12 rounded-2xl bg-accentSoft text-accent flex items-center justify-center mx-auto mb-3 shadow-sm">
            <UploadCloud size={24} strokeWidth={1.8} className={isDragActive ? 'animate-bounce' : ''} />
          </div>
          <div className="text-[14.5px] font-semibold text-textMain">
            {isDragActive ? 'Release files to index' : 'Drag & drop study materials here, or browse files'}
          </div>
          <div className="text-xs text-textFaint mt-1">
            PDF · DOCX · PPTX · TXT · MD — 100% local, never sent to third-party servers
          </div>
        </motion.button>

        {/* Uploading rows */}
        <AnimatePresence initial={false}>
          {uploadingEntries.map(([name, p]) => (
            <motion.div
              key={`up-${name}`}
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden mb-2.5"
            >
              <div className="rounded-xl border border-accent/40 bg-accentSoft/60 p-3.5 backdrop-blur shadow-sm">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm font-medium truncate flex items-center gap-2 text-textMain">
                    <Loader2 size={13} className="animate-spin text-accent" />
                    {name}
                  </span>
                  <span className="text-xs font-mono text-accent font-semibold">{Math.round(p * 100)}%</span>
                </div>
                <IndeterminateBar />
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* File table */}
        {!loaded ? (
          <SkeletonRows count={5} />
        ) : filtered.length === 0 && uploadingEntries.length === 0 ? (
          <EmptyState
            icon={Inbox}
            title={query ? 'No matching files' : 'Your knowledge base is empty'}
            body={
              query
                ? 'No documents matched your search filter.'
                : 'Upload lecture notes, textbooks, slides, or transcripts to ground your AI assistant in real facts.'
            }
          />
        ) : (
          <motion.div
            variants={stagger}
            initial="initial"
            animate="animate"
            className="space-y-2.5"
          >
            {filtered.map((f) => (
              <FileRow
                key={f.filename}
                file={f}
                onRemove={() => {
                  confirm({
                    title: 'Remove file',
                    message: `Remove "${f.filename}" and its indexed chunks?`,
                    confirmLabel: 'Remove',
                    onConfirm: async () => {
                      try {
                        await remove(f.filename);
                        toast.success(`Removed ${f.filename}`);
                      } catch {
                        toast.error('Failed to remove file');
                      }
                    },
                  });
                }}
              />
            ))}
          </motion.div>
        )}
      </div>

      <ChunkModal open={chunkModalId != null} chunkId={chunkModalId} onClose={closeChunk} />
    </div>
  );
}

function FileRow({ file, onRemove }) {
  const ext = (file.filename.split('.').pop() || '').toLowerCase();
  const Icon = EXT_ICON[ext] || FileText;
  const failed = file.status === 'failed';
  const processing = file.status === 'processing';

  return (
    <motion.div
      variants={staggerItem}
      layout
      exit={{ opacity: 0, x: 30, transition: { duration: 0.15 } }}
      className="group glass-card rounded-2xl p-4 hover:border-accent/40 hover:shadow-card transition-all duration-150"
    >
      <div className="flex items-start gap-3.5">
        <div className="w-10 h-10 rounded-xl bg-panel border border-border flex items-center justify-center flex-shrink-0 text-accent group-hover:scale-105 transition-transform">
          <Icon size={18} strokeWidth={1.8} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-[14px] font-semibold text-textMain truncate">{file.filename}</span>
            <StatusPill status={file.status} />
          </div>
          <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5 mt-1 text-[11.5px] text-textFaint">
            <span>{formatBytes(file.size_bytes)}</span>
            <span>·</span>
            <span>{relativeTime(file.uploaded_at)}</span>
            {file.chunk_count != null && (
              <>
                <span>·</span>
                <span className="font-mono text-textMuted font-medium">{file.chunk_count} chunks</span>
              </>
            )}
            {file.pages != null && (
              <>
                <span>·</span>
                <span className="font-mono text-textMuted font-medium">{file.pages} pages</span>
              </>
            )}
          </div>
          {failed && file.error && (
            <div className="mt-1.5 text-[11.5px] text-danger font-medium">{file.error}</div>
          )}
        </div>
        <button
          onClick={onRemove}
          aria-label={`Remove ${file.filename}`}
          className="opacity-0 group-hover:opacity-100 p-2 rounded-lg text-textFaint
            hover:text-danger hover:bg-dangerSoft transition-all flex-shrink-0 cursor-pointer"
        >
          <Trash2 size={15} />
        </button>
      </div>
      {processing && (
        <div className="mt-3">
          <IndeterminateBar height={2} />
        </div>
      )}
    </motion.div>
  );
}

function StatusPill({ status }) {
  if (status === 'indexed') {
    return (
      <span className="inline-flex items-center gap-1 text-[10.5px] font-medium px-2 py-0.5 rounded-full bg-successSoft text-success border border-success/25">
        <CheckCircle2 size={10} />
        Indexed
      </span>
    );
  }
  if (status === 'failed') {
    return (
      <span className="inline-flex items-center gap-1 text-[10.5px] font-medium px-2 py-0.5 rounded-full bg-dangerSoft text-danger border border-danger/25">
        <AlertCircle size={10} />
        Failed
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 text-[10.5px] font-medium px-2 py-0.5 rounded-full bg-accentSoft text-accent border border-accent/25">
      <Loader2 size={10} className="animate-spin" />
      Processing
    </span>
  );
}
