import os
from pydantic_settings import BaseSettings
from pathlib import Path

# Resolve base directories
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
BASE_DIR = BACKEND_DIR.parent

class Settings(BaseSettings):
    # App General Settings
    APP_NAME: str = "Call-Astro"
    DEBUG: bool = False
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # Ollama Settings
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_LLM_MODEL: str = "llama3"         # Default to Llama3 or user config
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text" # Default embedding model in Ollama

    # Embedding Settings (ollama | local)
    # If "local", it will fall back to using sentence-transformers on CPU
    EMBEDDING_PROVIDER: str = "ollama"
    LOCAL_EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"

    # Database
    DATABASE_PATH: str = str(BACKEND_DIR / "astro_chat.db")

    # Knowledge Base & Vector Data Directories
    KNOWLEDGE_BASE_DIR: str = str(BACKEND_DIR / "knowledge_base")
    VECTOR_DB_DIR: str = str(BACKEND_DIR / "vector_db_data")

    # RAG Settings
    CHUNK_SIZE: int = 800
    CHUNK_OVERLAP: int = 150
    TOP_K_RETRIEVAL: int = 4
    HYBRID_ALPHA: float = 0.5 # Balance weight between lexical (BM25) and vector cosine search

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Instantiate settings
settings = Settings()

# Ensure directories exist
os.makedirs(settings.KNOWLEDGE_BASE_DIR, exist_ok=True)
os.makedirs(settings.VECTOR_DB_DIR, exist_ok=True)
