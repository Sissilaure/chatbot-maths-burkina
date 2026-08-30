"""Tests de routage/validation des endpoints FastAPI (main.py).

Ne fait AUCUN appel réel à Claude (pas d'appels /api/chat, /api/exercise "heureux chemin" avec
génération) : ces tests couvrent le routage, la validation des entrées et l'authentification,
qui sont justement les points où plusieurs bugs de cette session sont passés inaperçus (ex: une
route acceptant GET mais pas HEAD, un endpoint mutateur sans authentification).

Importer `main` instancie le RAGSystem complet (modèle d'embeddings + ChromaDB) : le premier test
de ce fichier est donc lent (10-20s), les suivants réutilisent la même instance via le TestClient.
"""
from datetime import date
import json

import psycopg
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


@pytest.mark.parametrize("method", ["GET", "HEAD"])
def test_summary_file_route_accepts_get_and_head(monkeypatch, tmp_path, method):
    """Même régression HEAD que /api/course (voir plus haut) — /api/summary/file sert un PDF de
    résumé prérédigé par l'équipe pédagogique, avec la même convention de dossiers que DATA_DIR
    (voir find_course_file). Répertoire isolé (tmp_path) plutôt que data/summaries/ réel : le test
    ne doit pas dépendre de fichiers effectivement déposés en prod."""
    chapter_dir = tmp_path / "2nde" / "Vecteurs du plan"
    chapter_dir.mkdir(parents=True)
    (chapter_dir / "resume.pdf").write_bytes(b"%PDF-1.4 fake")
    monkeypatch.setattr(main.config, "SUMMARIES_DIR", str(tmp_path))

    res = client.request(method, "/api/summary/file/2nde/Vecteurs du plan")
    assert res.status_code == 200
    assert res.headers["content-disposition"].startswith("inline")


def test_summary_file_route_404_for_missing_document(monkeypatch, tmp_path):
    monkeypatch.setattr(main.config, "SUMMARIES_DIR", str(tmp_path))
    res = client.head("/api/summary/file/4ème/Théorème de Pythagore")
    assert res.status_code == 404


def test_summary_file_route_404_for_invalid_chapter():
    res = client.head("/api/summary/file/2nde/Chapitre-qui-n-existe-pas")
    assert res.status_code == 404


def test_flashcards_route_reads_front_back(monkeypatch, tmp_path):
    """Schéma canonique front/back, cartes à la racine du JSON (voir get_flashcards)."""
    chapter_dir = tmp_path / "2nde" / "Vecteurs du plan"
    chapter_dir.mkdir(parents=True)
    (chapter_dir / "cartes.json").write_text(
        json.dumps([{"front": "Que vaut $2+2$ ?", "back": "$4$"}]), encoding="utf-8"
    )
    monkeypatch.setattr(main.config, "FLASHCARDS_DIR", str(tmp_path))

    res = client.get("/api/flashcards/2nde/Vecteurs du plan")
    assert res.status_code == 200
    data = res.json()
    assert data["cards"] == [{"front": "Que vaut $2+2$ ?", "back": "$4$"}]


def test_flashcards_route_accepts_wrapped_and_aliased_fields(monkeypatch, tmp_path):
    """Tolère un objet {"cards": [...]}  et des noms de champs alternatifs (question/answer)."""
    chapter_dir = tmp_path / "2nde" / "Vecteurs du plan"
    chapter_dir.mkdir(parents=True)
    (chapter_dir / "cartes.json").write_text(
        json.dumps({"cards": [{"question": "Q1", "answer": "R1"}]}), encoding="utf-8"
    )
    monkeypatch.setattr(main.config, "FLASHCARDS_DIR", str(tmp_path))

    res = client.get("/api/flashcards/2nde/Vecteurs du plan")
    assert res.status_code == 200
    assert res.json()["cards"] == [{"front": "Q1", "back": "R1"}]


def test_flashcards_route_reads_real_pedagogical_schema(monkeypatch, tmp_path):
    """Schéma réel livré par l'équipe pédagogique (voir LISEZ-MOI.md) : clé "cartes" (pas "cards"),
    champs recto/verso, plus des métadonnées ignorées (niveau/chapitre/source/nombre_cartes/id/
    lecon/type/difficulte/tags) qui ne doivent pas faire échouer le parsing."""
    chapter_dir = tmp_path / "3ème" / "Théorème de Thalès et sa réciproque"
    chapter_dir.mkdir(parents=True)
    (chapter_dir / "flashcards_3eme_Chapitre_8_Thales.json").write_text(
        json.dumps({
            "niveau": "3ème",
            "chapitre": "Chapitre 8 : Théorème de Thalès et sa réciproque",
            "source": "maths/3eme/Chapitre_8_Thales",
            "nombre_cartes": 1,
            "cartes": [{
                "id": "3E-CH08-001", "lecon": "Configuration de Thalès", "type": "definition",
                "recto": "Dans quelle configuration peut-on appliquer le théorème de Thalès ?",
                "verso": "Deux droites sécantes en $A$ coupées par deux droites parallèles.",
                "difficulte": 1, "tags": ["thales", "configuration"],
            }],
        }, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(main.config, "FLASHCARDS_DIR", str(tmp_path))

    res = client.get("/api/flashcards/3ème/Théorème de Thalès et sa réciproque")
    assert res.status_code == 200
    assert res.json()["cards"] == [{
        "front": "Dans quelle configuration peut-on appliquer le théorème de Thalès ?",
        "back": "Deux droites sécantes en $A$ coupées par deux droites parallèles.",
    }]


def test_flashcards_route_404_for_missing_document(monkeypatch, tmp_path):
    monkeypatch.setattr(main.config, "FLASHCARDS_DIR", str(tmp_path))
    res = client.get("/api/flashcards/4ème/Théorème de Pythagore")
    assert res.status_code == 404


def test_flashcards_route_404_for_invalid_chapter():
    res = client.get("/api/flashcards/2nde/Chapitre-qui-n-existe-pas")
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
    """Fiche d'inscription complète par défaut (class_code/gender/birth_date/is_candidat_libre/
    school_name sont obligatoires depuis le correctif de spécification — voir RAPPORT_MIGRATION.md).
    `overrides` permet à un test de ne faire varier qu'un seul champ à la fois."""
    payload = {
        "username": unique_username("api"),
        "password": "motdepasse123",
        "class_code": "3ème",
        "gender": "F",
        "birth_date": "2012-06-15",
        "is_candidat_libre": False,
        "school_name": "École Test",
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


def test_register_rejects_implausible_birth_date(unique_username):
    """birth_year (année seule, borné 1950-2020) est remplacé par birth_date (date complète,
    validée en âge — voir main.py::_is_plausible_birth_date, MIN_AGE_YEARS/MAX_AGE_YEARS) : un
    élève de moins de 6 ans ou de plus de 80 ans, ou une date dans le futur, doit être rejeté."""
    too_young = date.today().replace(year=date.today().year - 2)
    res = _register(unique_username, birth_date=too_young.isoformat())
    assert res.status_code == 400

    too_old = date.today().replace(year=date.today().year - 90)
    res = _register(unique_username, birth_date=too_old.isoformat())
    assert res.status_code == 400

    in_the_future = date.today().replace(year=date.today().year + 1)
    res = _register(unique_username, birth_date=in_the_future.isoformat())
    assert res.status_code == 400


def test_register_ignores_unknown_region_field(unique_username):
    """region a été supprimée de la fiche (app.users.region, RegisterRequest.region — voir
    migrations/004_birth_date_drop_region.sql) : l'envoyer encore ne doit plus rien casser, Pydantic
    ignore silencieusement les champs inconnus par défaut."""
    res = _register(unique_username, region="Centre")
    assert res.status_code == 200


def test_register_requires_profile_fields(unique_username):
    """class_code/gender/birth_date/is_candidat_libre sont désormais obligatoires : les omettre
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
        class_code="3ème", gender="F", birth_date=date(2012, 6, 15), is_candidat_libre=False,
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
        # class_code/gender/birth_date omis : NULL, comme un compte migré pas encore complété.
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


def test_class_level_is_forced_from_account_for_authenticated_student(unique_username, monkeypatch):
    """La classe est désormais fixée au compte (app.users.class_code, voir RAPPORT_MIGRATION.md) :
    un élève connecté ne doit jamais pouvoir la contourner en envoyant une autre valeur dans la
    requête. Un élève inscrit en Tle qui envoie class_level="6ème" doit tout de même obtenir une
    réponse ancrée sur la Terminale — vérifié ici en interceptant l'appel à generate_response pour
    inspecter la classe réellement transmise, sans dépendre d'un vrai appel à Claude."""
    register_res = _register(unique_username, class_code="Tle")
    token = register_res.json()["token"]

    captured = {}

    def fake_generate_response(question, class_level, chapter, history=None):
        captured["class_level"] = class_level
        return {"answer": "ok", "sources": [], "from_rag": False}

    monkeypatch.setattr(main.rag_system, "generate_response", fake_generate_response)

    res = client.post(
        "/api/chat",
        json={"question": "test", "class_level": "6ème", "chapter": "", "history": []},
        headers=_auth_headers(token),
    )
    assert res.status_code == 200
    assert captured["class_level"] == "Tle"

    # Un invité, lui, garde le comportement précédent : la classe qu'il envoie est utilisée telle quelle.
    guest_res = client.post(
        "/api/chat",
        json={"question": "test", "class_level": "6ème", "chapter": "", "history": []},
    )
    assert guest_res.status_code == 200
    assert captured["class_level"] == "6ème"


def test_simplify_is_gated_too(unique_username):
    """La porte 428 couvre aussi /api/simplify (elle écrit en base pour un compte connecté, voir
    _persist_message_best_effort) — pas seulement chat/exercice/remédiation. /api/summary/file
    n'a plus cette porte à tester : depuis le passage à un PDF prérédigé, c'est un simple fichier
    statique (comme /api/course), qui ne lit ni n'écrit aucune donnée élève."""
    import auth
    import database

    username = unique_username("noconsentgate")
    user = database.create_user(
        username, auth.hash_password("motdepasse123"),
        class_code="3ème", gender="F", birth_date=date(2012, 6, 15), is_candidat_libre=False,
        school_name="École Test",
    )
    token = auth.create_token(user["id"], user["username"])

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
    # consent_version NULL et class_code/gender/birth_date NULL : un compte migré non résolu,
    # dans l'état le plus bloqué possible.
    token = auth.create_token(user["id"], user["username"])
    headers = _auth_headers(token)

    consent_res = client.post("/api/consent/accept", headers=headers)
    assert consent_res.status_code == 200

    profile_res = client.patch(
        "/api/profile",
        json={"class_code": "3ème", "gender": "F", "birth_date": "2012-06-15", "is_candidat_libre": True},
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
    il doit être compté et visible dans GET /api/health::persistence_failures.
    class_code="6ème" explicite : depuis le correctif "classe fixée au compte"
    (_resolve_class_level), le serveur ignore le class_level envoyé par le client pour un compte
    connecté et utilise celui du compte — le chapitre utilisé plus bas ("Les fractions") doit donc
    être valide pour la classe du compte, pas juste pour la valeur envoyée dans la requête."""
    register_res = _register(unique_username, class_code="6ème")
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


def test_dead_db_connection_returns_503_not_401(unique_username, monkeypatch):
    """Réveil Neon (voir database.get_pool, check_connection) : une connexion morte doit se
    traduire par un 503 explicite sur les routes à authentification stricte, jamais par un 401
    (qui renverrait à tort l'élève à l'écran de connexion pour un token qui est en réalité
    valide — voir RAPPORT_MIGRATION.md, section points d'attention)."""
    token = _register(unique_username).json()["token"]

    def broken_get_user_by_id(user_id):
        raise psycopg.OperationalError(
            "consuming input failed: SSL connection has been closed unexpectedly"
        )

    monkeypatch.setattr(main.database, "get_user_by_id", broken_get_user_by_id)

    res = client.get("/api/conversations", headers=_auth_headers(token))
    assert res.status_code == 503
    assert res.status_code != 401


def test_dead_db_connection_degrades_to_guest_on_optional_auth(unique_username, monkeypatch):
    """Les routes ouvertes aux invités (voir auth.get_current_user_optional) n'ont pas besoin
    d'un compte pour fonctionner : une panne base pendant la résolution de l'utilisateur ne doit
    pas les faire échouer, seulement les traiter comme un invité."""
    token = _register(unique_username).json()["token"]

    def broken_get_user_by_id(user_id):
        raise psycopg.OperationalError("consuming input failed: SSL connection has been closed unexpectedly")

    monkeypatch.setattr(main.database, "get_user_by_id", broken_get_user_by_id)
    monkeypatch.setattr(
        main.rag_system, "generate_response",
        lambda *a, **k: {"answer": "ok", "sources": [], "from_rag": False},
    )

    res = client.post(
        "/api/chat",
        json={"question": "test", "class_level": "", "chapter": "", "history": []},
        headers=_auth_headers(token),
    )
    assert res.status_code == 200
