import React, { useState } from 'react';
import { useManagerChat } from './useManagerChat';

function ManagerChat({
  layout = 'vertical',
  mode = 'general',
  threadId,
  onThreadId,
  onAfterReply,
  phase,
  reasoningSummary,
}) {
  const { messages, sendMessage, sending, error } = useManagerChat({
    mode,
    threadId,
    onThreadId,
    onAfterReply,
  });
  const [input, setInput] = useState('');
  const horizontal = layout === 'horizontal';

  const onSubmit = (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    sendMessage(input);
    setInput('');
  };

  const busy = sending || phase === 'generating' || phase === 'refining';

  return (
    <div className={`manager-chat${horizontal ? ' manager-chat--horizontal' : ''}`}>
      {!horizontal ? <h2 className="portal-panel-title">Manager</h2> : null}
      {reasoningSummary ? <p className="manager-reasoning-hint">{reasoningSummary}</p> : null}
      <div
        className={`manager-chat-messages${
          horizontal ? ' manager-chat-messages--horizontal' : ''
        }`}
      >
        {messages.map((m, i) => (
          <div key={`${m.role}-${i}`} className={`manager-chat-bubble manager-chat-bubble--${m.role}`}>
            {m.content}
          </div>
        ))}
        {busy ? (
          <div
            className="manager-chat-bubble manager-chat-bubble--assistant manager-chat-typing"
            role="status"
            aria-live="polite"
            aria-label="Manager is thinking"
          >
            <span className="manager-chat-typing-dot" />
            <span className="manager-chat-typing-dot" />
            <span className="manager-chat-typing-dot" />
          </div>
        ) : null}
      </div>
      {error ? <div className="error-message">{error}</div> : null}
      <form className="manager-chat-form" onSubmit={onSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={
            mode === 'epk_builder'
              ? 'Describe your EPK changes…'
              : 'Message your manager…'
          }
          disabled={busy}
        />
        <button type="submit" className="portal-btn portal-btn--primary" disabled={busy}>
          {busy ? '…' : mode === 'epk_builder' ? 'Update EPK' : 'Send'}
        </button>
      </form>
    </div>
  );
}

export default ManagerChat;
