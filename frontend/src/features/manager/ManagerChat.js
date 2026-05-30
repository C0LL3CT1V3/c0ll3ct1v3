import React, { useState } from 'react';
import { useManagerChat } from './useManagerChat';

function ManagerChat() {
  const { messages, sendMessage, sending, error } = useManagerChat();
  const [input, setInput] = useState('');

  const onSubmit = (e) => {
    e.preventDefault();
    if (!input.trim()) return;
    sendMessage(input);
    setInput('');
  };

  return (
    <div className="manager-chat">
      <h2 className="portal-panel-title">Manager</h2>
      <div className="manager-chat-messages">
        {messages.map((m, i) => (
          <div key={`${m.role}-${i}`} className={`manager-chat-bubble manager-chat-bubble--${m.role}`}>
            {m.content}
          </div>
        ))}
      </div>
      {error ? <div className="error-message">{error}</div> : null}
      <form className="manager-chat-form" onSubmit={onSubmit}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Message your manager…"
          disabled={sending}
        />
        <button type="submit" className="portal-btn portal-btn--primary" disabled={sending}>
          {sending ? '…' : 'Send'}
        </button>
      </form>
    </div>
  );
}

export default ManagerChat;
