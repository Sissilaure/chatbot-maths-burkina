import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Hugging Face Configuration (Free API)
    HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")
    HUGGINGFACE_MODEL = os.getenv("HUGGINGFACE_MODEL", "mistralai/Mistral-7B-Instruct-v0.2")
    
    # ChromaDB Configuration
    CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "../data/chroma_db")
    
    # Application Configuration
    APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT = int(os.getenv("APP_PORT", "8000"))
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(",")
    
    # RAG Parameters
    CHUNK_SIZE = 700
    CHUNK_OVERLAP = 150
    TOP_K = 4
    
    # Data Directory
    DATA_DIR = "../data/documents"

config = Config()
