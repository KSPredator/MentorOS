import React from 'react';
import { UploadCloud, FileText, CheckCircle2, MoreVertical, XCircle, AlertCircle } from 'lucide-react';

const mockFiles = [
  { id: 1, name: 'OS_Chapter4_Memory.pdf', size: '2.4 MB', date: 'Today', status: 'indexed', ext: 'PDF' },
  { id: 2, name: 'Lecture_Slides_Week3.pptx', size: '5.1 MB', date: 'Yesterday', status: 'indexed', ext: 'PPT' },
  { id: 3, name: 'Assignment_Requirements.docx', size: '1.2 MB', date: '3d ago', status: 'failed', ext: 'DOCX' },
];

function FileCard({ file }) {
  const isIndexed = file.status === 'indexed';
  const isFailed = file.status === 'failed';

  return (
    <div className="group flex items-center justify-between p-3 mb-2 rounded-xl border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900/30 hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors">
      <div className="flex items-center gap-3 overflow-hidden">
        <div className={`w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0 ${
          file.ext === 'PDF' ? 'bg-red-500/10 text-red-600 dark:text-red-400' :
          file.ext === 'PPT' ? 'bg-orange-500/10 text-orange-600 dark:text-orange-400' :
          'bg-blue-500/10 text-blue-600 dark:text-blue-400'
        }`}>
          <FileText size={20} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-gray-800 dark:text-gray-200 truncate pr-2">{file.name}</p>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-xs text-gray-500">{file.size}</span>
            <span className="text-gray-700 text-xs">•</span>
            {isIndexed ? (
              <span className="text-xs text-green-600 dark:text-green-400 flex items-center gap-1"><CheckCircle2 size={12}/> Indexed</span>
            ) : isFailed ? (
              <span className="text-xs text-red-600 dark:text-red-400 flex items-center gap-1"><AlertCircle size={12}/> Failed</span>
            ) : (
              <span className="text-xs text-amber-600 dark:text-amber-400">Processing...</span>
            )}
          </div>
        </div>
      </div>
      <button className="text-gray-500 opacity-0 group-hover:opacity-100 transition-opacity p-1">
        <MoreVertical size={16} />
      </button>
    </div>
  );
}

export default function FilePanel() {
  return (
    <div className="flex flex-col h-full w-full p-4">
      <div className="mb-6 flex justify-between items-center">
        <h2 className="font-semibold text-lg">Documents</h2>
      </div>

      <div className="border-2 border-dashed border-gray-300 dark:border-gray-700 hover:border-accent/50 rounded-2xl p-6 flex flex-col items-center justify-center text-center cursor-pointer transition-colors bg-gray-50 dark:bg-gray-800/20 hover:bg-accent/5 group mb-6">
        <div className="w-12 h-12 rounded-full bg-gray-200 dark:bg-gray-800 group-hover:bg-accent/20 flex items-center justify-center text-gray-400 group-hover:text-accent mb-3 transition-colors">
          <UploadCloud size={24} />
        </div>
        <p className="text-sm font-medium text-gray-800 dark:text-gray-300">Click or drag files here</p>
        <p className="text-xs text-gray-500 mt-1">Supports PDF, DOCX, PPT</p>
      </div>

      <div className="flex-1 overflow-y-auto pr-1 -mr-1">
        <div className="flex items-center justify-between mb-3 px-1">
          <span className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Uploaded Files</span>
          <span className="text-xs text-gray-500">{mockFiles.length} files</span>
        </div>
        
        {mockFiles.map(file => (
          <FileCard key={file.id} file={file} />
        ))}
      </div>
    </div>
  );
}
