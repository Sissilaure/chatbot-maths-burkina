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
    ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")
    ANTHROPIC_TEMPERATURE = float(os.getenv("ANTHROPIC_TEMPERATURE", "0.4"))
    # Ce modèle raisonne avant de répondre (blocs "thinking" qui consomment le même budget de
    # tokens que la réponse) et la part de raisonnement varie fortement d'un appel à l'autre :
    # sur un budget serré, il arrive qu'elle consomme la totalité des tokens sans laisser de
    # place à la moindre réponse texte. Une marge confortable réduit la fréquence de ce cas
    # (voir aussi le repli automatique dans _call_claude/_stream_claude, qui relance la requête
    # depuis zéro si jamais ça se produit malgré tout).
    MAX_TOKENS_CHAT = int(os.getenv("MAX_TOKENS_CHAT", "6144"))
    # Les exercices 4★ (figure géométrique incluse) sortent facilement 3000+ tokens de JSON :
    # une marge confortable évite de dépendre de la relance automatique (fragile en mode JSON,
    # le modèle ne reprenant pas toujours la chaîne exactement où elle a été coupée).
    MAX_TOKENS_EXERCISE = int(os.getenv("MAX_TOKENS_EXERCISE", "6144"))
    MAX_TOKENS_SIMPLIFY = int(os.getenv("MAX_TOKENS_SIMPLIFY", "1500"))
    MAX_TOKENS_BASICS = int(os.getenv("MAX_TOKENS_BASICS", "2000"))
    MAX_TOKENS_REMEDIATION = int(os.getenv("MAX_TOKENS_REMEDIATION", "6144"))
    MAX_TOKENS_SUMMARY = int(os.getenv("MAX_TOKENS_SUMMARY", "1200"))
    MAX_TOKENS_EXERCISE_PHOTO = int(os.getenv("MAX_TOKENS_EXERCISE_PHOTO", "3000"))
    # Photo d'exercice envoyée par l'élève : au-delà, on refuse plutôt que de laisser l'upload
    # traîner (mobile en 3G) ou de gonfler inutilement le payload envoyé à l'API Claude.
    MAX_EXERCISE_PHOTO_SIZE_BYTES = int(os.getenv("MAX_EXERCISE_PHOTO_SIZE_BYTES", str(8 * 1024 * 1024)))
    # Nombre maximal de "continuations" automatiques si Claude tronque une réponse
    # (relance transparente pour ne jamais couper une explication en plein milieu).
    MAX_AUTO_CONTINUATIONS = int(os.getenv("MAX_AUTO_CONTINUATIONS", "3"))

    # Conversation memory (multi-turn)
    HISTORY_MAX_TURNS = int(os.getenv("HISTORY_MAX_TURNS", "6"))

    # ChromaDB Configuration
    CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")

    # Comptes élèves (auth JWT + SQLite)
    DB_PATH = os.getenv("DB_PATH", "./data/app.db")
    JWT_SECRET = os.getenv("JWT_SECRET", "")
    # Volontairement court : réduit la fenêtre d'exploitation d'un token volé (pas de révocation
    # côté serveur pour l'instant, voir auth.py).
    JWT_EXPIRE_DAYS = int(os.getenv("JWT_EXPIRE_DAYS", "7"))

    # Application Configuration
    # "production" active des vérifications strictes au démarrage (voir auth.py : refuse de
    # démarrer sans JWT_SECRET explicite plutôt que d'en générer un silencieusement).
    APP_ENV = os.getenv("APP_ENV", "development")
    APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT = int(os.getenv("APP_PORT", "8000"))
    CORS_ORIGINS = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")

    # RAG Parameters
    CHUNK_SIZE = 700
    CHUNK_OVERLAP = 150
    TOP_K = 4

    # Data Directory
    DATA_DIR = os.getenv("DATA_DIR", "./data/documents")

config = Config()