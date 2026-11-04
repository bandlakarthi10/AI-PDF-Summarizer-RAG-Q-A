import os
from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Resolve project root (three levels up from this file: app/core/config.py -> app -> backend -> project root)
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent   # backend/
ROOT_DIR = BACKEND_DIR.parent                                  # project root

class Settings(BaseSettings):
    APP_NAME: str = "AI PDF Summarizer & RAG Q&A"
    APP_ENV: str = "development"

    # Ollama
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2"
    OLLAMA_TIMEOUT_SECONDS: float = 120.0

    # Embedding
    EMBEDDING_MODEL: str = "BAAI/bge-small-en-v1.5"

    # Chunking
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 100

    # Retrieval
    TOP_K: int = 5

    # Upload limits
    MAX_FILE_SIZE_MB: int = 50

    # CORS & Security
    ALLOWED_ORIGINS: str = "*"

    # Frontend build distribution
    FRONTEND_DIST_DIR: Path = ROOT_DIR / "frontend" / "dist"

    # Data directories (always anchored at ROOT_DIR)
    DATA_DIR: Path = ROOT_DIR / "data"

    # Conversation memory
    MAX_CONVERSATION_TURNS: int = 6

    model_config = SettingsConfigDict(
        env_file=str(ROOT_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("FRONTEND_DIST_DIR", mode="before")
    @classmethod
    def _resolve_frontend_dir(cls, v):
        if not v:
            return ROOT_DIR / "frontend" / "dist"
        p = Path(v)
        if not p.is_absolute():
            return (ROOT_DIR / p).resolve()
        return p.resolve()

    @field_validator("DATA_DIR", mode="before")
    @classmethod
    def _resolve_data_dir(cls, v):
        if not v:
            return ROOT_DIR / "data"
        p = Path(v)
        if not p.is_absolute():
            return (ROOT_DIR / p).resolve()
        return p.resolve()

    @property
    def upload_dir(self) -> Path:
        d = self.DATA_DIR / "uploads"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def vectorstore_dir(self) -> Path:
        d = self.DATA_DIR / "vectorstore"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def db_path(self) -> Path:
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        return self.DATA_DIR / "documents.db"

    def ensure_directories(self):
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.upload_dir      # property creates it
        self.vectorstore_dir # property creates it


settings = Settings()
settings.ensure_directories()
