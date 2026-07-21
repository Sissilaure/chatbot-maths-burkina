"""Rend le dossier backend/ importable (main.py, rag_system.py, ... utilisent des imports plats
comme `from config import config`, qui supposent que backend/ est sur sys.path)."""
import os
import sys
import tempfile
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# Les tests créent de vrais comptes (test_register_and_login_roundtrip) : DB_PATH doit pointer
# vers une base jetable, jamais data/app.db, pour ne pas polluer les statistiques réelles vues
# par le tableau de bord décideur. Doit être fait AVANT tout import de `config`/`main`.
os.environ["DB_PATH"] = os.path.join(tempfile.mkdtemp(prefix="chatmaths-test-db-"), "test.db")
