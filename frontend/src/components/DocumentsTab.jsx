import React from 'react';
import { FileText, Layers, Trash2, CheckCircle, Clock, AlertTriangle, RefreshCw, Cpu, Database } from 'lucide-react';

export default function DocumentsTab({
  documents,
  health,
  onDeleteDoc,
  onReprocessDoc,
  onRebuildIndex,
  reprocessingDocId,
  rebuildingIndex,
  rebuildMessage
}) {
  const formatBytes = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const formatDate = (isoStr) => {
    if (!isoStr) return '-';
    try {
      return new Date(isoStr).toLocaleString();
    } catch (e) {
      return isoStr;
    }
  };

  const getMethodBadge = (method) => {
    switch (method) {
      case 'native':
        return <span className="badge badge-info" style={{ fontSize: '0.7rem' }}>Native PDF</span>;
      case 'ocr':
        return <span className="badge badge-success" style={{ fontSize: '0.7rem' }}>OCR Extracted</span>;
      case 'ocr_required':
      case 'pending':
        return <span className="badge badge-warning" style={{ fontSize: '0.7rem' }}>OCR Pending</span>;
      default:
        return <span className="badge" style={{ background: 'rgba(255,255,255,0.05)', color: 'var(--text-dim)', fontSize: '0.7rem' }}>-</span>;
    }
  };

  const getStatusBadge = (doc) => {
    switch (doc.status) {
      case 'ready':
        return <span className="badge badge-success"><CheckCircle size={10} /> Ready</span>;
      case 'ocr_required':
        return (
          <span className="badge badge-warning" style={{ background: 'rgba(245, 158, 11, 0.2)', color: '#fbbf24', borderColor: 'rgba(245, 158, 11, 0.4)' }} title={doc.error_message || 'OCR Required'}>
            <AlertTriangle size={10} /> OCR Required
          </span>
        );
      case 'ocr_processing':
        return (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <span className="badge badge-warning animate-pulse-slow">
              <Clock size={10} /> {doc.error_message || `OCR Page ${doc.current_page}/${doc.total_pages}`}
            </span>
            {doc.total_pages > 0 && (
              <div style={{ width: '100px', height: '4px', background: 'rgba(255,255,255,0.1)', borderRadius: '2px', overflow: 'hidden' }}>
                <div style={{ width: `${doc.progress_percent || 0}%`, height: '100%', background: 'var(--accent-amber)', transition: 'width 0.3s' }} />
              </div>
            )}
          </div>
        );
      case 'failed':
      case 'ocr_failed':
      case 'indexing_failed':
        return (
          <span className="badge badge-danger" title={doc.error_message || 'Failed'}>
            <AlertTriangle size={10} /> Failed
          </span>
        );
      default:
        return (
          <span className="badge badge-warning animate-pulse-slow">
            <Clock size={10} /> {doc.status.toUpperCase()}
          </span>
        );
    }
  };

  const isOutOfSync = health && !health.index_in_sync;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '20px', overflowY: 'auto' }}>
      
      {/* Diagnostic & Vector Store Health Header */}
      <div className="glass-card" style={{ padding: '20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h2 style={{ fontSize: '1.2rem', color: '#fff', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Database size={20} color="var(--primary)" /> Document & Vector Store Diagnostics
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginTop: '4px' }}>
            Persistent SQLite database contains <strong style={{ color: '#fff' }}>{health?.total_chunks ?? 0}</strong> chunks across <strong style={{ color: '#fff' }}>{health?.ready_documents_count ?? 0}</strong> ready documents. FAISS contains <strong style={{ color: isOutOfSync ? 'var(--accent-amber)' : 'var(--accent-emerald)' }}>{health?.faiss_total_vectors ?? 0}</strong> indexed vectors.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {isOutOfSync ? (
            <span className="badge badge-warning" style={{ padding: '6px 12px' }}>
              <AlertTriangle size={12} /> Index Out of Sync
            </span>
          ) : (
            <span className="badge badge-success" style={{ padding: '6px 12px' }}>
              <CheckCircle size={12} /> Index In Sync
            </span>
          )}

          <button
            onClick={onRebuildIndex}
            disabled={rebuildingIndex}
            className="btn-primary"
            style={{ fontSize: '0.85rem' }}
          >
            <RefreshCw size={14} className={rebuildingIndex ? "animate-pulse-slow" : ""} />
            {rebuildingIndex ? "Rebuilding FAISS..." : "Rebuild FAISS Index"}
          </button>
        </div>
      </div>

      {rebuildMessage && (
        <div style={{ padding: '10px 16px', borderRadius: '8px', background: 'rgba(16, 185, 129, 0.15)', border: '1px solid rgba(16, 185, 129, 0.3)', color: 'var(--accent-emerald)', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <CheckCircle size={16} />
          <span>{rebuildMessage}</span>
        </div>
      )}

      {documents.length === 0 ? (
        <div className="glass-panel" style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
          <FileText size={40} color="var(--text-dim)" style={{ margin: '0 auto 16px auto', display: 'block' }} />
          <h3 style={{ fontSize: '1.1rem', color: '#fff', marginBottom: '8px' }}>No Documents Registered</h3>
          <p style={{ fontSize: '0.85rem' }}>Upload a PDF using the sidebar to index it into the local FAISS vector store.</p>
        </div>
      ) : (
        <div className="glass-card" style={{ padding: '0', overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left', fontSize: '0.85rem' }}>
            <thead>
              <tr style={{ background: 'rgba(15, 23, 42, 0.8)', borderBottom: '1px solid var(--border-color)', color: 'var(--text-muted)' }}>
                <th style={{ padding: '14px 18px' }}>Document Name</th>
                <th style={{ padding: '14px 18px' }}>Pages</th>
                <th style={{ padding: '14px 18px' }}>Size</th>
                <th style={{ padding: '14px 18px' }}>Chunks</th>
                <th style={{ padding: '14px 18px' }}>Method</th>
                <th style={{ padding: '14px 18px' }}>Status</th>
                <th style={{ padding: '14px 18px' }}>Uploaded At</th>
                <th style={{ padding: '14px 18px', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.document_id} style={{ borderBottom: '1px solid var(--border-color)' }}>
                  
                  {/* Document Name */}
                  <td style={{ padding: '14px 18px', fontWeight: 600, color: '#fff' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <FileText size={16} color="var(--primary)" />
                      <span>{doc.filename}</span>
                    </div>
                  </td>

                  {/* Pages */}
                  <td style={{ padding: '14px 18px', color: 'var(--text-main)' }}>{doc.total_pages || '-'}</td>

                  {/* Size */}
                  <td style={{ padding: '14px 18px', color: 'var(--text-main)' }}>{formatBytes(doc.file_size_bytes)}</td>

                  {/* Chunks */}
                  <td style={{ padding: '14px 18px', color: 'var(--text-main)' }}>
                    <span className="badge badge-info">{doc.chunk_count || 0}</span>
                  </td>

                  {/* Method */}
                  <td style={{ padding: '14px 18px' }}>
                    {getMethodBadge(doc.extraction_method || (doc.chunk_count > 0 ? 'native' : 'pending'))}
                  </td>

                  {/* Status */}
                  <td style={{ padding: '14px 18px' }}>
                    {getStatusBadge(doc)}
                  </td>

                  {/* Date */}
                  <td style={{ padding: '14px 18px', color: 'var(--text-dim)' }}>{formatDate(doc.created_at)}</td>

                  {/* Actions */}
                  <td style={{ padding: '14px 18px', textAlign: 'right' }}>
                    <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', alignItems: 'center' }}>
                      
                      {/* Reprocess OCR Button */}
                      {(doc.status === 'ocr_required' || doc.chunk_count === 0 || doc.status === 'failed') && (
                        <button
                          onClick={() => onReprocessDoc(doc.document_id)}
                          disabled={reprocessingDocId === doc.document_id}
                          className="btn-secondary"
                          style={{ padding: '4px 8px', fontSize: '0.75rem', color: 'var(--accent-amber)', borderColor: 'rgba(245, 158, 11, 0.4)' }}
                          title="Re-run OCR extraction pipeline"
                        >
                          <RefreshCw size={12} className={reprocessingDocId === doc.document_id ? "animate-pulse-slow" : ""} />
                          {reprocessingDocId === doc.document_id ? "OCR..." : "Run OCR"}
                        </button>
                      )}

                      {/* Delete */}
                      <button
                        onClick={() => onDeleteDoc(doc.document_id)}
                        className="btn-secondary"
                        style={{ color: 'var(--accent-rose)', border: 'none', background: 'transparent', padding: '6px' }}
                        title="Delete document and remove vectors"
                      >
                        <Trash2 size={16} />
                      </button>

                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

    </div>
  );
}
