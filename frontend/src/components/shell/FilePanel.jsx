import React, { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileText,
  FileType2,
  Presentation,
  X,
  Trash2,
  UploadCloud,
  CheckCircle2,
  AlertCircle,
  Inbox,
  FileCode,
} from 'lucide-react';
import { useFiles } from '../../stores/files';
import { useUI } from '../../stores/ui';
import { formatBytes, relativeTime } from '../../lib/format';
import IndeterminateBar from '../ui/IndeterminateBar';
import EmptyState from '../ui/EmptyState';
import { toast } from 'sonner';

const EXT_ICON = {
  pdf: FileText,
  docx: FileType2,
  doc: FileType2,
  pptx: Presentation,
  ppt: Presentation,
  txt: FileCode,
  md: FileCode,
};

const STATUS_STYLE = {
  indexed: { icon: CheckCircle2, color: 'var(--color-success)', label: 'Indexed' },
  processing: { icon: UploadCloud, color: 'var(--color-accent)', label: 'Processing' },
  failed: { icon: AlertCircle, color: 'var(--color-danger)', label: 'Failed' },
};

export default function FilePanel() {
  const files = useFiles((s) => s.files);
  const uploading = useFiles((s) => s.uploading);
  const upload = useFiles((s) => s.upload);
  const remove = useFiles((s) => s.remove);
  const removeAll = useFiles((s) => s.removeAll);
  const loaded = useFiles((s) => s.loaded);
  const filePanelOpen = useUI((s) => s.filePanelOpen);
  const setFilePanel = useUI((s) => s.setFilePanel);
  const confirm = useUI((s) => s.confirm);
  const [dragOver, setDragOver] = useState(false);

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

  const onRemoveAll = () => {
    confirm({
      title: 'Remove all files',
      message: `Delete all ${files.length} files and their indexed chunks? This cannot be undone.`,
      confirmLabel: 'Remove all',
      onConfirm: async () => {
        try {
          await removeAll();
          toast.success('All files removed');
        } catch {
          toast.error('Failed to remove files');
        }
      },
    });
  };

  if (!filePanelOpen) return null;

  const uploadingEntries = Object.entries(uploading);

  return (
    <aside
      {...getRootProps()}
      className={`hidden lg:flex flex-col w-[308px] flex-shrink-0 h-full glass-panel border-l border-border/80 z-10 transition-all
        ${isDragActive || dragOver ? 'ring-2 ring-inset ring-accent bg-accentSoft/30' : ''}`}
      onDragEnter={() => setDragOver(true)}
      onDragLeave={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget)) setDragOver(false);
      }}
      onDrop={() => setDragOver(false)}
    >
      <input {...getInputProps()} />
      <div className="flex items-center justify-between px-4 h-14 border-b border-border/70 flex-shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-lg bg-accentSoft text-accent flex items-center justify-center">
            <Inbox size={13} />
          </div>
          <span className="font-display font-bold text-[13.5px] text-textMain">Knowledge Base</span>
          <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-panel border border-border text-textMuted font-semibold">
            {files.length}
          </span>
        </div>
        <div className="flex items-center gap-1">
          {files.length > 0 && (
            <button
              onClick={onRemoveAll}
              aria-label="Remove all files"
              className="p-1.5 rounded-lg text-textFaint hover:text-danger hover:bg-dangerSoft transition-colors cursor-pointer"
            >
              <Trash2 size={14} />
            </button>
          )}
          <button
            onClick={() => setFilePanel(false)}
            aria-label="Close file panel"
            className="p-1.5 rounded-lg text-textFaint hover:text-textMain hover:bg-panelHover transition-colors cursor-pointer"
          >
            <X size={15} />
          </button>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-2.5">
        {/* Upload drop zone */}
        <button
          onClick={open}
          className={`w-full rounded-2xl border-2 border-dashed p-4 text-center transition-all cursor-pointer
            ${
              isDragActive
                ? 'border-accent bg-accentSoft shadow-sm'
                : 'border-border/80 glass-panel hover:border-accent/50 hover:bg-panelHover shadow-subtle'
            }`}
        >
          <UploadCloud size={22} className="mx-auto text-accent mb-1.5" strokeWidth={1.8} />
          <div className="text-[12.5px] font-semibold text-textMain">
            {isDragActive ? 'Drop to index' : 'Add study documents'}
          </div>
          <div className="text-[10px] text-textFaint mt-0.5">
            PDF · DOCX · PPTX · TXT · MD — 100% on-device
          </div>
        </button>

        {/* Uploading rows */}
        <AnimatePresence initial={false}>
          {uploadingEntries.map(([name, pct]) => (
            <motion.div
              key={`up-${name}`}
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="overflow-hidden"
            >
              <div className="rounded-xl border border-accent/40 bg-accentSoft/60 p-3 shadow-subtle">
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="text-xs font-semibold text-textMain truncate">{name}</span>
                  <span className="text-[10px] font-mono text-accent font-bold">
                    {Math.round(pct * 100)}%
                  </span>
                </div>
                <IndeterminateBar />
              </div>
            </motion.div>
          ))}
        </AnimatePresence>

        {/* File list */}
        {!loaded ? (
          <div className="space-y-2">
            {[0, 1, 2].map((i) => (
              <div key={i} className="skeleton h-[72px] rounded-xl" />
            ))}
          </div>
        ) : files.length === 0 && uploadingEntries.length === 0 ? (
          <EmptyState
            compact
            title="No documents yet"
            body="Drop notes or textbooks here — chunks and embeddings stay completely private."
          />
        ) : (
          <AnimatePresence initial={false}>
            {files.map((f) => (
              <FileRow
                key={f.filename}
                file={f}
                onRemove={() => {
                  confirm({
                    title: 'Remove file',
                    message: `Remove "${f.filename}" and its indexed chunks from the knowledge base?`,
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
          </AnimatePresence>
        )}
      </div>
    </aside>
  );
}

function FileRow({ file, onRemove }) {
  const ext = (file.filename.split('.').pop() || '').toLowerCase();
  const Icon = EXT_ICON[ext] || FileText;
  const statusConfig = STATUS_STYLE[file.status] || STATUS_STYLE.processing;
  const StatusIcon = statusConfig.icon;
  const isFailed = file.status === 'failed';
  const isProcessing = file.status === 'processing';

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, x: -20, transition: { duration: 0.15 } }}
      className="group glass-card rounded-xl p-3 hover:border-accent/40 transition-all duration-150"
    >
      <div className="flex items-start gap-2.5">
        <div className="w-8.5 h-8.5 rounded-lg bg-panel border border-border flex items-center justify-center flex-shrink-0 text-accent group-hover:scale-105 transition-transform">
          <Icon size={16} strokeWidth={1.8} />
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-1.5">
            <span className="text-[12.5px] font-semibold text-textMain truncate flex-1">
              {file.filename}
            </span>
            <span
              className="flex items-center gap-1 text-[10px] font-semibold px-1.5 py-0.5 rounded-full"
              style={{
                color: statusConfig.color,
                background:
                  file.status === 'indexed'
                    ? 'var(--color-successSoft)'
                    : file.status === 'failed'
                      ? 'var(--color-dangerSoft)'
                      : 'var(--color-accentSoft)',
              }}
            >
              <StatusIcon size={10} className={isProcessing ? 'animate-spin' : ''} />
              {statusConfig.label}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-x-1.5 text-[10.5px] text-textFaint mt-0.5">
            <span>{formatBytes(file.size_bytes)}</span>
            <span>·</span>
            <span>{relativeTime(file.uploaded_at)}</span>
            {file.chunk_count != null && (
              <>
                <span>·</span>
                <span className="font-mono font-medium">{file.chunk_count} chunks</span>
              </>
            )}
          </div>

          {isFailed && file.error && (
            <div className="text-[10.5px] text-danger font-medium mt-1 truncate">{file.error}</div>
          )}
        </div>

        <button
          onClick={onRemove}
          aria-label={`Remove ${file.filename}`}
          className="opacity-0 group-hover:opacity-100 p-1 rounded-md text-textFaint hover:text-danger hover:bg-dangerSoft transition-all flex-shrink-0 cursor-pointer"
        >
          <Trash2 size={13} />
        </button>
      </div>

      {isProcessing && (
        <div className="mt-2">
          <IndeterminateBar height={2} />
        </div>
      )}
    </motion.div>
  );
}
