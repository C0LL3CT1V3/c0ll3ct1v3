import { useCallback, useState } from 'react';
import { useApiClient } from '../../hooks/useApiClient';

export function useManagerChat() {
  const { apiClient } = useApiClient();
  const [messages, setMessages] = useState([
    {
      role: 'assistant',
      content:
        "I'm your c0ll3ct1v3 manager. Ask about your EPK, uploads, or next steps — I'll help you stay on track.",
    },
  ]);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

  const sendMessage = useCallback(
    async (text) => {
      const trimmed = text.trim();
      if (!trimmed || sending) return;

      const userMsg = { role: 'user', content: trimmed };
      setMessages((prev) => [...prev, userMsg]);
      setSending(true);
      setError('');

      try {
        const res = await apiClient.post('/manager/chat', { message: trimmed });
        const reply = res.data?.reply || 'No response.';
        setMessages((prev) => [...prev, { role: 'assistant', content: reply }]);
      } catch (err) {
        const detail = err?.response?.data?.detail || 'Manager chat failed.';
        setError(typeof detail === 'string' ? detail : JSON.stringify(detail));
      } finally {
        setSending(false);
      }
    },
    [apiClient, sending],
  );

  return { messages, sendMessage, sending, error };
}
