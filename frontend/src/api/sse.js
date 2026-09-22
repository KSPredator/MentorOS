/**
 * SSE-over-fetch client for POST /api/ask/stream.
 * Parses `event:` / `data:` lines from a ReadableStream.
 *
 * handlers: { onMeta, onStage, onToken, onCitations, onEvaluation, onFinal, onError }
 * Returns an abort function.
 */

export function streamAsk(body, handlers = {}) {
  const controller = new AbortController();

  (async () => {
    let res;
    try {
      res = await fetch('/api/ask/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
        signal: controller.signal,
      });
    } catch (e) {
      if (e.name === 'AbortError') return;
      handlers.onError?.({ message: 'Cannot reach the MentorOS API.' });
      return;
    }

    if (!res.ok) {
      let detail = `Stream failed (${res.status})`;
      try {
        const data = await res.json();
        if (typeof data?.detail === 'string') detail = data.detail;
      } catch {
        /* keep */
      }
      handlers.onError?.({ message: detail, status: res.status });
      return;
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    const dispatch = (eventName, dataStr) => {
      let data;
      try {
        data = JSON.parse(dataStr);
      } catch {
        data = dataStr;
      }
      switch (eventName) {
        case 'meta':
          handlers.onMeta?.(data);
          break;
        case 'stage':
          handlers.onStage?.(data);
          break;
        case 'token':
          handlers.onToken?.(data);
          break;
        case 'citations':
          handlers.onCitations?.(data);
          break;
        case 'evaluation':
          handlers.onEvaluation?.(data);
          break;
        case 'final':
          handlers.onFinal?.(data);
          break;
        case 'error':
          handlers.onError?.(data);
          break;
        default:
          break;
      }
    };

    try {
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        // Normalize \r\n to \n so CRLF line breaks parse reliably across Windows / Uvicorn
        buffer = buffer.replace(/\r\n/g, '\n').replace(/\r/g, '\n');

        let sep;
        while ((sep = buffer.indexOf('\n\n')) !== -1) {
          const block = buffer.slice(0, sep);
          buffer = buffer.slice(sep + 2);
          let eventName = 'message';
          const dataLines = [];
          for (const line of block.split('\n')) {
            const trimmed = line.trim();
            if (trimmed.startsWith('event:')) eventName = trimmed.slice(6).trim();
            else if (trimmed.startsWith('data:')) dataLines.push(trimmed.slice(5).trim());
          }
          if (dataLines.length) dispatch(eventName, dataLines.join('\n'));
        }
      }

      // Flush any trailing block left in buffer on stream completion
      if (buffer && buffer.trim()) {
        const block = buffer.trim();
        let eventName = 'message';
        const dataLines = [];
        for (const line of block.split('\n')) {
          const trimmed = line.trim();
          if (trimmed.startsWith('event:')) eventName = trimmed.slice(6).trim();
          else if (trimmed.startsWith('data:')) dataLines.push(trimmed.slice(5).trim());
        }
        if (dataLines.length) dispatch(eventName, dataLines.join('\n'));
      }
    } catch (e) {
      if (e.name !== 'AbortError') {
        handlers.onError?.({ message: e.message || 'Stream interrupted.' });
      }
    }
  })();

  return () => controller.abort();
}

export default streamAsk;
