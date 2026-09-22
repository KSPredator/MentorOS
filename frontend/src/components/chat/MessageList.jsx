import React from 'react';
import { motion } from 'framer-motion';
import { fadeInUp } from '../../lib/variants';
import UserMessage from './UserMessage';
import AssistantMessage from './AssistantMessage';
import EmptyHero from './EmptyHero';
import StreamingMessage from './StreamingMessage';
import { useChat } from '../../stores/chat';

/** Scrollable message thread with auto-scroll on new content. */
export default function MessageList() {
  const messages = useChat((s) => s.messages);
  const messagesLoading = useChat((s) => s.messagesLoading);
  const streaming = useChat((s) => s.streaming);
  const scrollRef = React.useRef(null);
  const stickToBottom = React.useRef(true);

  // Auto-scroll while streaming if user is near bottom
  React.useEffect(() => {
    const el = scrollRef.current;
    if (!el || !stickToBottom.current) return;
    el.scrollTop = el.scrollHeight;
  }, [messages, streaming]);

  const onScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    stickToBottom.current = el.scrollHeight - el.scrollTop - el.clientHeight < 120;
  };

  const isEmpty = !messagesLoading && messages.length === 0 && !streaming;

  return (
    <div
      ref={scrollRef}
      onScroll={onScroll}
      className="flex-1 overflow-y-auto overscroll-contain"
      role="log"
      aria-live="polite"
      aria-label="Chat messages"
    >
      {isEmpty ? (
        <EmptyHero />
      ) : (
        <div className="max-w-3xl mx-auto px-4 py-6 space-y-5">
          {messagesLoading && (
            <div className="space-y-4 py-4" aria-hidden>
              {[0, 1].map((i) => (
                <div key={i} className="skeleton h-16 w-3/4 rounded-2xl" />
              ))}
            </div>
          )}
          {messages.map((m, i) => (
            <motion.div key={m.id ?? i} {...fadeInUp}>
              {m.role === 'user' ? (
                <UserMessage message={m} />
              ) : (
                <AssistantMessage message={m} />
              )}
            </motion.div>
          ))}
          {streaming && <StreamingMessage />}
        </div>
      )}
    </div>
  );
}
