"""Tests de database.py (Postgres/Neon). Voir conftest.py : tout compte créé ici doit passer
par le fixture unique_username() pour être nettoyé automatiquement en fin de test."""
import re

import database as db

PUBLIC_CODE_RE = re.compile(r"^CM-\d{4}-[A-Z0-9]{6}$")


def _make_user(unique_username, role: str = "eleve"):
    username = unique_username(role)
    user = db.create_user(username, password_hash="x", role=role)
    assert user is not None
    return user


def test_public_code_unique_and_well_formed(unique_username):
    user_a = _make_user(unique_username)
    user_b = _make_user(unique_username)

    assert PUBLIC_CODE_RE.match(user_a["public_code"])
    assert PUBLIC_CODE_RE.match(user_b["public_code"])
    assert user_a["public_code"] != user_b["public_code"]


def test_create_user_rejects_duplicate_username(unique_username):
    username = unique_username("dup")
    first = db.create_user(username, password_hash="x")
    again = db.create_user(username, password_hash="y")

    assert first is not None
    assert again is None  # nom déjà pris


def test_conversation_and_messages_isolated_between_students(unique_username):
    student_a = _make_user(unique_username)
    student_b = _make_user(unique_username)

    conv = db.create_conversation(student_a["id"], "3ème", "Théorème de Pythagore et sa réciproque")
    db.add_exchange(conv["id"], student_a["id"], "Question de A", "Réponse à A")

    # B ne doit jamais pouvoir lire la conversation ou les messages de A, même en connaissant
    # son UUID exact.
    assert db.get_conversation(conv["id"], student_b["id"]) is None
    assert db.get_messages(conv["id"], student_b["id"]) == []

    # A, lui, les voit bien.
    assert db.get_conversation(conv["id"], student_a["id"]) is not None
    messages = db.get_messages(conv["id"], student_a["id"])
    assert len(messages) == 2


def test_delete_conversation_is_scoped_to_owner(unique_username):
    student_a = _make_user(unique_username)
    student_b = _make_user(unique_username)
    conv = db.create_conversation(student_a["id"], "6ème", "Les fractions")

    # B ne peut pas supprimer la conversation de A.
    assert db.delete_conversation(conv["id"], student_b["id"]) is False
    assert db.get_conversation(conv["id"], student_a["id"]) is not None

    # A le peut.
    assert db.delete_conversation(conv["id"], student_a["id"]) is True
    assert db.get_conversation(conv["id"], student_a["id"]) is None


def test_message_seq_is_ordered_and_incremental(unique_username):
    student = _make_user(unique_username)
    conv = db.create_conversation(student["id"], "Tle", "Nombres complexes")

    db.add_message(conv["id"], student["id"], "user", "Premier message")
    db.add_message(conv["id"], student["id"], "assistant", "Deuxième message")
    db.add_message(conv["id"], student["id"], "user", "Troisième message")

    messages = db.get_messages(conv["id"], student["id"])
    assert [m["seq"] for m in messages] == [1, 2, 3]
    assert [m["content"] for m in messages] == [
        "Premier message", "Deuxième message", "Troisième message",
    ]


def test_admin_aggregates_hidden_below_min_cohort(unique_username):
    chapter = f"Chapitre test {unique_username('')}"  # nom garanti unique, pas de collision
    class_code = "3ème"

    # Un seul élève répond : sous MIN_COHORT (5 par défaut), la cellule doit rester invisible.
    student = _make_user(unique_username)
    db.add_remediation_answers(
        student["id"], class_code, chapter,
        [{"notion": "Notion test", "question": "Q1", "is_correct": False}],
    )

    by_chapter = db.get_success_by_chapter(class_code)
    assert not any(row["chapter"] == chapter for row in by_chapter)

    weak = db.get_weak_notions_global(class_code)
    assert not any(row["notion"] == "Notion test" for row in weak)


def test_admin_aggregates_visible_at_min_cohort(unique_username):
    chapter = f"Chapitre test {unique_username('')}"
    class_code = "3ème"

    for _ in range(db.MIN_COHORT):
        student = _make_user(unique_username)
        db.add_remediation_answers(
            student["id"], class_code, chapter,
            [{"notion": "Notion test visible", "question": "Q1", "is_correct": True}],
        )

    by_chapter = db.get_success_by_chapter(class_code)
    assert any(row["chapter"] == chapter for row in by_chapter)

    # Toutes les réponses sont correctes ici : get_weak_notions_global (qui ne remonte que les
    # notions avec au moins un échec, voir get_weak_notions) peut légitimement ne rien lister.
    # On vérifie seulement que l'appel ne casse pas et respecte le type attendu.
    weak = db.get_weak_notions_global(class_code)
    assert isinstance(weak, list)


def test_admin_filters_work_without_type_error(unique_username):
    """Régression du bug IndeterminateDatatype (voir RAPPORT_MIGRATION.md) : ces appels doivent
    réussir aussi bien avec un filtre qu'avec class_code=None (aucun filtre)."""
    for fn in (db.get_success_by_chapter, db.get_weak_notions_global,
               db.get_success_trend, db.get_activity_trend):
        assert isinstance(fn(None), list)
        assert isinstance(fn("3ème"), list)
    assert isinstance(db.get_demographics(None), dict)
    assert isinstance(db.get_demographics("3ème"), dict)


def test_create_user_accepts_null_is_candidat_libre(unique_username):
    """Un compte migré depuis SQLite n'a jamais répondu à cette question (voir
    migrate_sqlite_to_pg.py) : la colonne doit rester NULL plutôt que de retomber sur un défaut
    silencieux à false (voir backend/migrations/002_nullable_candidat_libre.sql)."""
    username = unique_username("nullcandlibre")
    user = db.create_user(username, password_hash="x", is_candidat_libre=None)
    assert user is not None
    assert user["is_candidat_libre"] is None


def test_create_user_rejects_nsp_gender(unique_username):
    """Le genre est restreint à 'F'/'M' depuis le correctif de spécification (contrainte CHECK
    en base, voir backend/migrations/003_gender_two_values.sql)."""
    import psycopg

    username = unique_username("nspgender")
    try:
        db.create_user(username, password_hash="x", gender="NSP")
        assert False, "aurait dû lever une violation de contrainte CHECK"
    except psycopg.errors.CheckViolation:
        pass
