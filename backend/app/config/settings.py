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

    # LLM Provider — "groq" (cloud, always-on) or "ollama" (local)
    LLM_PROVIDER: str = "groq"

    # Groq Settings (used when LLM_PROVIDER=groq)
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-70b-versatile"

    # Ollama Settings (used when LLM_PROVIDER=ollama, for local development)
    OLLAMA_HOST: str = "http://localhost:11434"
    OLLAMA_LLM_MODEL: str = "llama3"
    OLLAMA_EMBED_MODEL: str = "nomic-embed-text"

    # Embedding Settings (ollama | local)
    # "local" uses sentence-transformers (all-MiniLM-L6-v2) — required in production (Railway has no Ollama)
    EMBEDDING_PROVIDER: str = "local"
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
    MIN_RAG_RELEVANCE: float = 0.3  # Minimum hybrid score to include a chunk in context (0.0–1.0)
    HYBRID_ALPHA: float = 0.5 # Balance weight between lexical (BM25) and vector cosine search

    # Dasha Lambda (separate, bearer-token-authenticated API providing
    # real calculated Mahadasha/Antardasha/Pratyantardasha with actual dates)
    DASHA_LAMBDA_URL: str = "https://bivrov2febq5ued37psv2hcxyi0wlxet.lambda-url.ap-south-1.on.aws/"
    DASHA_LAMBDA_BEARER_TOKEN: str = "f83c6105-1731-4cd9-9d94-9543ff01bfe1"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Instantiate settings
settings = Settings()

# Ensure directories exist
os.makedirs(settings.KNOWLEDGE_BASE_DIR, exist_ok=True)
os.makedirs(settings.VECTOR_DB_DIR, exist_ok=True)
