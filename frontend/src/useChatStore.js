import { useState, useCallback, useRef } from 'react';
import { askStream } from './api';

/**
 * Chat state and message-send logic.
 *
 * messages[] shape:
 *   { id, role: 'user'|'ai', content: string,
 *     citations?, confidence?, planner?, evaluation?, isStreaming? }
 */
export function useChatStore(sessionId) {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [streamingText, setStreamingText] = useState('');
  const [plannerInfo, setPlannerInfo] = useState(null);
  const abortRef = useRef(null);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setStreamingText('');
    setPlannerInfo(null);
  }, []);

  const sendMessage = useCallback(async (question) => {
    if (!question.trim() || isLoading) return;

    // Cancel any previous in-flight request
    if (abortRef.current) abortRef.current.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    // Append user message immediately
    const userMsg = { id: Date.now(), role: 'user', content: question };
    setMessages(prev => [...prev, userMsg]);
    setIsLoading(true);
    setStreamingText('');
    setPlannerInfo(null);

    // Placeholder AI message (streaming)
    const aiId = Date.now() + 1;
    setMessages(prev => [...prev, { id: aiId, role: 'ai', content: '', isStreaming: true }]);

    try {
      const bodyStream = await askStream(question, sessionId, controller.signal);
      const reader = bodyStream.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let accumulated = '';
      let finalPlanner = null;

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer = buffer.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
        const lines = buffer.split('\n');
        buffer = lines.pop(); // keep incomplete last line

        for (const rawLine of lines) {
          const line = rawLine.trim();
          if (!line.startsWith('data:')) continue;
          try {
            const evt = JSON.parse(line.slice(5).trim());

            if (evt.type === 'planner' || evt.stage === 'planning') {
              finalPlanner = evt;
              setPlannerInfo(evt);
            } else if (evt.token || evt.delta) {
              const tok = evt.token || evt.delta || '';
              accumulated += tok;
              setStreamingText(accumulated);
              // Update the placeholder in-place
              setMessages(prev =>
                prev.map(m => m.id === aiId ? { ...m, content: accumulated } : m)
              );
            } else if (evt.type === 'done' || evt.content) {
              if (evt.content) accumulated = evt.content;
              // Streaming complete — mark message as non-streaming
              setMessages(prev =>
                prev.map(m =>
                  m.id === aiId
                    ? { ...m, content: accumulated, isStreaming: false, planner: finalPlanner }
                    : m
                )
              );
            }
          } catch {
            // skip malformed line
          }
        }
      }
    } catch (err) {
      if (err.name === 'AbortError') return;
      // Show error inline
      setMessages(prev =>
        prev.map(m =>
          m.id === aiId
            ? { ...m, content: `⚠️ Error: ${err.message}`, isStreaming: false, isError: true }
            : m
        )
      );
    } finally {
      setIsLoading(false);
      setStreamingText('');
    }
  }, [sessionId, isLoading]);

  return { messages, isLoading, streamingText, plannerInfo, sendMessage, clearMessages };
}
