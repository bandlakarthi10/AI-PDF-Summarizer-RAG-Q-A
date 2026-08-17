import React from 'react';
import { Cpu, Database, Bot, FileText, CheckCircle2, AlertCircle, RefreshCw, Layers } from 'lucide-react';

export default function Navbar({ health, onRebuildIndex, rebuildingIndex }) {
  const getOllamaBadge = () => {
    if (!health) return <span className="badge badge-warning">Connecting...</span>;
    if (health.ollama === 'available') {
      return (
        <span className="badge badge-success" title={`Model: ${health.ollama_model}`}>
          <span style={{ display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%', background: 'currentColor' }} />
          Ollama Ready ({health.ollama_model})
        </span>
      );
    }
    if (health.ollama === 'model_missing') {
      return (
        <span className="badge badge-warning">
          <AlertCircle size={12} /> Pull Model (`ollama pull {health.ollama_model}`)
        </span>
      );
    }
    return (
      <span className="badge badge-danger">
        <AlertCircle size={12} /> Ollama Offline (`ollama serve`)
      </span>
    );
  };

  const isOutOfSync = health && !health.index_in_sync;

  return (
    <header className="glass-panel" style={{ borderRadius: 0, borderTop: 0, borderLeft: 0, borderRight: 0, padding: '12px 28px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', maxWidth: '1440px', margin: '0 auto' }}>
        
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <div style={{
            background: 'linear-gradient(135deg, #6366f1 0%, #06b6d4 100%)',
            padding: '10px',
            borderRadius: '10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 12px rgba(99, 102, 241, 0.3)'
          }}>
            <FileText size={22} color="#fff" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.2rem', fontWeight: 700, background: 'linear-gradient(90deg, #fff 0%, #cbd5e1 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              AI PDF Summarizer & RAG Q&A
            </h1>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Local Semantic Search & Map-Reduce Summarization
            </p>
          </div>
        </div>

        {/* Diagnostic Metrics Status Bar */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
          
          {/* Embedding Status */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: 'var(--text-muted)', background: 'rgba(15, 23, 42, 0.6)', padding: '6px 12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <Cpu size={14} color="var(--accent-cyan)" />
            <span>Embedding:</span>
            <span style={{ color: '#fff', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%', background: 'var(--accent-cyan)' }} />
              {health?.embedding_model_name ? health.embedding_model_name.split('/')[1] || health.embedding_model_name : 'bge-small-en-v1.5'}
            </span>
          </div>

          {/* Vector Store Count */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: 'var(--text-muted)', background: 'rgba(15, 23, 42, 0.6)', padding: '6px 12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <Database size={14} color={isOutOfSync ? 'var(--accent-amber)' : 'var(--accent-emerald)'} />
            <span>Vectors:</span>
            <span style={{ color: isOutOfSync ? 'var(--accent-amber)' : '#fff', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%', background: isOutOfSync ? 'var(--accent-amber)' : 'var(--accent-emerald)' }} />
              {health?.faiss_total_vectors ?? 0}
            </span>
          </div>

          {/* Documents Count */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.8rem', color: 'var(--text-muted)', background: 'rgba(15, 23, 42, 0.6)', padding: '6px 12px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            <Layers size={14} color="var(--primary)" />
            <span>Documents:</span>
            <span style={{ color: '#fff', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ display: 'inline-block', width: '6px', height: '6px', borderRadius: '50%', background: 'var(--primary)' }} />
              {health?.ready_documents_count ?? 0} Ready
            </span>
          </div>

          {/* Index Sync Status Badge / Quick Action */}
          {isOutOfSync ? (
            <button
              onClick={onRebuildIndex}
              disabled={rebuildingIndex}
              className="badge badge-warning"
              style={{ cursor: 'pointer', border: '1px solid var(--accent-amber)', padding: '6px 10px', fontSize: '0.75rem', gap: '6px' }}
              title="Click to rebuild and synchronize FAISS index"
            >
              <RefreshCw size={12} className={rebuildingIndex ? "animate-pulse-slow" : ""} />
              {rebuildingIndex ? "Syncing..." : "Sync Index"}
            </button>
          ) : (
            <span className="badge badge-success" style={{ padding: '6px 10px', fontSize: '0.75rem' }}>
              <CheckCircle2 size={12} /> In Sync
            </span>
          )}

          {/* Ollama Status */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Bot size={16} color="var(--primary)" />
            {getOllamaBadge()}
          </div>

        </div>

      </div>
    </header>
  );
}
