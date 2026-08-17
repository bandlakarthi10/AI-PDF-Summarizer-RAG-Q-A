import React, { useRef } from 'react';
import { UploadCloud, FileText, Trash2, CheckCircle, Clock, AlertTriangle, Layers, RefreshCw } from 'lucide-react';

export default function Sidebar({
  documents,
  selectedDocIds,
  onToggleDocSelect,
  onUploadFile,
  onDeleteDoc,
  onReprocessDoc,
  uploading,
  uploadError,
  reprocessingDocId
}) {
  const fileInputRef = useRef(null);

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      onUploadFile(e.target.files[0]);
      e.target.value = '';
    }
  };

  const getStatusBadge = (doc) => {
    switch (doc.status) {
      case 'ready':
        return <span className="badge badge-success"><CheckCircle size={10} /> Ready</span>;
      case 'ocr_processing':
        return (
          <span className="badge badge-warning animate-pulse-slow" title={doc.error_message || 'OCR Processing'}>
            <Clock size={10} /> {doc.error_message || `OCR Page ${doc.current_page}/${doc.total_pages}`}
          </span>
        );
      case 'uploaded':
      case 'processing':
      case 'extracting':
      case 'chunking':
      case 'embedding':
      case 'indexing':
        return (
          <span className="badge badge-warning animate-pulse-slow">
            <Clock size={10} /> {doc.status.toUpperCase()}...
          </span>
        );
      case 'ocr_required':
        return (
          <span className="badge badge-warning" style={{ background: 'rgba(245, 158, 11, 0.2)', color: '#fbbf24', borderColor: 'rgba(245, 158, 11, 0.4)' }} title={doc.error_message || 'OCR Required (0 chunks)'}>
            <AlertTriangle size={10} /> OCR Required
          </span>
        );
      case 'failed':
      case 'ocr_failed':
      case 'indexing_failed':
        return (
          <span className="badge badge-danger" title={doc.error_message || 'Processing failed'}>
            <AlertTriangle size={10} /> Failed
          </span>
        );
      default:
        return <span className="badge badge-info">{doc.status}</span>;
    }
  };

  const formatBytes = (bytes) => {
    if (!bytes) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  return (
    <aside className="glass-panel" style={{ width: '320px', minWidth: '320px', height: 'calc(100vh - 65px)', padding: '20px', display: 'flex', flexDirection: 'column', gap: '20px', borderRadius: 0, borderTop: 0, borderBottom: 0, borderLeft: 0 }}>
      
      {/* Upload Box */}
      <div>
        <h3 style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.5px', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <UploadCloud size={16} color="var(--primary)" /> Upload PDF Manual
        </h3>

        <div
          onClick={() => !uploading && fileInputRef.current?.click()}
          style={{
            border: '2px dashed rgba(99, 102, 241, 0.4)',
            borderRadius: '12px',
            padding: '24px 16px',
            textAlign: 'center',
            cursor: uploading ? 'not-allowed' : 'pointer',
            background: 'rgba(99, 102, 241, 0.04)',
            transition: 'var(--transition)'
          }}
          onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--primary)'}
          onMouseLeave={(e) => e.currentTarget.style.borderColor = 'rgba(99, 102, 241, 0.4)'}
        >
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            accept="application/pdf,.pdf"
            style={{ display: 'none' }}
            disabled={uploading}
          />
          <UploadCloud size={32} color="var(--primary)" style={{ margin: '0 auto 8px auto', display: 'block' }} />
          <p style={{ fontSize: '0.85rem', fontWeight: 600, color: '#fff' }}>
            {uploading ? 'Processing PDF Pipeline...' : 'Click to Upload PDF'}
          </p>
          <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '4px' }}>
            PDF files up to 50MB
          </p>
        </div>

        {uploadError && (
          <div style={{ marginTop: '10px', padding: '8px 12px', borderRadius: '8px', background: 'rgba(244, 63, 94, 0.15)', border: '1px solid rgba(244, 63, 94, 0.3)', color: 'var(--accent-rose)', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <AlertTriangle size={14} />
            <span>{uploadError}</span>
          </div>
        )}
      </div>

      {/* Document Filter Header */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
          <h3 style={{ fontSize: '0.85rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Layers size={16} color="var(--accent-cyan)" /> Uploaded PDFs ({documents.length})
          </h3>
          {selectedDocIds.length > 0 && (
            <span style={{ fontSize: '0.75rem', color: 'var(--accent-cyan)' }}>
              {selectedDocIds.length} scoped
            </span>
          )}
        </div>

        {/* Documents List */}
        <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '10px', paddingRight: '4px' }}>
          {documents.length === 0 ? (
            <div style={{ textTransform: 'none', textAlign: 'center', padding: '30px 10px', color: 'var(--text-dim)', fontSize: '0.85rem' }}>
              No PDFs uploaded yet. Upload a document to start asking questions or generating summaries.
            </div>
          ) : (
            documents.map((doc) => {
              const isSelected = selectedDocIds.includes(doc.document_id);
              const isOCRReq = doc.status === 'ocr_required' || doc.chunk_count === 0;
              return (
                <div
                  key={doc.document_id}
                  className="glass-card"
                  style={{
                    padding: '12px',
                    borderColor: isSelected ? 'var(--primary)' : 'var(--border-color)',
                    background: isSelected ? 'rgba(99, 102, 241, 0.1)' : 'var(--bg-card)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px'
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '8px' }}>
                    
                    <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', overflow: 'hidden' }}>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => onToggleDocSelect(doc.document_id)}
                        disabled={doc.status !== 'ready'}
                        style={{ marginTop: '3px', cursor: doc.status === 'ready' ? 'pointer' : 'not-allowed' }}
                        title={doc.status === 'ready' ? "Select for chat scope filter" : "Document not ready for chat"}
                      />
                      <div style={{ overflow: 'hidden' }}>
                        <p style={{ fontSize: '0.85rem', fontWeight: 600, color: '#fff', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }} title={doc.filename}>
                          {doc.filename}
                        </p>
                        <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', marginTop: '2px' }}>
                          {doc.total_pages > 0 ? `${doc.total_pages} pages` : 'Processing'} • {formatBytes(doc.file_size_bytes)} • {doc.chunk_count} chunks
                        </p>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      {isOCRReq && onReprocessDoc && (
                        <button
                          onClick={() => onReprocessDoc(doc.document_id)}
                          disabled={reprocessingDocId === doc.document_id}
                          className="btn-secondary"
                          style={{ padding: '4px', color: 'var(--accent-amber)', background: 'transparent', border: 'none' }}
                          title="Re-process with OCR"
                        >
                          <RefreshCw size={14} className={reprocessingDocId === doc.document_id ? "animate-pulse-slow" : ""} />
                        </button>
                      )}
                      <button
                        onClick={() => onDeleteDoc(doc.document_id)}
                        className="btn-secondary"
                        style={{ padding: '4px', color: 'var(--accent-rose)', background: 'transparent', border: 'none' }}
                        title="Delete document"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>

                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '2px' }}>
                    {getStatusBadge(doc)}
                  </div>

                </div>
              );
            })
          )}
        </div>
      </div>

    </aside>
  );
}
