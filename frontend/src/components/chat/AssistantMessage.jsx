import React, { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Bot, Copy, Check } from 'lucide-react';
import CitationList from './CitationList';
import RefusalCard from './RefusalCard';
import QuizCard from './QuizCard';
import PodcastCard from './PodcastCard';
import MemoryCard from './MemoryCard';
import EvaluationBadge from './EvaluationBadge';
import { motion } from 'framer-motion';
import { fadeInUp } from '../../lib/variants';
import { toast } from 'sonner';

export default function AssistantMessage({ message }) {
  const meta = message?.meta || {};
  const type = meta.type || 'answer';
  const isRefusal = meta.is_refusal;

  if (type === 'quiz') {
    return (
      <div className="flex gap-3.5">
        <Avatar />
        <div className="min-w-0 flex-1">
          <QuizCard message={message} />
        </div>
      </div>
    );
  }

  if (type === 'podcast') {
    return (
      <div className="flex gap-3.5">
        <Avatar />
        <div className="min-w-0 flex-1">
          <PodcastCard script={meta.podcast_script} />
        </div>
      </div>
    );
  }

  if (type === 'memory') {
    return (
      <div className="flex gap-3.5">
        <Avatar />
        <div className="min-w-0 flex-1">
          <MemoryCard stats={meta.memory_stats} updates={meta.memory_updates} />
        </div>
      </div>
    );
  }

  if (isRefusal) {
    return (
      <div className="flex gap-3.5">
        <Avatar />
        <div className="min-w-0 flex-1">
          <RefusalCard message={message} />
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3.5">
      <Avatar />
      <div className="min-w-0 flex-1">
        <div className="answer-md text-textMain break-words">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              code({ node: _node, inline, className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || '');
                if (!inline && match) {
                  return (
                    <CodeBlock language={match[1]}>
                      {String(children).replace(/\n$/, '')}
                    </CodeBlock>
                  );
                }
                return (
                  <code className={className} {...props}>
                    {children}
                  </code>
                );
              },
            }}
          >
            {message?.content || ''}
          </ReactMarkdown>
        </div>

        {((meta.citations && meta.citations.length > 0) || meta.evaluation) && (
          <motion.div {...fadeInUp} className="mt-3.5 space-y-2.5">
            {meta.evaluation && <EvaluationBadge evaluation={meta.evaluation} />}
            {meta.citations && meta.citations.length > 0 && (
              <CitationList citations={meta.citations} />
            )}
          </motion.div>
        )}

        <MetaChips meta={meta} />
      </div>
    </div>
  );
}

function CodeBlock({ language, children }) {
  const [copied, setCopied] = useState(false);

  const onCopy = async () => {
    try {
      await navigator.clipboard.writeText(children);
      setCopied(true);
      toast.success('Code copied to clipboard');
      setTimeout(() => setCopied(false), 2000);
    } catch {
      toast.error('Failed to copy code');
    }
  };

  return (
    <div className="my-3 rounded-xl overflow-hidden border border-border bg-[#18181b] shadow-sm">
      <div className="flex items-center justify-between px-3.5 py-1.5 bg-[#121214] border-b border-border/50 text-[11px] font-mono text-textMuted">
        <span className="uppercase tracking-wider font-semibold text-accent">{language}</span>
        <button
          onClick={onCopy}
          className="flex items-center gap-1.5 px-2 py-1 rounded-md text-textFaint hover:text-textMain hover:bg-white/10 transition-colors"
          title="Copy code"
        >
          {copied ? (
            <>
              <Check size={12} className="text-success" />
              <span className="text-success font-sans text-[10px]">Copied</span>
            </>
          ) : (
            <>
              <Copy size={12} />
              <span className="font-sans text-[10px]">Copy</span>
            </>
          )}
        </button>
      </div>
      <div className="p-3 overflow-x-auto text-[13px] leading-relaxed">
        <SyntaxHighlighter
          style={oneDark}
          language={language}
          PreTag="div"
          customStyle={{
            margin: 0,
            padding: 0,
            background: 'transparent',
            fontSize: '0.88em',
          }}
        >
          {children}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}

function Avatar() {
  return (
    <div
      className="w-8 h-8 rounded-full bg-panel border border-border flex items-center
      justify-center flex-shrink-0 text-accent mt-0.5 shadow-sm"
      style={{
        boxShadow: '0 0 12px rgba(14, 165, 233, 0.15)',
      }}
    >
      <Bot size={15} strokeWidth={1.8} />
    </div>
  );
}

function MetaChips({ meta }) {
  const chips = [];
  if (meta?.route_method) {
    chips.push(
      <span
        key="method"
        className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-panel border border-border text-textFaint"
      >
        {meta.route_method}
      </span>,
    );
  }
  if (meta?.model_name) {
    chips.push(
      <span
        key="model"
        className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-panel border border-border text-textFaint"
      >
        {meta.model_name}
      </span>,
    );
  }
  if (meta?.memory_updates?.length > 0) {
    chips.push(
      <span
        key="mem"
        className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-successSoft text-success border border-success/25"
      >
        +{meta.memory_updates.length} memories
      </span>,
    );
  }
  if (!chips.length) return null;
  return (
    <div className="flex flex-wrap gap-1.5 mt-2.5 opacity-70 hover:opacity-100 transition-opacity">
      {chips}
    </div>
  );
}
