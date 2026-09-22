import { create } from 'zustand';
import { api } from '../api/client';
import { streamAsk } from '../api/sse';

/**
 * Chat store: sessions, messages, live streaming state.
 * Streaming model: tokens accumulate in `streamText` (verifying state);
 * onFinal replaces everything with the persisted message (post-gate).
 */
export const useChat = create((set, get) => ({
  sessions: [],
  sessionsLoaded: false,
  activeId: null,
  messages: [],
  messagesLoading: false,

  // streaming
  streaming: false,
  streamStage: null, // planning | retrieving | generating | evaluating | done
  streamAction: null,
  streamRoute: null,
  streamText: '',
  streamEvaluation: null,
  streamError: null,
  abortFn: null,

  loadSessions: async () => {
    try {
      const sessions = await api.get('/api/sessions');
      set({ sessions, sessionsLoaded: true });
    } catch {
      set({ sessionsLoaded: true });
    }
  },

  setActive: async (sessionId) => {
    set({ activeId: sessionId, messages: [], messagesLoading: !!sessionId });
    if (!sessionId) return;
    try {
      const data = await api.get(`/api/sessions/${sessionId}/messages`);
      set({ messages: data.messages || [], messagesLoading: false });
    } catch {
      set({ messages: [], messagesLoading: false });
    }
  },

  newChat: () => {
    get().resetStream();
    set({ activeId: null, messages: [] });
  },

  renameSession: async (sessionId, title) => {
    try {
      await api.patch(`/api/sessions/${sessionId}`, { title });
      await get().loadSessions();
    } catch {
      /* toast handled by caller */
      throw new Error('rename failed');
    }
  },

  deleteSession: async (sessionId) => {
    await api.del(`/api/sessions/${sessionId}`);
    if (get().activeId === sessionId) {
      set({ activeId: null, messages: [] });
    }
    await get().loadSessions();
  },

  resetStream: () => {
    const abort = get().abortFn;
    if (abort) abort();
    set({
      streaming: false,
      streamStage: null,
      streamAction: null,
      streamRoute: null,
      streamText: '',
      streamEvaluation: null,
      streamError: null,
      abortFn: null,
    });
  },

  /** Optimistically append the user bubble, then stream the assistant reply. */
  sendMessage: (text) => {
    const message = (text || '').trim();
    if (!message || get().streaming) return;

    const optimistic = {
      id: `tmp-${Date.now()}`,
      role: 'user',
      content: message,
      meta: {},
      created_at: new Date().toISOString(),
    };
    set((s) => ({
      messages: [...s.messages, optimistic],
      streaming: true,
      streamStage: 'planning',
      streamText: '',
      streamEvaluation: null,
      streamAction: null,
      streamRoute: null,
      streamError: null,
    }));

    const abortFn = streamAsk(
      { message, session_id: get().activeId },
      {
        onMeta: (d) => {
          set({
            streamAction: d.action,
            streamRoute: d,
            // New session created server-side
            ...(d.session_id && d.session_id !== get().activeId
              ? { activeId: d.session_id }
              : {}),
          });
          if (d.user_message_id) {
            // Replace optimistic id with the real one
            set((s) => ({
              messages: s.messages.map((m, i) =>
                i === s.messages.length - 1 && m.id?.toString?.().startsWith('tmp-')
                  ? { ...m, id: d.user_message_id }
                  : m,
              ),
            }));
          }
          get().loadSessions();
        },
        onStage: (d) => set({ streamStage: d.stage }),
        onToken: (d) =>
          set((s) => ({ streamText: s.streamText + (d.delta || '') })),
        onEvaluation: (d) => set({ streamEvaluation: d }),
        onFinal: (d) => {
          const assistantMsg = {
            id: d.assistant_message_id,
            role: 'assistant',
            content: d.content,
            meta: {
              type: d.type,
              action: d.action,
              route_method: d.route_method,
              route_confidence: d.route_confidence,
              citations: d.citations,
              retrieved: d.retrieved,
              evaluation: d.evaluation,
              memory_updates: d.memory_updates,
              quiz: d.quiz,
              podcast_script: d.podcast_script,
              memory_stats: d.memory_stats,
              is_refusal: d.is_refusal,
              model_name: d.model_name,
            },
            created_at: new Date().toISOString(),
          };
          set((s) => ({
            messages: [...s.messages, assistantMsg],
            streaming: false,
            streamStage: 'done',
            streamText: '',
            streamEvaluation: null,
            abortFn: null,
          }));
          // Refresh sessions for title/count updates, then clear stage shortly
          get().loadSessions();
          setTimeout(() => {
            if (!get().streaming) set({ streamStage: null, streamAction: null, streamRoute: null });
          }, 1200);
        },
        onError: (e) => {
          set({
            streaming: false,
            streamError: e?.message || 'Something went wrong.',
            streamStage: null,
            abortFn: null,
          });
        },
      },
    );
    set({ abortFn });
  },

  /** Append a server-persisted assistant message (quiz results etc.). */
  appendMessage: (msg) => set((s) => ({ messages: [...s.messages, msg] })),

  submitQuiz: async (messageId, answers) => {
    const sessionId = get().activeId;
    const result = await api.post('/api/quiz/submit', {
      session_id: sessionId,
      message_id: messageId,
      answers,
    });
    const msg = {
      id: result.assistant_message_id ?? `qr-${Date.now()}`,
      role: 'assistant',
      content: result.content,
      meta: {
        type: 'quiz_result',
        score: result.score,
        total: result.total,
        feedback: result.feedback,
        memory_updates: result.memory_updates,
      },
      created_at: new Date().toISOString(),
    };
    // Only append if not already present (server persisted it for reload)
    set((s) => {
      if (s.messages.some((m) => m.id === msg.id)) return s;
      return { messages: [...s.messages, msg] };
    });
    return result;
  },
}));
