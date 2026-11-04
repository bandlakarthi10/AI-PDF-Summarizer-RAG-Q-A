const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

async function handleResponse(response) {
  if (!response.ok) {
    let errorDetail = `HTTP ${response.status}: ${response.statusText}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch (e) {
      // Ignore json parse error
    }
    throw new Error(errorDetail);
  }
  return response.json();
}

export const api = {
  // Health status and system diagnostics
  async getHealth() {
    const res = await fetch(`${API_BASE_URL}/health`);
    return handleResponse(res);
  },

  // Upload PDF document
  async uploadDocument(file) {
    const formData = new FormData();
    formData.append('file', file);

    const res = await fetch(`${API_BASE_URL}/documents/upload`, {
      method: 'POST',
      body: formData,
    });
    return handleResponse(res);
  },

  // Re-process document (e.g. OCR)
  async reprocessDocument(documentId) {
    const res = await fetch(`${API_BASE_URL}/documents/${documentId}/reprocess`, {
      method: 'POST',
    });
    return handleResponse(res);
  },

  // List all uploaded documents
  async listDocuments() {
    const res = await fetch(`${API_BASE_URL}/documents`);
    return handleResponse(res);
  },

  // Get single document status
  async getDocument(documentId) {
    const res = await fetch(`${API_BASE_URL}/documents/${documentId}`);
    return handleResponse(res);
  },

  // Delete document and remove vectors
  async deleteDocument(documentId) {
    const res = await fetch(`${API_BASE_URL}/documents/${documentId}`, {
      method: 'DELETE',
    });
    return handleResponse(res);
  },

  // Rebuild FAISS index from SQLite database
  async rebuildIndex() {
    const res = await fetch(`${API_BASE_URL}/index/rebuild`, {
      method: 'POST',
    });
    return handleResponse(res);
  },

  // Chat Q&A
  async sendChatMessage({ question, documentIds = null, conversationId = null, topK = null }) {
    const payload = {
      question,
      document_ids: documentIds && documentIds.length > 0 ? documentIds : null,
      conversation_id: conversationId || null,
      top_k: topK || null
    };

    const res = await fetch(`${API_BASE_URL}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    return handleResponse(res);
  },

  // Summarize document
  async generateSummary(documentId, summaryType = 'medium') {
    const res = await fetch(`${API_BASE_URL}/summary/${documentId}?summary_type=${summaryType}`, {
      method: 'POST',
    });
    return handleResponse(res);
  }
};
