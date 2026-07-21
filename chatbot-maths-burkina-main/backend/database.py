"""Base SQLite pour les comptes élèves : utilisateurs, conversations/messages,
et signaux de lacunes (résultats de remédiation, notions simplifiées) utilisés
pour l'accueil personnalisé. Pas d'ORM : le reste du projet n'en utilise nulle
part ailleurs, et l'échelle (quelques élèves) ne le justifie pas.
"""
import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from config import config


@contextmanager
def get_connection():
    Path(config.DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'eleve',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                title TEXT NOT NULL DEFAULT 'Discussion libre',
                class_level TEXT NOT NULL DEFAULT '',
                chapter TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                type TEXT NOT NULL,
                text TEXT,
                kind TEXT,
                sources_json TEXT,
                data_json TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS remediation_answers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                class_level TEXT NOT NULL,
                chapter TEXT NOT NULL,
                notion TEXT NOT NULL,
                is_correct INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS struggles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                class_level TEXT NOT NULL,
                chapter TEXT NOT NULL,
                question TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
            CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
            CREATE INDEX IF NOT EXISTS idx_remediation_user ON remediation_answers(user_id);
            CREATE INDEX IF NOT EXISTS idx_struggles_user ON struggles(user_id);
        """)

        # Migration défensive : une base créée avant l'ajout du rôle décideur n'a pas
        # cette colonne — CREATE TABLE IF NOT EXISTS ne la rajoute pas rétroactivement.
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
        if "role" not in columns:
            conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'eleve'")


# ---------------------------------------------------------------------------
# Utilisateurs
# ---------------------------------------------------------------------------

def create_user(username: str, password_hash: str, role: str = "eleve") -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
            (username, password_hash, role),
        )
        return cur.lastrowid


def get_user_by_username(username: str):
    with get_connection() as conn:
        return conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()


def get_user_by_id(user_id: int):
    with get_connection() as conn:
        return conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


# ---------------------------------------------------------------------------
# Conversations / messages
# ---------------------------------------------------------------------------

def create_conversation(user_id: int, class_level: str = "", chapter: str = "") -> int:
    title = f"{class_level} · {chapter}" if class_level and chapter else (class_level or "Discussion libre")
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO conversations (user_id, title, class_level, chapter) VALUES (?, ?, ?, ?)",
            (user_id, title, class_level, chapter),
        )
        return cur.lastrowid


def list_conversations(user_id: int):
    with get_connection() as conn:
        return conn.execute(
            "SELECT id, title, class_level, chapter, created_at, updated_at FROM conversations "
            "WHERE user_id = ? ORDER BY updated_at DESC",
            (user_id,),
        ).fetchall()


def get_conversation(conversation_id: int, user_id: int):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM conversations WHERE id = ? AND user_id = ?", (conversation_id, user_id)
        ).fetchone()


def get_messages(conversation_id: int):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id ASC", (conversation_id,)
        ).fetchall()
    messages = []
    for row in rows:
        messages.append({
            "type": row["type"],
            "text": row["text"],
            "kind": row["kind"],
            "sources": json.loads(row["sources_json"]) if row["sources_json"] else [],
            "data": json.loads(row["data_json"]) if row["data_json"] else None,
        })
    return messages


def delete_conversation(conversation_id: int, user_id: int) -> bool:
    with get_connection() as conn:
        cur = conn.execute(
            "DELETE FROM conversations WHERE id = ? AND user_id = ?", (conversation_id, user_id)
        )
        return cur.rowcount > 0


TITLE_MAX_LENGTH = 60


def add_message(conversation_id: int, type_: str, text: str = None, kind: str = None,
                 sources: list = None, data: dict = None):
    """Ajoute un message et, s'il s'agit du tout premier message de l'élève dans cette
    conversation, renomme son titre avec le début de sa question (plus utile dans l'historique
    qu'un générique "classe · chapitre", qui se répète pour toutes les conversations sur le même
    chapitre et ne dit rien du contenu réel de l'échange). Retourne le nouveau titre si renommé,
    sinon None."""
    new_title = None
    with get_connection() as conn:
        if type_ == "user" and text and text.strip():
            already_has_question = conn.execute(
                "SELECT 1 FROM messages WHERE conversation_id = ? AND type = 'user' LIMIT 1",
                (conversation_id,),
            ).fetchone()
            if not already_has_question:
                stripped = text.strip()
                new_title = (stripped[:TITLE_MAX_LENGTH] + "…") if len(stripped) > TITLE_MAX_LENGTH else stripped
                conn.execute("UPDATE conversations SET title = ? WHERE id = ?", (new_title, conversation_id))

        conn.execute(
            "INSERT INTO messages (conversation_id, type, text, kind, sources_json, data_json) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                conversation_id, type_, text, kind,
                json.dumps(sources, ensure_ascii=False) if sources else None,
                json.dumps(data, ensure_ascii=False) if data else None,
            ),
        )
        conn.execute(
            "UPDATE conversations SET updated_at = datetime('now') WHERE id = ?", (conversation_id,)
        )
    return new_title


# ---------------------------------------------------------------------------
# Signaux de lacunes (remédiation, struggles) — alimentent l'accueil personnalisé
# ---------------------------------------------------------------------------

def add_remediation_answers(user_id: int, class_level: str, chapter: str, answers: list):
    with get_connection() as conn:
        conn.executemany(
            "INSERT INTO remediation_answers (user_id, class_level, chapter, notion, is_correct) "
            "VALUES (?, ?, ?, ?, ?)",
            [(user_id, class_level, chapter, a["notion"], int(bool(a["is_correct"]))) for a in answers],
        )


def add_struggle(user_id: int, class_level: str, chapter: str, question: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO struggles (user_id, class_level, chapter, question) VALUES (?, ?, ?, ?)",
            (user_id, class_level, chapter, question),
        )


def get_weak_notions(user_id: int, limit: int = 5):
    """Notions les plus souvent ratées en remédiation (signal de lacune le plus fiable)."""
    with get_connection() as conn:
        return conn.execute(
            "SELECT notion, class_level, chapter, COUNT(*) as wrong_count "
            "FROM remediation_answers WHERE user_id = ? AND is_correct = 0 "
            "GROUP BY notion, class_level, chapter ORDER BY wrong_count DESC, MAX(created_at) DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()


def get_recent_struggles(user_id: int, limit: int = 5):
    with get_connection() as conn:
        return conn.execute(
            "SELECT class_level, chapter, question, created_at FROM struggles "
            "WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()


def get_recent_topics(user_id: int, limit: int = 5):
    with get_connection() as conn:
        return conn.execute(
            "SELECT class_level, chapter, MAX(updated_at) as last_visited, COUNT(*) as visits "
            "FROM conversations WHERE user_id = ? AND chapter != '' "
            "GROUP BY class_level, chapter ORDER BY last_visited DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()


def has_any_history(user_id: int) -> bool:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT "
            "(SELECT COUNT(*) FROM conversations WHERE user_id = ?) + "
            "(SELECT COUNT(*) FROM remediation_answers WHERE user_id = ?) + "
            "(SELECT COUNT(*) FROM struggles WHERE user_id = ?) AS total",
            (user_id, user_id, user_id),
        ).fetchone()
        return row["total"] > 0


# ---------------------------------------------------------------------------
# Tableau de bord décideurs — statistiques agrégées uniquement (jamais de
# résultat rattaché à un élève nommé : toujours groupées par classe/chapitre/
# notion/mois, jamais par user_id).
# ---------------------------------------------------------------------------

def get_admin_overview():
    with get_connection() as conn:
        row = conn.execute("""
            SELECT
                (SELECT COUNT(DISTINCT user_id) FROM (
                    SELECT user_id, created_at FROM conversations
                    UNION ALL
                    SELECT user_id, created_at FROM remediation_answers
                ) WHERE created_at >= datetime('now', '-30 days')) AS active_students,
                (SELECT COUNT(*) FROM (
                    SELECT DISTINCT user_id, class_level, chapter, substr(created_at, 1, 16)
                    FROM remediation_answers
                )) AS remediations_completed,
                (SELECT COUNT(*) FROM remediation_answers) AS total_answers,
                (SELECT COALESCE(AVG(is_correct) * 100.0, 0) FROM remediation_answers) AS success_rate
        """).fetchone()
        return dict(row)


def get_success_by_chapter(class_level: str = None):
    query = (
        "SELECT class_level, chapter, COUNT(*) AS attempts, AVG(is_correct) * 100.0 AS success_rate "
        "FROM remediation_answers"
    )
    params = []
    if class_level:
        query += " WHERE class_level = ?"
        params.append(class_level)
    query += " GROUP BY class_level, chapter ORDER BY class_level, chapter"
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(query, params)]


def get_weak_notions_global(class_level: str = None, limit: int = 10):
    query = (
        "SELECT notion, class_level, chapter, "
        "SUM(CASE WHEN is_correct = 0 THEN 1 ELSE 0 END) AS wrong_count, COUNT(*) AS attempts "
        "FROM remediation_answers"
    )
    params = []
    if class_level:
        query += " WHERE class_level = ?"
        params.append(class_level)
    query += " GROUP BY notion, class_level, chapter HAVING wrong_count > 0 ORDER BY wrong_count DESC LIMIT ?"
    params.append(limit)
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(query, params)]


def get_success_trend(class_level: str = None):
    """Taux de réussite en remédiation groupé par mois : la vue « évolution du niveau »."""
    query = (
        "SELECT strftime('%Y-%m', created_at) AS month, COUNT(*) AS attempts, "
        "AVG(is_correct) * 100.0 AS success_rate FROM remediation_answers"
    )
    params = []
    if class_level:
        query += " WHERE class_level = ?"
        params.append(class_level)
    query += " GROUP BY month ORDER BY month"
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(query, params)]


def get_activity_trend(class_level: str = None):
    """Nombre de conversations démarrées par mois : proxy d'engagement dans le temps."""
    query = "SELECT strftime('%Y-%m', created_at) AS month, COUNT(*) AS conversations FROM conversations"
    params = []
    if class_level:
        query += " WHERE class_level = ?"
        params.append(class_level)
    query += " GROUP BY month ORDER BY month"
    with get_connection() as conn:
        return [dict(r) for r in conn.execute(query, params)]
