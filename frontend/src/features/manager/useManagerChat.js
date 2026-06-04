import { useCallback, useEffect, useState } from 'react';
import { useApiClient } from '../../hooks/useApiClient';

export function useManagerChat({ mode = 'general', threadId: externalThreadId, onThreadId, onAfterReply } = {}) {
  const { apiClient, authReady } = useApiClient();
  const [threadId, setThreadId] = useState(externalThreadId || null);
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        mode === 'epk_builder'
          ? 'Describe how you want your EPK to look. I will update the preview on the right.'
          : "I'm your c0ll3ct1v3 manager. Ask about your EPK, uploads, or next steps.",
    },
  ]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (externalThreadId) setThreadId(externalThreadId);
  }, [externalThreadId]);

  useEffect(() => {
    if (!authReady || !threadId) return;
    apiClient
      .get(`/manager/threads/${threadId}`)
      .then((res) => {
        const msgs = res.data?.messages || [];
        if (msgs.length) {
          setMessages(msgs.map((m) => ({ role: m.role, content: m.content })));
        }
      })
      .catch(() => {});
  }, [authReady, threadId, apiClient]);

  const ensureThread = useCallback(async () => {
    if (threadId) return threadId;
    const res = await apiClient.post('/manager/threads', {
      mode: mode === 'epk_builder' ? 'epk_builder' : 'general',
    });
    const id = res.data.id;
    setThreadId(id);
    onThreadId?.(id);
    return id;
  }, [apiClient, threadId, mode, onThreadId]);

  const sendMessage = useCallback(
    async (text) => {
      const trimmed = text.trim();
      if (!trimmed || sending) return;

      const userMsg = { role: 'user', content: trimmed };
      setMessages((prev) => [...prev, userMsg]);
      setSending(true);
      setError('');

      try {
        const tid = await ensureThread();
        const res = await apiClient.post('/manager/chat', {
          message: trimmed,
          thread_id: tid,
          channel: 'portal',
          mode: mode === 'epk_builder' ? 'epk_builder' : 'general',
        });
        const reply = res.data?.reply || 'No response.';
        const draftUpdated = Boolean(res.data?.draft_updated);
        const reasoningSummary = res.data?.reasoning_summary || '';
        if (res.data?.thread_id) {
          setThreadId(res.data.thread_id);
          onThreadId?.(res.data.thread_id);
        }
        setMessages((prev) => [...prev, { role: 'assistant', content: reply }]);
        if (onAfterReply) {
          await onAfterReply({ draftUpdated, reasoningSummary, reply });
        }
      } catch (err) {
        const detail = err?.response?.data?.detail || 'Manager chat failed.';
        setError(typeof detail === 'string' ? detail : JSON.stringify(detail));
      } finally {
        setSending(false);
      }
    },
    [apiClient, sending, ensureThread, onThreadId, onAfterReply],
  );

  return { messages, sendMessage, sending, error, threadId, setThreadId };
}
