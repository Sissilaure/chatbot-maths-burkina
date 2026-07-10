import os
from pathlib import Path
from dotenv import load_dotenv

# Charger le .env en utilisant le chemin absolu
env_path = Path(__file__).resolve().parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()  # fallback

class Config:
    # Anthropic Claude Configuration
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
    
    # ChromaDB Configuration
    CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")
    
    # Application Configuration
    APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT = int(os.getenv("APP_PORT", "8000"))
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
    
    # RAG Parameters
    CHUNK_SIZE = 700
    CHUNK_OVERLAP = 150
    TOP_K = 4
    
    # Data Directory
    DATA_DIR = os.getenv("DATA_DIR", "./data/documents")

config = Config()