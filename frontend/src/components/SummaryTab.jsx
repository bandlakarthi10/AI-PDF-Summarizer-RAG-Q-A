import React, { useState } from 'react';
import { FileText, Sparkles, ShieldAlert, CheckSquare, ListChecks, RefreshCw, AlertTriangle } from 'lucide-react';

export default function SummaryTab({
  documents,
  onGenerateSummary,
  onReprocessDoc,
  loadingSummary,
  reprocessingDocId,
  currentSummary
}) {
  const [selectedDocId, setSelectedDocId] = useState(documents[0]?.document_id || '');
  const [summaryType, setSummaryType] = useState('medium');

  // Find currently selected document metadata
  const selectedDoc = documents.find(d => d.document_id === selectedDocId) || documents[0];

  const handleGenerate = () => {
    if (!selectedDocId || !selectedDoc || selectedDoc.chunk_count === 0 || selectedDoc.status !== 'ready') return;
    onGenerateSummary(selectedDocId, summaryType);
  };

  const isOCRRequired = selectedDoc && (selectedDoc.status === 'ocr_required' || selectedDoc.chunk_count === 0);
  const isProcessing = selectedDoc && ['uploaded', 'processing', 'extracting', 'ocr_processing', 'chunking', 'embedding', 'indexing'].includes(selectedDoc.status);
  const isReady = selectedDoc && selectedDoc.status === 'ready' && selectedDoc.chunk_count > 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', gap: '20px', overflowY: 'auto', paddingRight: '6px' }}>
      
      {/* Summary Controls Bar */}
      <div className="glass-card" style={{ padding: '20px', display: 'flex', flexWrap: 'wrap', gap: '16px', alignItems: 'center', justifyContent: 'space-between' }}>
        
        {/* Document Selection Dropdown */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 500 }}>Select PDF Document:</label>
          <select
            value={selectedDocId || selectedDoc?.document_id || ''}
            onChange={(e) => setSelectedDocId(e.target.value)}
            disabled={documents.length === 0 || loadingSummary}
            style={{
              background: 'rgba(15, 23, 42, 0.8)',
              border: '1px solid var(--border-color)',
              borderRadius: '8px',
              padding: '8px 14px',
              color: '#fff',
              fontSize: '0.85rem',
              outline: 'none'
            }}
          >
            {documents.length === 0 ? (
              <option value="">No documents available</option>
            ) : (
              documents.map(d => (
                <option key={d.document_id} value={d.document_id}>
                  {d.filename} ({d.total_pages || 0} pages • {d.chunk_count || 0} chunks • {d.status.toUpperCase()})
                </option>
              ))
            )}
          </select>
        </div>

        {/* Summary Length Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 500 }}>Summary Length:</label>
          <div style={{ display: 'flex', gap: '4px', background: 'rgba(15, 23, 42, 0.8)', padding: '4px', borderRadius: '8px', border: '1px solid var(--border-color)' }}>
            {['short', 'medium', 'detailed'].map((type) => (
              <button
                key={type}
                onClick={() => setSummaryType(type)}
                disabled={!isReady || loadingSummary}
                style={{
                  padding: '6px 12px',
                  borderRadius: '6px',
                  border: 'none',
                  fontSize: '0.8rem',
                  fontWeight: 500,
                  cursor: isReady ? 'pointer' : 'not-allowed',
                  textTransform: 'capitalize',
                  background: summaryType === type ? 'var(--primary)' : 'transparent',
                  color: summaryType === type ? '#fff' : 'var(--text-muted)',
                  opacity: isReady ? 1 : 0.5
                }}
              >
                {type}
              </button>
            ))}
          </div>
        </div>

        {/* Action Button */}
        <button
          onClick={handleGenerate}
          disabled={!isReady || loadingSummary}
          className="btn-primary"
          title={!isReady ? "Document must be in READY state with extractable chunks" : "Generate Map-Reduce summary"}
        >
          {loadingSummary ? <RefreshCw size={16} className="animate-pulse-slow" /> : <Sparkles size={16} />}
          {loadingSummary ? 'Summarizing PDF...' : 'Generate Summary'}
        </button>

      </div>

      {/* OCR Required Alert Card */}
      {isOCRRequired && (
        <div className="glass-card" style={{ padding: '20px', borderColor: 'rgba(245, 158, 11, 0.4)', background: 'rgba(245, 158, 11, 0.08)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
            <AlertTriangle size={24} color="var(--accent-amber)" style={{ marginTop: '2px', flexShrink: 0 }} />
            <div>
              <h4 style={{ fontSize: '0.95rem', color: '#fbbf24', fontWeight: 600 }}>OCR Processing Required</h4>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-main)', marginTop: '4px' }}>
                '{selectedDoc?.filename}' contains vector outline or scanned content with 0 extractable text characters. Run multi-stage OCR to extract text and generate chunks.
              </p>
            </div>
          </div>
          <button
            onClick={() => onReprocessDoc(selectedDoc.document_id)}
            disabled={reprocessingDocId === selectedDoc.document_id}
            className="btn-primary"
            style={{ background: 'var(--accent-amber)', color: '#000', fontWeight: 600, flexShrink: 0 }}
          >
            <RefreshCw size={14} className={reprocessingDocId === selectedDoc.document_id ? "animate-pulse-slow" : ""} />
            {reprocessingDocId === selectedDoc.document_id ? 'Running OCR...' : 'Re-process with OCR'}
          </button>
        </div>
      )}

      {/* Processing State Alert Card */}
      {isProcessing && (
        <div className="glass-card" style={{ padding: '20px', borderColor: 'rgba(6, 182, 212, 0.4)', background: 'rgba(6, 182, 212, 0.08)', display: 'flex', alignItems: 'center', gap: '12px' }}>
          <RefreshCw size={22} color="var(--accent-cyan)" className="animate-pulse-slow" />
          <div>
            <h4 style={{ fontSize: '0.95rem', color: 'var(--accent-cyan)', fontWeight: 600 }}>Document is currently processing ({selectedDoc?.status.toUpperCase()})</h4>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-main)', marginTop: '2px' }}>
              {selectedDoc?.error_message || 'Extracting pages, generating chunks, and indexing into FAISS vector store...'}
            </p>
          </div>
        </div>
      )}

      {/* Summary Display Content */}
      {loadingSummary ? (
        <div className="glass-panel" style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
          <Sparkles size={40} color="var(--primary)" style={{ margin: '0 auto 16px auto', display: 'block' }} className="animate-pulse-slow" />
          <h3 style={{ fontSize: '1.2rem', color: '#fff', marginBottom: '8px' }}>Generating Map-Reduce Summary</h3>
          <p style={{ fontSize: '0.85rem', maxWidth: '450px', margin: '0 auto' }}>
            Processing document chunks in parallel batches and consolidating key procedures, warnings, and overview...
          </p>
        </div>
      ) : !currentSummary ? (
        <div className="glass-panel" style={{ padding: '60px', textAlign: 'center', color: 'var(--text-muted)' }}>
          <FileText size={40} color="var(--text-dim)" style={{ margin: '0 auto 16px auto', display: 'block' }} />
          <h3 style={{ fontSize: '1.1rem', color: '#fff', marginBottom: '8px' }}>No Summary Generated Yet</h3>
          <p style={{ fontSize: '0.85rem', maxWidth: '460px', margin: '0 auto' }}>
            {isReady
              ? `Select length and click "Generate Summary" to create a structured executive breakdown of '${selectedDoc?.filename}'.`
              : 'Select a READY document above with indexed chunks to generate an AI summary.'}
          </p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          
          {/* Overview */}
          {currentSummary.overview && (
            <div className="glass-card" style={{ padding: '20px' }}>
              <h3 style={{ fontSize: '1.1rem', color: '#fff', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Sparkles size={18} color="var(--primary)" /> Executive Overview
              </h3>
              <p style={{ fontSize: '0.95rem', lineHeight: '1.6', color: 'var(--text-main)' }}>
                {currentSummary.overview}
              </p>
            </div>
          )}

          {/* Key Points */}
          {currentSummary.key_points && currentSummary.key_points.length > 0 && (
            <div className="glass-card" style={{ padding: '20px' }}>
              <h3 style={{ fontSize: '1.1rem', color: '#fff', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ListChecks size={18} color="var(--accent-cyan)" /> Key Points & Requirements
              </h3>
              <ul style={{ paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {currentSummary.key_points.map((point, i) => (
                  <li key={i} style={{ fontSize: '0.9rem', color: 'var(--text-main)', lineHeight: '1.5' }}>
                    {point}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Important Procedures */}
          {currentSummary.important_procedures && currentSummary.important_procedures.length > 0 && (
            <div className="glass-card" style={{ padding: '20px' }}>
              <h3 style={{ fontSize: '1.1rem', color: '#fff', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <CheckSquare size={18} color="var(--accent-emerald)" /> Important Procedures & Instructions
              </h3>
              <ul style={{ paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {currentSummary.important_procedures.map((proc, i) => (
                  <li key={i} style={{ fontSize: '0.9rem', color: 'var(--text-main)', lineHeight: '1.5' }}>
                    {proc}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Warnings & Safety */}
          {currentSummary.warnings && currentSummary.warnings.length > 0 && (
            <div className="glass-card" style={{ padding: '20px', borderColor: 'rgba(244, 63, 94, 0.3)', background: 'rgba(244, 63, 94, 0.05)' }}>
              <h3 style={{ fontSize: '1.1rem', color: 'var(--accent-rose)', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ShieldAlert size={18} color="var(--accent-rose)" /> Warnings & Safety Notes
              </h3>
              <ul style={{ paddingLeft: '20px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {currentSummary.warnings.map((warn, i) => (
                  <li key={i} style={{ fontSize: '0.9rem', color: '#fff', lineHeight: '1.5' }}>
                    {warn}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Conclusion */}
          {currentSummary.conclusions && (
            <div className="glass-card" style={{ padding: '20px' }}>
              <h3 style={{ fontSize: '1.1rem', color: '#fff', marginBottom: '10px' }}>Conclusion</h3>
              <p style={{ fontSize: '0.9rem', lineHeight: '1.6', color: 'var(--text-main)' }}>
                {currentSummary.conclusions}
              </p>
            </div>
          )}

        </div>
      )}

    </div>
  );
}
