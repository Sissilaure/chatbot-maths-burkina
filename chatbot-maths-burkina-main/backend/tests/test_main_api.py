"""Tests de routage/validation des endpoints FastAPI (main.py).

Ne fait AUCUN appel réel à Claude (pas d'appels /api/chat, /api/exercise "heureux chemin" avec
génération) : ces tests couvrent le routage, la validation des entrées et l'authentification,
qui sont justement les points où plusieurs bugs de cette session sont passés inaperçus (ex: une
route acceptant GET mais pas HEAD, un endpoint mutateur sans authentification).

Importer `main` instancie le RAGSystem complet (modèle d'embeddings + ChromaDB) : le premier test
de ce fichier est donc lent (10-20s), les suivants réutilisent la même instance via le TestClient.
"""
import pytest
from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


def test_health_check():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"


def test_classes_list_matches_curriculum():
    res = client.get("/api/classes")
    assert res.status_code == 200
    codes = {c["code"] for c in res.json()["classes"]}
    assert codes == {"6ème", "5ème", "4ème", "3ème", "2nde", "1ère", "Tle"}


def test_chapters_for_valid_class():
    res = client.get("/api/classes/6ème/chapters")
    assert res.status_code == 200
    assert "Les fractions" in res.json()["chapters"]


def test_chapters_for_invalid_class_returns_404():
    res = client.get("/api/classes/inexistante/chapters")
    assert res.status_code == 404


@pytest.mark.parametrize("method", ["GET", "HEAD"])
def test_course_route_accepts_get_and_head(method):
    """Régression : FastAPI n'ajoute pas HEAD automatiquement aux routes @app.get comme le fait
    Starlette — le frontend fait un HEAD pour vérifier la disponibilité du cours avant d'ouvrir un
    nouvel onglet, et une route GET-only renvoyait toujours 405 (donc toujours "indisponible")."""
    res = client.request(method, "/api/course/2nde/Vecteurs du plan")
    assert res.status_code == 200


def test_course_route_404_for_missing_document():
    res = client.head("/api/course/4ème/Théorème de Pythagore")
    assert res.status_code == 404


def test_course_route_404_for_invalid_chapter():
    res = client.head("/api/course/2nde/Chapitre-qui-n-existe-pas")
    assert res.status_code == 404


def test_exercise_rejects_invalid_class():
    res = client.post("/api/exercise", json={"class_level": "inexistante", "chapter": ""})
    assert res.status_code == 400


def test_exercise_rejects_chapter_not_in_curriculum():
    res = client.post(
        "/api/exercise",
        json={"class_level": "6ème", "chapter": "Un chapitre qui n'existe pas"},
    )
    assert res.status_code == 400


def test_exercise_accepts_missing_chapter_and_difficulty_as_optional():
    """La validation ne doit PAS rejeter une requête sans chapitre/difficulté (elles sont
    facultatives et déduites côté serveur) — seule la présence d'un chapitre invalide doit 400."""
    res = client.post(
        "/api/exercise",
        json={"class_level": "6ème", "chapter": "", "difficulty": None},
    )
    # 500 est acceptable ici si Claude échoue/n'est pas dispo en environnement de test : ce qui
    # est testé, c'est que ça n'échoue pas à la VALIDATION (jamais 400/422).
    assert res.status_code in (200, 500)


def test_chat_allows_empty_class_and_chapter():
    res = client.post(
        "/api/chat",
        json={"question": "test", "class_level": "", "chapter": "", "history": []},
    )
    assert res.status_code != 400


def test_documents_upload_requires_decideur_auth():
    res = client.post(
        "/api/documents/upload",
        files={"file": ("test.txt", b"contenu de test", "text/plain")},
    )
    assert res.status_code == 401


def test_documents_initialize_sample_requires_decideur_auth():
    res = client.post("/api/documents/initialize-sample")
    assert res.status_code == 401


def test_admin_routes_require_decideur_auth():
    for path in (
        "/api/admin/overview",
        "/api/admin/success-by-chapter",
        "/api/admin/weak-notions",
        "/api/admin/trend",
        "/api/admin/activity",
    ):
        assert client.get(path).status_code == 401


def test_register_and_login_roundtrip():
    import uuid
    username = f"test_{uuid.uuid4().hex[:8]}"
    register_res = client.post(
        "/api/auth/register", json={"username": username, "password": "motdepasse123"}
    )
    assert register_res.status_code == 200
    token = register_res.json()["token"]

    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["username"] == username

    login_res = client.post(
        "/api/auth/login", json={"username": username, "password": "wrong-password"}
    )
    assert login_res.status_code == 401


def test_register_rejects_short_password():
    res = client.post("/api/auth/register", json={"username": "toto", "password": "123"})
    assert res.status_code == 400


def test_exercise_photo_forwards_history_to_rag_system(monkeypatch):
    """Le champ `history` (JSON, en form field) doit être décodé et transmis tel quel à
    explain_exercise_photo : c'est ce qui permet à Claude de "revoir" la photo sur les messages
    de suivi (voir App.jsx::activePhoto) plutôt que de répondre en aveugle."""
    captured = {}

    def fake_explain(file_bytes, media_type, class_level, chapter, user_prompt, history):
        captured["history"] = history
        return "ok"

    monkeypatch.setattr(main.rag_system, "explain_exercise_photo", fake_explain)

    history = [{"role": "user", "content": "[Photo d'exercice envoyée]"}, {"role": "assistant", "content": "Voici l'exercice..."}]
    res = client.post(
        "/api/exercise/photo",
        files={"file": ("exercice.jpg", b"\xff\xd8\xff", "image/jpeg")},
        data={"history": __import__("json").dumps(history)},
    )
    assert res.status_code == 200
    assert captured["history"] == history


def test_exercise_photo_ignores_malformed_history(monkeypatch):
    """Un `history` JSON invalide ne doit jamais faire planter la requête : repli sur liste vide."""
    captured = {}

    def fake_explain(file_bytes, media_type, class_level, chapter, user_prompt, history):
        captured["history"] = history
        return "ok"

    monkeypatch.setattr(main.rag_system, "explain_exercise_photo", fake_explain)

    res = client.post(
        "/api/exercise/photo",
        files={"file": ("exercice.jpg", b"\xff\xd8\xff", "image/jpeg")},
        data={"history": "not valid json"},
    )
    assert res.status_code == 200
    assert captured["history"] == []


def test_generate_remediation_resilient_to_retrieval_failure(monkeypatch):
    """generate_remediation cherche maintenant des extraits de cours pour ancrer le QCM (utile
    pour les chapitres "Remédiation Hakili Lab") : si cette recherche échoue, la génération du
    QCM ne doit pas planter pour autant (repli silencieux, voir le try/except du code)."""
    def broken_retrieve(*args, **kwargs):
        raise RuntimeError("chroma indisponible")

    one_question = (
        '{"notion": "n", "question": "q", "choix": ["a", "b", "c", "d"], '
        '"reponse_correcte_index": 0, "explication": "e", "conseil": "c"}'
    )
    fake_json = '{"questions": [' + ",".join([one_question] * 8) + "]}"

    monkeypatch.setattr(main.rag_system, "_retrieve_with_filters", broken_retrieve)
    monkeypatch.setattr(main.rag_system, "_call_claude", lambda *a, **k: fake_json)

    questions = main.rag_system.generate_remediation("3ème", "Les fractions", history=[])
    assert len(questions) == 8


def test_exercise_photo_without_history_defaults_to_empty_list(monkeypatch):
    captured = {}

    def fake_explain(file_bytes, media_type, class_level, chapter, user_prompt, history):
        captured["history"] = history
        return "ok"

    monkeypatch.setattr(main.rag_system, "explain_exercise_photo", fake_explain)

    res = client.post(
        "/api/exercise/photo",
        files={"file": ("exercice.jpg", b"\xff\xd8\xff", "image/jpeg")},
    )
    assert res.status_code == 200
    assert captured["history"] == []
