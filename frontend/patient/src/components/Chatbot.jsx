import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';

const API_BASE = 'http://localhost:8000';

function Chatbot({ patientId }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: "Hello! I'm the MediSearch Triage Assistant. Please describe your primary symptom." }
  ]);
  const [input, setInput] = useState('');
  const [sessionId, setSessionId] = useState('');
  const [loading, setLoading] = useState(false);
  const [complete, setComplete] = useState(false);

  const endRef = useRef(null);
  const inputRef = useRef(null);
  const navigate = useNavigate();

  useEffect(() => {
    setSessionId(`sess_${Date.now()}_${Math.floor(Math.random() * 10000)}`);
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || loading || complete) return;

    const userMsg = input.trim();
    setInput('');
    const newMessages = [...messages, { role: 'user', content: userMsg }];
    setMessages(newMessages);
    setLoading(true);

    try {
      // 1. Post user message to get the next turn from the keyword state machine
      const resp = await fetch(`${API_BASE}/chatbot/next`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          message: userMsg,
          patient_id: patientId
        })
      });
      const data = await resp.json();

      if (data.complete) {
        setComplete(true);
        setMessages(prev => [...prev, { role: 'assistant', content: data.reply || 'Thank you. Processing your assessment...' }]);
        
        // 2. Finalize triage to run BM25 and persist the case/report
        const finalizeResp = await fetch(`${API_BASE}/chatbot/finalize`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: sessionId,
            patient_id: patientId
          })
        });
        const reportRaw = await finalizeResp.json();
        
        setTimeout(() => {
           navigate('/result', { state: { report: reportRaw } });
        }, 1200);

      } else {
        setMessages(prev => [...prev, { role: 'assistant', content: data.reply }]);
      }
    } catch (err) {
      console.error(err);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '⚠️ Failed to reach the triage engine.'
      }]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-messages">
        {messages.map((m, i) => (
          <div key={i} className={`chat-bubble ${m.role === 'user' ? 'user' : 'bot'}`}>
            {m.content}
          </div>
        ))}
        {loading && (
          <div className="typing-indicator">
            <span></span><span></span><span></span>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <form onSubmit={handleSend} className="chat-input-row">
        <input
          ref={inputRef}
          autoFocus
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          className="input-field"
          placeholder={complete ? "Assessment complete..." : "Type your response..."}
          disabled={loading || complete}
        />
        <button type="submit" className="btn btn-primary" disabled={loading || complete || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}

export default Chatbot;
