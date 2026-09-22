import React, { useState, useCallback, useEffect, useRef } from 'react';
import {
  UploadCloud, FileText, CheckCircle2, AlertCircle,
  Loader2, X, RefreshCw
} from 'lucide-react';
import { uploadFile, getStatus } from '../api';

const EXT_COLORS = {
  PDF:  'bg-red-500/10 text-red-500',
  PPTX: 'bg-orange-500/10 text-orange-500',
  PPT:  'bg-orange-500/10 text-orange-500',
  DOCX: 'bg-blue-500/10 text-blue-500',
  DOC:  'bg-blue-500/10 text-blue-500',
  TXT:  'bg-gray-500/10 text-gray-500',
  MD:   'bg-gray-500/10 text-gray-500',
};

function extOf(name) {
  return (name.split('.').pop() || '').toUpperCase();
}

function FileCard({ file }) {
  const ext = extOf(file.name);
  const colorClass = EXT_COLORS[ext] || 'bg-gray-500/10 text-gray-500';

  return (
    <div className="group flex items-center gap-3 p-3 mb-2 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900/30 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
      <div className={`w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 text-[10px] font-bold ${colorClass}`}>
        {ext.slice(0, 3)}
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">{file.name}</p>
        <span className="text-xs text-emerald-500 flex items-center gap-1 mt-0.5">
          <CheckCircle2 size={11} /> Indexed
        </span>
      </div>
    </div>
  );
}

function UploadingCard({ name, progress }) {
  return (
    <div className="flex items-center gap-3 p-3 mb-2 rounded-xl border border-accent/30 bg-accent/5">
      <div className="w-9 h-9 rounded-lg flex items-center justify-center flex-shrink-0 bg-accent/10 text-accent">
        <Loader2 size={16} className="animate-spin" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate">{name}</p>
        <div className="w-full h-1 bg-gray-200 dark:bg-gray-800 rounded-full mt-1.5 overflow-hidden">
          <div className="h-full bg-accent rounded-full animate-pulse" style={{ width: `${progress}%` }} />
        </div>
      </div>
    </div>
  );
}

export default function FilePanel({ sessionId }) {
  const [sources, setSources] = useState([]);
  const [uploading, setUploading] = useState([]); // [{ name, progress }]
  const [error, setError] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef(null);

  const refreshSources = useCallback(async () => {
    try {
      const status = await getStatus();
      setSources(status.indexed_sources || []);
    } catch { /* backend not reachable */ }
  }, []);

  useEffect(() => { refreshSources(); }, [refreshSources]);

  const handleFiles = useCallback(async (files) => {
    setError('');
    const fileArr = Array.from(files);
    for (const file of fileArr) {
      const name = file.name;
      setUploading(prev => [...prev, { name, progress: 30 }]);
      try {
        setUploading(prev => prev.map(u => u.name === name ? { ...u, progress: 60 } : u));
        await uploadFile(file, sessionId);
        setUploading(prev => prev.map(u => u.name === name ? { ...u, progress: 100 } : u));
        await refreshSources();
      } catch (e) {
        setError(`Failed to upload "${name}": ${e.message}`);
      } finally {
        setTimeout(() => setUploading(prev => prev.filter(u => u.name !== name)), 800);
      }
    }
  }, [sessionId, refreshSources]);

  const onDrop = useCallback((e) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  }, [handleFiles]);

  const onDragOver = (e) => { e.preventDefault(); setIsDragging(true); };
  const onDragLeave = () => setIsDragging(false);

  return (
    <div className="flex flex-col h-full w-full p-4">
      <div className="mb-5 flex justify-between items-center">
        <h2 className="font-semibold text-lg">Documents</h2>
        <button
          id="refresh-docs-btn"
          onClick={refreshSources}
          className="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 p-1 rounded-md hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
          title="Refresh"
        >
          <RefreshCw size={15} />
        </button>
      </div>

      {/* Drop zone */}
      <div
        id="upload-dropzone"
        onClick={() => inputRef.current?.click()}
        onDrop={onDrop}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        className={`border-2 border-dashed rounded-2xl p-6 flex flex-col items-center justify-center text-center cursor-pointer transition-all mb-5 ${
          isDragging
            ? 'border-accent bg-accent/10 scale-[1.01]'
            : 'border-gray-300 dark:border-gray-700 hover:border-accent/50 bg-gray-50 dark:bg-gray-800/20 hover:bg-accent/5'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept=".pdf,.docx,.pptx,.txt,.md"
          className="hidden"
          onChange={(e) => handleFiles(e.target.files)}
        />
        <div className={`w-12 h-12 rounded-full flex items-center justify-center mb-3 transition-colors ${
          isDragging ? 'bg-accent/20 text-accent' : 'bg-gray-200 dark:bg-gray-800 text-gray-400 group-hover:bg-accent/20 group-hover:text-accent'
        }`}>
          <UploadCloud size={22} />
        </div>
        <p className="text-sm font-medium text-gray-800 dark:text-gray-300">
          {isDragging ? 'Drop to upload' : 'Click or drag files here'}
        </p>
        <p className="text-xs text-gray-500 mt-1">PDF, DOCX, PPTX, TXT, MD</p>
      </div>

      {/* Error */}
      {error && (
        <div className="flex items-start gap-2 text-xs text-red-500 bg-red-500/10 border border-red-500/20 rounded-lg p-3 mb-3">
          <AlertCircle size={13} className="mt-0.5 flex-shrink-0" />
          <span>{error}</span>
          <button onClick={() => setError('')} className="ml-auto"><X size={13} /></button>
        </div>
      )}

      {/* File list */}
      <div className="flex-1 overflow-y-auto pr-1 -mr-1">
        <div className="flex items-center justify-between mb-3 px-1">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Indexed Files</span>
          <span className="text-xs text-gray-500">{sources.length} file{sources.length !== 1 ? 's' : ''}</span>
        </div>

        {uploading.map(u => (
          <UploadingCard key={u.name} name={u.name} progress={u.progress} />
        ))}

        {sources.length === 0 && uploading.length === 0 ? (
          <div className="text-center text-xs text-gray-500 mt-6">
            <FileText size={24} className="mx-auto mb-2 opacity-30" />
            No documents indexed yet.
          </div>
        ) : (
          sources.map(name => <FileCard key={name} file={{ name }} />)
        )}
      </div>
    </div>
  );
}
