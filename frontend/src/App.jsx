import React, { useState, useEffect } from 'react';
import Navbar from './components/Navbar';
import Sidebar from './components/Sidebar';
import ChatTab from './components/ChatTab';
import SummaryTab from './components/SummaryTab';
import DocumentsTab from './components/DocumentsTab';
import { api } from './services/api';
import { MessageSquare, FileText, Layers } from 'lucide-react';

export default function App() {
  const [activeTab, setActiveTab] = useState('chat'); // 'chat' | 'summary' | 'documents'
  const [health, setHealth] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [selectedDocIds, setSelectedDocIds] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);

  // Background action states
  const [reprocessingDocId, setReprocessingDocId] = useState(null);
  const [rebuildingIndex, setRebuildingIndex] = useState(false);
  const [rebuildMessage, setRebuildMessage] = useState(null);

  // Chat state
  const [messages, setMessages] = useState([]);
  const [asking, setAsking] = useState(false);
  const [conversationId, setConversationId] = useState(null);

  // Summary state
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [currentSummary, setCurrentSummary] = useState(null);

  // 1. Fetch health check
  const fetchHealth = async () => {
    try {
      const data = await api.getHealth();
      setHealth(data);
    } catch (err) {
      console.error('Health check failed:', err);
    }
  };

  // 2. Fetch documents list
  const fetchDocuments = async () => {
    try {
      const docs = await api.listDocuments();
      setDocuments(docs);
    } catch (err) {
      console.error('Failed to list documents:', err);
    }
  };

  useEffect(() => {
    fetchHealth();
    fetchDocuments();

    // Poll health every 8s
    const healthInterval = setInterval(fetchHealth, 8000);
    return () => clearInterval(healthInterval);
  }, []);

  // Poll document processing status if any document is processing
  useEffect(() => {
    const isProcessing = documents.some(d => 
      ['uploaded', 'processing', 'extracting', 'ocr_processing', 'chunking', 'embedding', 'indexing'].includes(d.status)
    );

    if (isProcessing || reprocessingDocId) {
      const docInterval = setInterval(() => {
        fetchDocuments();
        fetchHealth();
      }, 2500);
      return () => clearInterval(docInterval);
    }
  }, [documents, reprocessingDocId]);

  // Handle document upload
  const handleUploadFile = async (file) => {
    setUploading(true);
    setUploadError(null);
    try {
      await api.uploadDocument(file);
      await fetchDocuments();
      await fetchHealth();
    } catch (err) {
      setUploadError(err.message || 'Failed to upload document.');
    } finally {
      setUploading(false);
    }
  };

  // Handle document re-processing (e.g. OCR)
  const handleReprocessDoc = async (docId) => {
    setReprocessingDocId(docId);
    try {
      await api.reprocessDocument(docId);
      await fetchDocuments();
      await fetchHealth();
    } catch (err) {
      alert(`Reprocess failed: ${err.message}`);
    } finally {
      setTimeout(() => setReprocessingDocId(null), 3000);
    }
  };

  // Handle FAISS Index Rebuild
  const handleRebuildIndex = async () => {
    setRebuildingIndex(true);
    setRebuildMessage(null);
    try {
      const res = await api.rebuildIndex();
      setRebuildMessage(res.message || `FAISS index synchronized (${res.vectors} vectors across ${res.documents} documents).`);
      await fetchHealth();
      await fetchDocuments();
      setTimeout(() => setRebuildMessage(null), 6000);
    } catch (err) {
      alert(`Index rebuild failed: ${err.message}`);
    } finally {
      setRebuildingIndex(false);
    }
  };

  // Handle document deletion
  const handleDeleteDoc = async (docId) => {
    if (!window.confirm('Are you sure you want to delete this document and remove its vectors from FAISS?')) return;
    try {
      await api.deleteDocument(docId);
      setSelectedDocIds(prev => prev.filter(id => id !== docId));
      if (currentSummary?.document_id === docId) setCurrentSummary(null);
      await fetchDocuments();
      await fetchHealth();
    } catch (err) {
      alert(`Delete failed: ${err.message}`);
    }
  };

  // Handle document filter toggle
  const handleToggleDocSelect = (docId) => {
    setSelectedDocIds(prev =>
      prev.includes(docId) ? prev.filter(id => id !== docId) : [...prev, docId]
    );
  };

  // Handle Chat Message
  const handleSendMessage = async (questionText) => {
    const userMsg = { role: 'user', content: questionText };
    setMessages(prev => [...prev, userMsg]);
    setAsking(true);

    try {
      const res = await api.sendChatMessage({
        question: questionText,
        documentIds: selectedDocIds,
        conversationId: conversationId
      });

      if (res.conversation_id) setConversationId(res.conversation_id);

      const assistantMsg = {
        role: 'assistant',
        content: res.answer,
        sources: res.sources
      };
      setMessages(prev => [...prev, assistantMsg]);
    } catch (err) {
      const errorMsg = {
        role: 'assistant',
        content: `❌ Error: ${err.message}`
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setAsking(false);
    }
  };

  // Handle Generate Summary
  const handleGenerateSummary = async (docId, summaryType) => {
    setLoadingSummary(true);
    try {
      const summary = await api.generateSummary(docId, summaryType);
      setCurrentSummary(summary);
    } catch (err) {
      alert(`Failed to generate summary: ${err.message}`);
    } finally {
      setLoadingSummary(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', width: '100vw' }}>
      
      {/* Top Navbar with Diagnostics */}
      <Navbar
        health={health}
        onRebuildIndex={handleRebuildIndex}
        rebuildingIndex={rebuildingIndex}
      />

      {/* Main Workspace Layout */}
      <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
        
        {/* Left Sidebar */}
        <Sidebar
          documents={documents}
          selectedDocIds={selectedDocIds}
          onToggleDocSelect={handleToggleDocSelect}
          onUploadFile={handleUploadFile}
          onDeleteDoc={handleDeleteDoc}
          onReprocessDoc={handleReprocessDoc}
          uploading={uploading}
          uploadError={uploadError}
          reprocessingDocId={reprocessingDocId}
        />

        {/* Right Main Content Area */}
        <main style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '20px', gap: '16px', overflow: 'hidden' }}>
          
          {/* Main Navigation Tabs */}
          <div style={{ display: 'flex', gap: '8px', borderBottom: '1px solid var(--border-color)', paddingBottom: '10px' }}>
            
            <button
              onClick={() => setActiveTab('chat')}
              className="btn-secondary"
              style={{
                background: activeTab === 'chat' ? 'var(--primary-light)' : 'transparent',
                borderColor: activeTab === 'chat' ? 'var(--primary)' : 'transparent',
                color: activeTab === 'chat' ? '#fff' : 'var(--text-muted)',
                fontWeight: 600
              }}
            >
              <MessageSquare size={16} color={activeTab === 'chat' ? 'var(--primary)' : 'currentColor'} /> Chat & Q&A
            </button>

            <button
              onClick={() => setActiveTab('summary')}
              className="btn-secondary"
              style={{
                background: activeTab === 'summary' ? 'var(--primary-light)' : 'transparent',
                borderColor: activeTab === 'summary' ? 'var(--primary)' : 'transparent',
                color: activeTab === 'summary' ? '#fff' : 'var(--text-muted)',
                fontWeight: 600
              }}
            >
              <FileText size={16} color={activeTab === 'summary' ? 'var(--accent-cyan)' : 'currentColor'} /> Summarization
            </button>

            <button
              onClick={() => setActiveTab('documents')}
              className="btn-secondary"
              style={{
                background: activeTab === 'documents' ? 'var(--primary-light)' : 'transparent',
                borderColor: activeTab === 'documents' ? 'var(--primary)' : 'transparent',
                color: activeTab === 'documents' ? '#fff' : 'var(--text-muted)',
                fontWeight: 600
              }}
            >
              <Layers size={16} color={activeTab === 'documents' ? 'var(--accent-emerald)' : 'currentColor'} /> Document Registry
            </button>

          </div>

          {/* Active Tab View */}
          <div style={{ flex: 1, overflow: 'hidden' }}>
            {activeTab === 'chat' && (
              <ChatTab
                messages={messages}
                onSendMessage={handleSendMessage}
                asking={asking}
                selectedDocIds={selectedDocIds}
                documents={documents}
                health={health}
                onRebuildIndex={handleRebuildIndex}
                rebuildingIndex={rebuildingIndex}
              />
            )}

            {activeTab === 'summary' && (
              <SummaryTab
                documents={documents}
                onGenerateSummary={handleGenerateSummary}
                onReprocessDoc={handleReprocessDoc}
                loadingSummary={loadingSummary}
                reprocessingDocId={reprocessingDocId}
                currentSummary={currentSummary}
              />
            )}

            {activeTab === 'documents' && (
              <DocumentsTab
                documents={documents}
                health={health}
                onDeleteDoc={handleDeleteDoc}
                onReprocessDoc={handleReprocessDoc}
                onRebuildIndex={handleRebuildIndex}
                reprocessingDocId={reprocessingDocId}
                rebuildingIndex={rebuildingIndex}
                rebuildMessage={rebuildMessage}
              />
            )}
          </div>

        </main>

      </div>

    </div>
  );
}
