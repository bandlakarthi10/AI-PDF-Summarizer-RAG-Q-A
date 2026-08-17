import React, { useState, useRef, useEffect } from 'react';
import { Send, Bot, User, FileText, Sparkles, BookOpen, AlertCircle, Copy, Check, RefreshCw } from 'lucide-react';

export default function ChatTab({
  messages,
  onSendMessage,
  asking,
  selectedDocIds,
  documents,
  health,
  onRebuildIndex,
  rebuildingIndex
}) {
  const [input, setInput] = useState('');
  const [copiedIdx, setCopiedIdx] = useState(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, asking]);

  const hasVectors = (health?.faiss_total_vectors ?? 0) > 0;

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!input.trim() || asking || !hasVectors) return;
    onSendMessage(input.trim());
    setInput('');
  };

  const handleCopy = (text, idx) => {
    navigator.clipboard.writeText(text);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  const suggestedQuestions = [
    "What is the warranty period and coverage?",
    "What are the key responsibilities and profile details?",
    "Describe the safety procedures and warnings.",
    "Summarize the main topics discussed in the document."
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '16px' }}>
      
      {/* 0-Vector Warning Guard */}
      {!hasVectors && (
        <div className="glass-card" style={{ padding: '16px 20px', borderColor: 'rgba(245, 158, 11, 0.4)', background: 'rgba(245, 158, 11, 0.08)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <AlertCircle size={20} color="var(--accent-amber)" />
            <div>
              <h4 style={{ fontSize: '0.9rem', color: '#fbbf24', fontWeight: 600 }}>Vector Store Empty (0 Vectors Indexed)</h4>
              <p style={{ fontSize: '0.8rem', color: 'var(--text-main)', marginTop: '2px' }}>
                Chat requires indexed document chunks in FAISS. Upload a PDF or click Rebuild Index to synchronize.
              </p>
            </div>
          </div>
          {onRebuildIndex && (
            <button
              onClick={onRebuildIndex}
              disabled={rebuildingIndex}
              className="btn-primary"
              style={{ background: 'var(--accent-amber)', color: '#000', fontSize: '0.8rem', padding: '6px 14px' }}
            >
              <RefreshCw size={12} className={rebuildingIndex ? "animate-pulse-slow" : ""} />
              {rebuildingIndex ? "Rebuilding..." : "Rebuild Index"}
            </button>
          )}
        </div>
      )}

      {/* Message History Area */}
      <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '16px', paddingRight: '6px' }}>
        
        {messages.length === 0 ? (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            textAlign: 'center',
            color: 'var(--text-muted)',
            padding: '40px 20px'
          }}>
            <div style={{
              background: 'rgba(99, 102, 241, 0.1)',
              padding: '20px',
              borderRadius: '50%',
              marginBottom: '16px',
              border: '1px solid rgba(99, 102, 241, 0.2)'
            }}>
              <Sparkles size={36} color="var(--primary)" />
            </div>
            <h2 style={{ fontSize: '1.4rem', color: '#fff', marginBottom: '8px' }}>
              Ask Questions About Your Documents
            </h2>
            <p style={{ fontSize: '0.9rem', maxWidth: '500px', marginBottom: '24px' }}>
              Upload PDF manuals and ask questions. Answers are strictly grounded in your documents with exact page citations.
            </p>

            {/* Suggested Question Pills */}
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', justifyContent: 'center', maxWidth: '640px' }}>
              {suggestedQuestions.map((q, idx) => (
                <button
                  key={idx}
                  onClick={() => hasVectors && onSendMessage(q)}
                  disabled={!hasVectors || asking}
                  className="btn-secondary"
                  style={{ borderRadius: '20px', padding: '8px 16px', opacity: hasVectors ? 1 : 0.5 }}
                >
                  <BookOpen size={14} color="var(--accent-cyan)" /> {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div
              key={idx}
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: msg.role === 'user' ? 'flex-end' : 'flex-start',
                gap: '8px'
              }}
            >
              <div
                style={{
                  display: 'flex',
                  gap: '12px',
                  maxWidth: '85%',
                  alignItems: 'flex-start',
                  flexDirection: msg.role === 'user' ? 'row-reverse' : 'row'
                }}
              >
                {/* Avatar */}
                <div style={{
                  width: '36px',
                  height: '36px',
                  borderRadius: '10px',
                  background: msg.role === 'user' ? 'linear-gradient(135deg, #06b6d4 0%, #3b82f6 100%)' : 'linear-gradient(135deg, #6366f1 0%, #4f46e5 100%)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  flexShrink: 0
                }}>
                  {msg.role === 'user' ? <User size={18} color="#fff" /> : <Bot size={18} color="#fff" />}
                </div>

                {/* Content Bubble */}
                <div
                  className="glass-card"
                  style={{
                    padding: '16px 20px',
                    borderRadius: msg.role === 'user' ? '16px 4px 16px 16px' : '4px 16px 16px 16px',
                    background: msg.role === 'user' ? 'rgba(6, 182, 212, 0.12)' : 'var(--bg-card)',
                    borderColor: msg.role === 'user' ? 'rgba(6, 182, 212, 0.3)' : 'var(--border-color)',
                    whiteSpace: 'pre-wrap',
                    fontSize: '0.95rem',
                    lineHeight: '1.6'
                  }}
                >
                  <div>{msg.content}</div>

                  {/* Copy Answer Button */}
                  {msg.role === 'assistant' && (
                    <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '8px' }}>
                      <button
                        onClick={() => handleCopy(msg.content, idx)}
                        style={{ background: 'none', border: 'none', color: 'var(--text-dim)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem' }}
                      >
                        {copiedIdx === idx ? <Check size={12} color="var(--accent-emerald)" /> : <Copy size={12} />}
                        {copiedIdx === idx ? 'Copied' : 'Copy'}
                      </button>
                    </div>
                  )}
                </div>
              </div>

              {/* Source Citation Cards */}
              {msg.sources && msg.sources.length > 0 && (
                <div style={{ marginLeft: '48px', maxWidth: '85%', marginTop: '4px' }}>
                  <p style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--accent-cyan)', marginBottom: '6px', display: 'flex', alignItems: 'center', gap: '4px' }}>
                    <FileText size={12} /> Source Page Citations ({msg.sources.length}):
                  </p>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '8px' }}>
                    {msg.sources.map((src, sIdx) => (
                      <div
                        key={sIdx}
                        style={{
                          padding: '10px 14px',
                          borderRadius: '8px',
                          background: 'rgba(15, 23, 42, 0.6)',
                          border: '1px solid rgba(6, 182, 212, 0.2)',
                          fontSize: '0.8rem'
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                          <span style={{ fontWeight: 600, color: '#fff' }}>{src.filename}</span>
                          <span className="badge badge-info" style={{ fontSize: '0.65rem' }}>Page {src.page_number}</span>
                        </div>
                        <p style={{ color: 'var(--text-muted)', fontSize: '0.75rem', display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}>
                          "{src.snippet}"
                        </p>
                        <div style={{ textAlign: 'right', marginTop: '4px', fontSize: '0.7rem', color: 'var(--text-dim)' }}>
                          Relevance Score: {(src.score * 100).toFixed(1)}%
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

            </div>
          ))
        )}

        {asking && (
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <div style={{ width: '36px', height: '36px', borderRadius: '10px', background: 'var(--primary)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Bot size={18} color="#fff" />
            </div>
            <div className="glass-card" style={{ padding: '12px 18px', color: 'var(--text-muted)', fontSize: '0.85rem' }}>
              <span className="animate-pulse-slow">Retrieving relevant context & generating grounded answer with llama3.2...</span>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Question Input Form */}
      <form onSubmit={handleSubmit} style={{ display: 'flex', gap: '10px' }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={
            !hasVectors
              ? "Chat unavailable: No indexed document content found. Please upload a PDF first."
              : selectedDocIds.length > 0
              ? `Ask question scoped to ${selectedDocIds.length} selected document(s)...`
              : "Ask a question about your uploaded documents..."
          }
          disabled={asking || !hasVectors}
          style={{
            flex: 1,
            background: 'var(--bg-card)',
            border: '1px solid var(--border-color)',
            borderRadius: '10px',
            padding: '14px 18px',
            color: '#fff',
            fontSize: '0.95rem',
            outline: 'none',
            opacity: hasVectors ? 1 : 0.6
          }}
        />
        <button
          type="submit"
          disabled={asking || !input.trim() || !hasVectors}
          className="btn-primary"
          style={{ padding: '0 24px' }}
        >
          <Send size={18} /> Ask
        </button>
      </form>

    </div>
  );
}
