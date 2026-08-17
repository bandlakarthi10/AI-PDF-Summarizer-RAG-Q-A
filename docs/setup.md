# Setup & Troubleshooting Guide

## Prerequisites

- **Python**: Version 3.11 or higher
- **Node.js**: Version 18.0 or higher
- **Ollama**: Download and install from [ollama.com](https://ollama.com)

---

## Installation Walkthrough

### 1. Repository Setup
```bash
git clone <repo-url>
cd "AI PDF Summarizer"
```

### 2. Environment Configuration
Create `.env` in the root folder:
```bash
cp .env.example .env
```

### 3. Backend Installation
```bash
pip install -r backend/requirements.txt
```

Verify test suite:
```bash
python -m pytest backend/tests/ -v
```

### 4. Running Ollama Local LLM
Start Ollama service:
```bash
ollama serve
```

Pull target model in a separate shell:
```bash
ollama pull llama3.2
```

### 5. Running the Backend Server
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir backend
```

### 6. Running the Frontend App
```bash
cd frontend
npm install
npm run dev
```
Open browser at `http://localhost:5173`.

---

## Troubleshooting

### Ollama is reported as "unavailable"
- Verify that `ollama serve` is running on `http://localhost:11434`.
- Test endpoint directly: `curl http://localhost:11434/api/tags`.

### Model Missing Error
- Ensure you have pulled the model configured in `.env` (`OLLAMA_MODEL=llama3.2`).
- Pull command: `ollama pull llama3.2`.

### FAISS Index Reset
- To reset vector store, delete files under `backend/data/vectorstore/`.
