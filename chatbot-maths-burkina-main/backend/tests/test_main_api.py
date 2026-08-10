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


def _register(unique_username, **overrides):
    """Fiche d'inscription complète par défaut (class_code/gender/birth_year/is_candidat_libre/
    school_name sont obligatoires depuis le correctif de spécification — voir RAPPORT_MIGRATION.md).
    `overrides` permet à un test de ne faire varier qu'un seul champ à la fois."""
    payload = {
        "username": unique_username("api"),
        "password": "motdepasse123",
        "class_code": "3ème",
        "gender": "F",
        "birth_year": 2012,
        "is_candidat_libre": False,
        "school_name": "École Test",
        "region": "Centre",
        "consent_accepted": True,
    }
    payload.update(overrides)
    return client.post("/api/auth/register", json=payload)


def test_register_and_login_roundtrip(unique_username):
    register_res = _register(unique_username)
    assert register_res.status_code == 200
    body = register_res.json()
    token = body["token"]
    username = body["username"]
    assert body["public_code"].startswith("CM-")
    assert body["consent_ok"] is True
    assert body["profile_complete"] is True

    me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["username"] == username
    assert me_res.json()["consent_ok"] is True
    assert me_res.json()["profile_complete"] is True

    login_res = client.post(
        "/api/auth/login", json={"username": username, "password": "wrong-password"}
    )
    assert login_res.status_code == 401


def test_register_rejects_short_password(unique_username):
    res = _register(unique_username, password="123")
    assert res.status_code == 400


def test_register_requires_consent(unique_username):
    res = _register(unique_username, consent_accepted=False)
    assert res.status_code == 400


def test_register_rejects_duplicate_username(unique_username):
    username = unique_username("dup")
    first = _register(unique_username, username=username)
    assert first.status_code == 200
    second = _register(unique_username, username=username)
    assert second.status_code == 409


def test_register_rejects_invalid_class_or_gender(unique_username):
    bad_class = _register(unique_username, class_code="classe-inexistante")
    assert bad_class.status_code == 400
    bad_gender = _register(unique_username, gender="X")
    assert bad_gender.status_code == 400


def test_register_requires_profile_fields(unique_username):
    """class_code/gender/birth_year/is_candidat_libre sont désormais obligatoires : les omettre
    doit 422 (erreur de validation Pydantic, interceptée par le handler français, voir main.py),
    pas 400 (qui suppose que le champ est présent mais que sa VALEUR est invalide)."""
    payload = {
        "username": unique_username("incomplete"),
        "password": "motdepasse123",
        "consent_accepted": True,
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 422
    assert isinstance(res.json()["detail"], str)  # message français unique, pas la liste brute Pydantic


def test_register_requires_school_unless_candidat_libre(unique_username):
    missing_school = _register(unique_username, school_name=None, is_candidat_libre=False)
    assert missing_school.status_code == 422

    blank_school = _register(unique_username, school_name="   ", is_candidat_libre=False)
    assert blank_school.status_code == 422


def test_register_candidat_libre_does_not_require_school(unique_username):
    res = _register(unique_username, school_name=None, is_candidat_libre=True)
    assert res.status_code == 200
    assert res.json()["profile_complete"] is True


def test_business_route_blocked_when_consent_missing(unique_username):
    """Simule un compte migré depuis SQLite (consent_version = NULL) : voir migrate_sqlite_to_pg.py.
    Créé directement via database.create_user (pas la route /api/auth/register, qui garantit
    toujours un consentement à jour pour un nouveau compte)."""
    import auth
    import database

    username = unique_username("noconsent428")
    user = database.create_user(
        username, auth.hash_password("motdepasse123"),
        class_code="3ème", gender="F", birth_year=2012, is_candidat_libre=False,
        school_name="École Test",
        # consent_version omis : reste NULL, comme un compte migré.
    )
    token = auth.create_token(user["id"], user["username"])

    res = client.post(
        "/api/chat", json={"question": "test", "class_level": "", "chapter": "", "history": []},
        headers=_auth_headers(token),
    )
    assert res.status_code == 428
    assert res.json()["detail"]["reason"] == "consent_required"


def test_business_route_blocked_when_profile_incomplete(unique_username):
    """Simule un compte migré ayant déjà donné son consentement (ex: reconnecté une première
    fois et validé POST /api/consent/accept) mais pas encore complété sa fiche."""
    import auth
    import database
    from consent_text import CONSENT_VERSION

    username = unique_username("noprofile428")
    user = database.create_user(
        username, auth.hash_password("motdepasse123"),
        consent_version=CONSENT_VERSION,
        # class_code/gender/birth_year omis : NULL, comme un compte migré pas encore complété.
    )
    token = auth.create_token(user["id"], user["username"])

    res = client.post(
        "/api/exercise", json={"class_level": "3ème", "chapter": "", "history": []},
        headers=_auth_headers(token),
    )
    assert res.status_code == 428
    assert res.json()["detail"]["reason"] == "profile_incomplete"

    # Le mode invité, lui, n'est jamais concerné par ce contrôle.
    guest_res = client.post(
        "/api/exercise", json={"class_level": "3ème", "chapter": "", "history": []},
    )
    assert guest_res.status_code != 428


def test_summary_and_simplify_are_gated_too(unique_username):
    """La porte 428 couvre aussi /api/summary et /api/simplify (elles écrivent en base pour un
    compte connecté, voir _persist_message_best_effort) — pas seulement chat/exercice/remédiation."""
    import auth
    import database

    username = unique_username("noconsentgate")
    user = database.create_user(
        username, auth.hash_password("motdepasse123"),
        class_code="3ème", gender="F", birth_year=2012, is_candidat_libre=False,
        school_name="École Test",
    )
    token = auth.create_token(user["id"], user["username"])

    summary_res = client.post(
        "/api/summary", json={"history": [], "class_level": "", "chapter": ""},
        headers=_auth_headers(token),
    )
    assert summary_res.status_code == 428
    assert summary_res.json()["detail"]["reason"] == "consent_required"

    simplify_res = client.post(
        "/api/simplify", json={"answer": "x", "class_level": "3ème", "question": "y", "chapter": ""},
        headers=_auth_headers(token),
    )
    assert simplify_res.status_code == 428
    assert simplify_res.json()["detail"]["reason"] == "consent_required"


def test_profile_and_consent_routes_are_never_gated(unique_username):
    """/api/profile et /api/consent* doivent rester accessibles à un compte au consentement
    périmé / à la fiche incomplète : ce sont justement les routes qui permettent de se débloquer.
    Si elles étaient gatées, un compte bloqué ne pourrait plus jamais se débloquer lui-même."""
    import auth
    import database

    username = unique_username("selfunblock")
    user = database.create_user(username, auth.hash_password("motdepasse123"))
    # consent_version NULL et class_code/gender/birth_year NULL : un compte migré non résolu,
    # dans l'état le plus bloqué possible.
    token = auth.create_token(user["id"], user["username"])
    headers = _auth_headers(token)

    consent_res = client.post("/api/consent/accept", headers=headers)
    assert consent_res.status_code == 200

    profile_res = client.patch(
        "/api/profile",
        json={"class_code": "3ème", "gender": "F", "birth_year": 2012, "is_candidat_libre": True},
        headers=headers,
    )
    assert profile_res.status_code == 200

    me_res = client.get("/api/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["consent_ok"] is True
    assert me_res.json()["profile_complete"] is True


def test_persistence_failure_is_counted_and_exposed_in_health(unique_username, monkeypatch):
    """La persistance best-effort ne doit jamais faire échouer la réponse à l'élève, mais un
    échec ne doit plus non plus rester complètement muet (voir _persist_exchange_best_effort) :
    il doit être compté et visible dans GET /api/health::persistence_failures."""
    register_res = _register(unique_username)
    token = register_res.json()["token"]
    conv_id = client.post(
        "/api/conversations", json={"class_level": "6ème", "chapter": "Les fractions"},
        headers=_auth_headers(token),
    ).json()["id"]

    monkeypatch.setattr(
        main.rag_system, "generate_response",
        lambda *a, **k: {"answer": "réponse de test", "sources": [], "from_rag": False},
    )

    before = client.get("/api/health").json()["persistence_failures"]

    def broken_add_exchange(*args, **kwargs):
        raise RuntimeError("panne simulée d'écriture Postgres")

    monkeypatch.setattr(main.database, "add_exchange", broken_add_exchange)

    chat_res = client.post(
        "/api/chat",
        json={"question": "test", "class_level": "6ème", "chapter": "Les fractions", "history": [], "conversation_id": conv_id},
        headers=_auth_headers(token),
    )
    # La panne de sauvegarde ne doit jamais se répercuter sur la réponse envoyée à l'élève.
    assert chat_res.status_code == 200
    assert chat_res.json()["answer"] == "réponse de test"

    after = client.get("/api/health").json()["persistence_failures"]
    assert after == before + 1


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def test_students_cannot_access_each_others_conversations(unique_username):
    """Isolation entre élèves : B ne doit jamais pouvoir lire ou supprimer une conversation de A,
    même en connaissant son id exact. 404 plutôt que 403 (choix délibéré, voir RAPPORT_MIGRATION.md) :
    on ne confirme même pas l'existence de la conversation à un compte qui n'en est pas propriétaire."""
    token_a = _register(unique_username).json()["token"]
    token_b = _register(unique_username).json()["token"]

    create_res = client.post(
        "/api/conversations", json={"class_level": "3ème", "chapter": "Les fractions"},
        headers=_auth_headers(token_a),
    )
    assert create_res.status_code == 200
    conv_id = create_res.json()["id"]

    assert client.get(f"/api/conversations/{conv_id}", headers=_auth_headers(token_b)).status_code == 404
    assert client.delete(f"/api/conversations/{conv_id}", headers=_auth_headers(token_b)).status_code == 404

    # A, lui, y accède normalement.
    own_res = client.get(f"/api/conversations/{conv_id}", headers=_auth_headers(token_a))
    assert own_res.status_code == 200
    assert own_res.json()["messages"] == []


def test_admin_demographics_requires_decideur_auth():
    assert client.get("/api/admin/demographics").status_code == 401


def test_export_history_requires_auth():
    assert client.get("/api/export/history").status_code == 401


def test_export_history_scoped_to_caller(unique_username):
    token = _register(unique_username).json()["token"]
    res = client.get("/api/export/history", headers=_auth_headers(token))
    assert res.status_code == 200
    assert res.json() == {"conversations": []}


def test_consent_endpoint_is_public():
    res = client.get("/api/consent")
    assert res.status_code == 200
    assert res.json()["version"]
    assert res.json()["text"]


def test_schools_search_short_query_returns_empty():
    res = client.get("/api/schools/search", params={"q": "a"})
    assert res.status_code == 200
    assert res.json() == {"schools": []}


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
