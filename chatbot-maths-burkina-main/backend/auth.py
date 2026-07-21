"""Authentification des comptes élèves : hash de mot de passe (bcrypt) et
tokens de connexion (JWT bearer, pas de session serveur)."""
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from config import config
import database

JWT_ALGORITHM = "HS256"
JWT_SECRET_FILE = Path(config.DB_PATH).parent / ".jwt_secret"

_security = HTTPBearer(auto_error=False)


def _get_jwt_secret() -> str:
    """Utilise JWT_SECRET si configuré, sinon génère un secret une seule fois et le
    persiste sur disque pour que les sessions survivent aux redémarrages du serveur."""
    if config.JWT_SECRET:
        return config.JWT_SECRET

    JWT_SECRET_FILE.parent.mkdir(parents=True, exist_ok=True)
    if JWT_SECRET_FILE.exists():
        return JWT_SECRET_FILE.read_text(encoding="utf-8").strip()

    secret = secrets.token_hex(32)
    JWT_SECRET_FILE.write_text(secret, encoding="utf-8")
    return secret


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def create_token(user_id: int, username: str) -> str:
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(days=config.JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, _get_jwt_secret(), algorithm=JWT_ALGORITHM)


def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(_security)):
    """Dépendance FastAPI : 401 si le token est absent, invalide, expiré, ou si
    l'utilisateur correspondant n'existe plus."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentification requise")

    try:
        payload = jwt.decode(credentials.credentials, _get_jwt_secret(), algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Token invalide ou expiré")

    user = database.get_user_by_id(int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    return user


def require_decideur(user=Depends(get_current_user)):
    """Dépendance FastAPI pour les routes /api/admin/* : réservées aux comptes décideur
    (créés hors inscription publique, voir create_decideur.py)."""
    if user["role"] != "decideur":
        raise HTTPException(status_code=403, detail="Accès réservé aux comptes décideur")
    return user
