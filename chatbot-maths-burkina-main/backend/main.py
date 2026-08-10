from fastapi import Depends, FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, model_validator
from typing import Optional, List
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import os
import json
import logging
from config import config
from curriculum_data import get_classes, get_class_name, get_chapters
from rag_system import RAGSystem
from document_processor import DocumentProcessor, find_course_file
from consent_text import CONSENT_VERSION, CONSENT_TEXT
import database
import auth

logger = logging.getLogger(__name__)

app = FastAPI(title="Chatbot Maths Burkina Faso API")

# Compteur en mémoire (remis à zéro à chaque redémarrage, comme le reste de l'état du process —
# voir aussi le limiter plus bas) des échecs d'écriture de la persistance best-effort (voir
# _persist_exchange_best_effort/_persist_message_best_effort). Exposé dans GET /api/health : un
# nombre qui grimpe en continu signale un problème de sauvegarde silencieux (ex: pool Postgres
# épuisé) qui ne remonterait sinon que dans les logs.
_persistence_failure_count = 0

# Déploiements "tout-en-un" (voir routes en fin de fichier) : dossier du build React/Vite,
# présent seulement si le frontend a été copié dans l'image à côté du backend. Absent en
# local/Railway (frontend déployé à part, ex. Vercel) : les routes concernées restent inactives.
_FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "frontend_dist")

# Limite de débit : protège à la fois le portefeuille (chaque appel Claude coûte) et les comptes
# (empêche de tester des mots de passe en boucle sur /api/auth/login). En mémoire par processus —
# suffisant pour un déploiement mono-instance ; passer sur un backend Redis si un jour on scale
# horizontalement.
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Remplace le detail par défaut de FastAPI (une liste d'objets d'erreur Pydantic, en anglais)
    par un message français unique portant sur la première erreur — cohérent avec le reste de
    l'API (voir handleJson côté frontend, qui affiche err.detail tel quel à l'élève) et lisible
    par quelqu'un qui n'a jamais vu du JSON Pydantic."""
    first = exc.errors()[0]
    field = str(first["loc"][-1]) if first.get("loc") else "champ"
    if first.get("type") == "missing":
        detail = f"Le champ « {field} » est requis."
    else:
        detail = f"Champ « {field} » invalide : {first.get('msg', '')}"
    return JSONResponse(status_code=422, content={"detail": detail})
AUTH_RATE_LIMIT = "5/minute"
LLM_RATE_LIMIT = "20/minute"
# Recherche d'établissement (autocomplétion frappée en direct) : plus permissif que les routes
# d'authentification, mais toujours borné pour éviter un usage détourné en scraping du référentiel.
SEARCH_RATE_LIMIT = "30/minute"

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# En-têtes de sécurité de base sur toutes les réponses : protège contre le clickjacking
# (X-Frame-Options), le MIME-sniffing (X-Content-Type-Options), et limite les informations de
# provenance envoyées vers d'autres sites (Referrer-Policy). HSTS est sans effet en local (HTTP)
# mais utile derrière Railway/Cloudflare qui terminent le HTTPS en amont.
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response

# Initialize RAG system
rag_system = RAGSystem()
rag_system.initialize_vector_store()

# Initialize accounts database (Postgres/Neon, schéma "app" — voir database.py). Sur la même
# base que l'index vectoriel du RAG (DATABASE_URL), mais dans un schéma séparé.
database.init_db()

# Request/Response models
class HistoryTurn(BaseModel):
    role: str
    content: str

class QuestionRequest(BaseModel):
    question: str
    class_level: str = ""
    chapter: str = ""
    history: List[HistoryTurn] = []
    # Si renseigné ET que l'appelant est authentifié, le backend persiste lui-même l'échange
    # (question + réponse) dans cette conversation — voir add_exchange côté database.py. La
    # conversation doit déjà exister (créée via POST /api/conversations) et appartenir à
    # l'appelant, sinon la persistance est silencieusement ignorée (la réponse au chat, elle,
    # est renvoyée normalement : un échec de sauvegarde ne doit jamais casser la conversation).
    conversation_id: Optional[str] = None

class ExerciseRequest(BaseModel):
    class_level: str
    chapter: str = ""
    difficulty: Optional[int] = None
    history: List[HistoryTurn] = []
    conversation_id: Optional[str] = None

class SimplifyRequest(BaseModel):
    answer: str
    class_level: str
    question: str = ""
    chapter: str = ""
    conversation_id: Optional[str] = None

class RemediationRequest(BaseModel):
    class_level: str
    chapter: str
    history: List[HistoryTurn] = []
    conversation_id: Optional[str] = None

class SummaryRequest(BaseModel):
    history: List[HistoryTurn] = []
    class_level: str = ""
    chapter: str = ""
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    sources: List[dict]
    from_rag: bool
    internet_search: Optional[bool] = False
    error: Optional[str] = None

class ExerciseResponse(BaseModel):
    enonce: str
    indices: List[str] = []
    solution: str = ""
    reponse_finale: str = ""
    chapter: str
    class_level: str
    difficulty: int = 2
    figure: Optional[dict] = None
    qcm: Optional[List[dict]] = None
    error: Optional[str] = None


class RemediationResponse(BaseModel):
    chapter: str
    class_level: str
    questions: List[dict]

class RegisterRequest(BaseModel):
    username: str
    password: str
    # Fiche d'inscription : obligatoire dès l'inscription (voir correctif de spécification —
    # un compte incomplet ne doit jamais être créé, contrairement à la version précédente de ce
    # formulaire). Les comptes migrés depuis SQLite, eux, PEUVENT avoir ces colonnes à NULL en
    # base (voir database.py, non modifié) : l'obligation ne porte que sur la création via cette
    # route, pas sur un CHECK/NOT NULL en base — voir PATCH /api/profile pour leur régularisation.
    class_code: str
    gender: str  # 'F' / 'M' — choix obligatoire, pas d'option "préfère ne pas répondre"
    birth_year: int
    is_candidat_libre: bool
    school_name: Optional[str] = None
    region: Optional[str] = None
    consent_accepted: bool

    @model_validator(mode="after")
    def _school_required_unless_candidat_libre(self):
        if not self.is_candidat_libre and not (self.school_name and self.school_name.strip()):
            raise ValueError(
                "school_name est requis sauf si is_candidat_libre est vrai"
            )
        return self

class LoginRequest(BaseModel):
    username: str
    password: str

class AuthResponse(BaseModel):
    token: str
    username: str
    role: str = "eleve"
    public_code: Optional[str] = None
    # Un nouveau compte (créé via /api/auth/register) a toujours les deux à True — seul un compte
    # migré depuis SQLite (voir migrate_sqlite_to_pg.py) ou inscrit sous un consentement antérieur
    # peut se reconnecter avec l'un des deux à False (voir require_consent/require_complete_profile
    # dans auth.py, et ConsentNotice.jsx / ProfileCompletionGate.jsx côté frontend).
    consent_ok: bool = True
    profile_complete: bool = True

class CreateConversationRequest(BaseModel):
    class_level: str = ""
    chapter: str = ""

class AppendMessageRequest(BaseModel):
    type: str
    text: Optional[str] = None
    kind: Optional[str] = None
    sources: List[dict] = []
    data: Optional[dict] = None

class RemediationResultAnswer(BaseModel):
    notion: str
    is_correct: bool

class RemediationResultsRequest(BaseModel):
    class_level: str
    chapter: str
    answers: List[RemediationResultAnswer]

class StruggleRequest(BaseModel):
    class_level: str
    chapter: str
    question: str

class ProfileUpdateRequest(BaseModel):
    class_code: Optional[str] = None
    gender: Optional[str] = None
    birth_year: Optional[int] = None
    is_candidat_libre: Optional[bool] = None
    region: Optional[str] = None
    school_name: Optional[str] = None

@app.get("/")
def read_root():
    # Déploiements "tout-en-un" (frontend servi par ce même backend, voir plus bas dans ce
    # fichier) : la page d'accueil doit être l'appli React, pas ce message JSON.
    index_path = os.path.join(_FRONTEND_DIST, "index.html")
    if os.path.isfile(index_path):
        return FileResponse(index_path)
    return {
        "message": "Chatbot Maths Burkina Faso API",
        "version": "1.0",
        "status": "running"
    }

@app.get("/api/classes")
def get_all_classes():
    """Get list of all available classes"""
    classes = []
    for class_code in get_classes():
        classes.append({
            "code": class_code,
            "name": get_class_name(class_code)
        })
    return {"classes": classes}

@app.get("/api/classes/{class_code}/chapters")
def get_class_chapters(class_code: str):
    """Get chapters for a specific class"""
    if class_code not in get_classes():
        raise HTTPException(status_code=404, detail="Class not found")

    chapters = get_chapters(class_code)
    return {
        "class_code": class_code,
        "class_name": get_class_name(class_code),
        "chapters": chapters
    }


def _ensure_authenticated_user_ready(user):
    """Portes 428 pour les routes ouvertes aux invités qui ÉCRIVENT en base pour un compte
    connecté (chat, chat/stream, exercice, remédiation, résumé, simplification, photo d'exercice —
    voir plus bas) : un invité (user=None) n'est jamais concerné, il continue comme avant. Un
    compte connecté doit en revanche avoir accepté le consentement courant ET avoir une fiche
    complète avant que quoi que ce soit ne soit persisté en son nom — les deux concernent surtout
    les comptes migrés depuis SQLite (consent_version et class_code/gender/birth_year à NULL, voir
    migrate_sqlite_to_pg.py). /api/course n'a PAS cette porte : elle ne stocke jamais rien.
    /api/profile et /api/consent* non plus : ce sont justement les routes qui permettent à un
    compte bloqué de se débloquer, elles ne peuvent pas dépendre d'un état déjà à jour.
    On n'utilise pas Depends(auth.require_consent)/Depends(auth.require_complete_profile)
    directement sur ces routes : ces dépendances forcent get_current_user (401 sans token), ce qui
    casserait le mode invité que ces mêmes routes doivent justement continuer à servir.
    Consentement vérifié avant la fiche : accepter le consentement est un préalable logique à
    toute collecte de données supplémentaires."""
    if not user:
        return
    if not auth.is_consent_ok(user):
        raise HTTPException(
            status_code=428,
            detail={"reason": "consent_required", "message": "Consentement requis avant de continuer."},
        )
    if not auth.is_profile_complete(user):
        raise HTTPException(
            status_code=428,
            detail={
                "reason": "profile_incomplete",
                "message": "Complète ta fiche d'inscription avant de continuer.",
            },
        )


def _persist_exchange_best_effort(user, conversation_id, question, answer, **meta):
    """Écrit un échange (question + réponse) côté serveur pour un élève connecté, sans jamais
    faire échouer la requête HTTP en cours si la persistance échoue (best-effort) : l'élève doit
    toujours recevoir sa réponse même si l'enregistrement de l'historique a un problème. Ignore
    silencieusement si l'appelant n'est pas connecté, n'a pas transmis de conversation_id, ou si
    cette conversation ne lui appartient pas (vérifié explicitement — voir database.get_conversation,
    qui filtre toujours par user_id)."""
    if not user or not conversation_id:
        return
    try:
        if not database.get_conversation(conversation_id, user["id"]):
            return
        database.add_exchange(conversation_id, user["id"], question, answer, **meta)
    except Exception as e:
        global _persistence_failure_count
        _persistence_failure_count += 1
        logger.error(
            "Persistance de l'échange échouée (conversation_id=%s, kind=%s, exception=%s): %s",
            conversation_id, meta.get("kind"), type(e).__name__, e,
        )


def _persist_message_best_effort(user, conversation_id, role, content, **meta):
    """Variante à un seul message (voir _persist_exchange_best_effort) : utilisée quand il n'y a
    pas de "question" élève naturelle à enregistrer en face (exercice généré, remédiation, résumé,
    simplification — voir les routes correspondantes plus bas)."""
    if not user or not conversation_id:
        return
    try:
        if not database.get_conversation(conversation_id, user["id"]):
            return
        database.add_message(conversation_id, user["id"], role, content, **meta)
    except Exception as e:
        global _persistence_failure_count
        _persistence_failure_count += 1
        logger.error(
            "Persistance du message échouée (conversation_id=%s, kind=%s, exception=%s): %s",
            conversation_id, meta.get("kind"), type(e).__name__, e,
        )


@app.post("/api/chat", response_model=ChatResponse)
@limiter.limit(LLM_RATE_LIMIT)
def ask_question(request: Request, payload: QuestionRequest, user=Depends(auth.get_current_user_optional)):
    """Ask a question to the chatbot. La classe et le chapitre sont optionnels :
    si l'élève ne les précise pas, Claude répond en mode général."""
    _ensure_authenticated_user_ready(user)
    try:
        class_level = payload.class_level.strip()
        chapter = payload.chapter.strip()

        if class_level and class_level not in get_classes():
            raise HTTPException(status_code=400, detail="Invalid class level")

        if chapter and class_level and chapter not in get_chapters(class_level):
            raise HTTPException(status_code=400, detail="Invalid chapter for this class")

        history = [turn.dict() for turn in payload.history]
        response = rag_system.generate_response(
            payload.question,
            class_level,
            chapter,
            history=history
        )

        _persist_exchange_best_effort(
            user, payload.conversation_id, payload.question, response.get("answer", ""),
            kind="chat", class_code=class_level or None, chapter=chapter or None,
            from_rag=response.get("from_rag"),
        )

        return ChatResponse(**response)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] /api/chat: {e}")
        raise HTTPException(status_code=500, detail="Une erreur interne est survenue, réessaie.")

@app.post("/api/chat/stream")
@limiter.limit(LLM_RATE_LIMIT)
def ask_question_stream(request: Request, payload: QuestionRequest, user=Depends(auth.get_current_user_optional)):
    """Variante en streaming de /api/chat : renvoie la réponse au fil de l'eau (Server-Sent Events)
    afin que l'élève voie le texte s'écrire progressivement plutôt que d'attendre le bloc complet."""
    _ensure_authenticated_user_ready(user)
    class_level = payload.class_level.strip()
    chapter = payload.chapter.strip()

    if class_level and class_level not in get_classes():
        raise HTTPException(status_code=400, detail="Invalid class level")
    if chapter and class_level and chapter not in get_chapters(class_level):
        raise HTTPException(status_code=400, detail="Invalid chapter for this class")

    history = [turn.dict() for turn in payload.history]

    def event_stream():
        full_text = ""
        from_rag = None
        try:
            for event in rag_system.generate_response_stream(
                payload.question, class_level, chapter, history=history
            ):
                if isinstance(event.get("delta"), str):
                    full_text += event["delta"]
                if event.get("done"):
                    from_rag = event.get("from_rag")
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            print(f"[ERROR] /api/chat/stream: {e}")
            yield f"data: {json.dumps({'error': 'Une erreur interne est survenue, réessaie.'}, ensure_ascii=False)}\n\n"
        finally:
            # Se déclenche aussi si le client se déconnecte en cours de génération (le serveur
            # ASGI referme alors le générateur, ce qui exécute ce bloc via GeneratorExit) : le
            # texte déjà produit jusque-là est sauvegardé, jamais perdu silencieusement.
            if full_text:
                _persist_exchange_best_effort(
                    user, payload.conversation_id, payload.question, full_text,
                    kind="chat", class_code=class_level or None, chapter=chapter or None,
                    from_rag=from_rag,
                )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@app.post("/api/remediation", response_model=RemediationResponse)
@limiter.limit(LLM_RATE_LIMIT)
def get_remediation(request: Request, payload: RemediationRequest, user=Depends(auth.get_current_user_optional)):
    """QCM diagnostique de 8 questions sur le chapitre : vérifie que l'élève a compris le cours
    avant de continuer, et pointe les notions précises à revoir sinon."""
    _ensure_authenticated_user_ready(user)
    try:
        class_level = payload.class_level.strip()
        chapter = payload.chapter.strip()

        if class_level not in get_classes():
            raise HTTPException(status_code=400, detail="Invalid class level")
        if chapter not in get_chapters(class_level):
            raise HTTPException(status_code=400, detail="Invalid chapter for this class")

        history = [turn.dict() for turn in payload.history]
        questions = rag_system.generate_remediation(class_level, chapter, history=history)

        _persist_message_best_effort(
            user, payload.conversation_id, "assistant",
            f"QCM de remédiation — {chapter}",
            kind="remediation", payload={"chapter": chapter, "class_level": class_level, "questions": questions},
            class_code=class_level, chapter=chapter,
        )

        return RemediationResponse(chapter=chapter, class_level=class_level, questions=questions)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] /api/remediation: {e}")
        raise HTTPException(status_code=500, detail="Une erreur interne est survenue, réessaie.")

@app.api_route("/api/course/{class_code}/{chapter}", methods=["GET", "HEAD"])
def get_course_file(class_code: str, chapter: str):
    """Renvoie le document de cours (PDF/DOCX/TXT) déposé pour cette classe/ce chapitre,
    tel que fourni par l'équipe pédagogique (voir ingest_documents.py). Accepte aussi HEAD :
    contrairement à Starlette, FastAPI n'ajoute pas HEAD automatiquement aux routes GET, et le
    frontend s'en sert pour vérifier la disponibilité du cours avant d'ouvrir un nouvel onglet."""
    if class_code not in get_classes():
        raise HTTPException(status_code=404, detail="Class not found")
    if chapter not in get_chapters(class_code):
        raise HTTPException(status_code=404, detail="Chapter not found")

    # Priorité à l'index vectoriel : un filtre EXACT classe+chapitre, fiable car l'ingestion classe
    # désormais les documents par leur CONTENU (pas leur nom de fichier). Repli sur la correspondance
    # de noms de fichiers pour les documents pas encore réindexés avec la classification par contenu.
    file_path = rag_system.find_course_file_from_index(class_code, chapter)
    if not file_path:
        file_path = find_course_file(config.DATA_DIR, class_code, chapter)
    if not file_path:
        raise HTTPException(status_code=404, detail="Aucun document de cours disponible pour ce chapitre")

    return FileResponse(file_path, filename=os.path.basename(file_path))

@app.post("/api/summary")
@limiter.limit(LLM_RATE_LIMIT)
def get_summary(request: Request, payload: SummaryRequest, user=Depends(auth.get_current_user_optional)):
    """Résumé des points essentiels : de la séance en cours si une conversation existe,
    sinon du chapitre choisi."""
    _ensure_authenticated_user_ready(user)
    try:
        class_level = payload.class_level.strip()
        chapter = payload.chapter.strip()

        if class_level and class_level not in get_classes():
            raise HTTPException(status_code=400, detail="Invalid class level")
        if chapter and class_level and chapter not in get_chapters(class_level):
            raise HTTPException(status_code=400, detail="Invalid chapter for this class")

        history = [turn.dict() for turn in payload.history]
        content = rag_system.generate_summary(history, class_level, chapter)

        _persist_message_best_effort(
            user, payload.conversation_id, "assistant", content,
            kind="summary", class_code=class_level or None, chapter=chapter or None,
        )

        return {"content": content}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] /api/summary: {e}")
        raise HTTPException(status_code=500, detail="Une erreur interne est survenue, réessaie.")

@app.post("/api/exercise", response_model=ExerciseResponse)
@limiter.limit(LLM_RATE_LIMIT)
def generate_exercise(request: Request, payload: ExerciseRequest, user=Depends(auth.get_current_user_optional)):
    """Generate a practice exercise. Le chapitre et la difficulté sont facultatifs : sans eux,
    un chapitre pertinent et une difficulté adaptée sont déduits (conversation récente, ou
    valeurs par défaut sinon)."""
    _ensure_authenticated_user_ready(user)
    try:
        if payload.class_level not in get_classes():
            raise HTTPException(status_code=400, detail="Invalid class level")

        chapter = payload.chapter.strip()
        if chapter and chapter not in get_chapters(payload.class_level):
            raise HTTPException(status_code=400, detail="Invalid chapter for this class")

        history = [turn.dict() for turn in payload.history]
        response = rag_system.generate_exercise(
            payload.class_level,
            chapter,
            payload.difficulty,
            history=history
        )

        _persist_message_best_effort(
            user, payload.conversation_id, "assistant",
            response.get("enonce") or f"Exercice — {response.get('chapter', chapter)}",
            kind="exercise", payload=response,
            class_code=payload.class_level, chapter=response.get("chapter") or chapter or None,
            difficulty=response.get("difficulty"),
        )

        return ExerciseResponse(**response)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] /api/exercise: {e}")
        raise HTTPException(status_code=500, detail="Une erreur interne est survenue, réessaie.")

ALLOWED_PHOTO_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif", "application/pdf"}


@app.post("/api/exercise/photo")
@limiter.limit(LLM_RATE_LIMIT)
async def explain_exercise_photo(
    request: Request,
    file: UploadFile = File(...),
    class_level: str = "",
    chapter: str = "",
    prompt: str = "",
    history: str = Form(""),
    conversation_id: str = Form(""),
    user=Depends(auth.get_current_user_optional),
):
    """Reçoit la photo (ou le PDF scanné) d'un exercice et renvoie une explication de la méthode
    suivie de la correction détaillée. Ouvert comme /api/chat et /api/exercise (pas d'authentification
    requise) : le fichier n'est jamais écrit sur disque, seulement transmis en mémoire à l'API Claude.

    `history` (JSON, champ de formulaire — pas la query string, qui a une limite de taille) permet
    de renvoyer la MÊME photo avec les échanges suivants de la conversation (voir le frontend,
    App.jsx::activePhoto) : sans ça, Claude "oublie" l'image dès le message suivant et ne peut plus
    répondre à des questions de suivi comme "résous la question a" sur cette même photo."""
    _ensure_authenticated_user_ready(user)
    try:
        if class_level and class_level not in get_classes():
            raise HTTPException(status_code=400, detail="Invalid class level")
        if chapter and class_level and chapter not in get_chapters(class_level):
            raise HTTPException(status_code=400, detail="Invalid chapter for this class")

        content_type = (file.content_type or "").lower()
        if content_type not in ALLOWED_PHOTO_CONTENT_TYPES:
            raise HTTPException(
                status_code=400,
                detail="Format non supporté (photo jpeg/png/webp/gif ou PDF attendu)",
            )

        file_bytes = await file.read()
        if not file_bytes:
            raise HTTPException(status_code=400, detail="Fichier vide")
        if len(file_bytes) > config.MAX_EXERCISE_PHOTO_SIZE_BYTES:
            raise HTTPException(status_code=400, detail="Fichier trop volumineux (8 Mo maximum)")

        history_list = []
        if history:
            try:
                parsed = json.loads(history)
                if isinstance(parsed, list):
                    history_list = parsed
            except (json.JSONDecodeError, TypeError):
                history_list = []

        answer = rag_system.explain_exercise_photo(file_bytes, content_type, class_level, chapter, prompt, history_list)

        _persist_exchange_best_effort(
            user, conversation_id or None, prompt or "[Photo d'exercice envoyée]", answer,
            kind="photo", class_code=class_level or None, chapter=chapter or None,
        )

        return {"answer": answer}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] /api/exercise/photo: {e}")
        raise HTTPException(status_code=500, detail="Une erreur interne est survenue, réessaie.")

@app.post("/api/simplify")
@limiter.limit(LLM_RATE_LIMIT)
def simplify_answer(request: Request, payload: SimplifyRequest, user=Depends(auth.get_current_user_optional)):
    """Simplify an answer for better understanding"""
    _ensure_authenticated_user_ready(user)
    try:
        simplified = rag_system.simplify_answer(
            payload.question,
            payload.answer,
            payload.class_level,
            payload.chapter
        )

        _persist_message_best_effort(
            user, payload.conversation_id, "assistant", simplified,
            kind="simplify", class_code=payload.class_level or None, chapter=payload.chapter or None,
        )

        return {
            "simplified_answer": simplified,
            "original_answer": payload.answer
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] /api/simplify: {e}")
        raise HTTPException(status_code=500, detail="Une erreur interne est survenue, réessaie.")

ALLOWED_UPLOAD_EXTENSIONS = (".pdf", ".docx", ".txt")


@app.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    class_level: str = None,
    chapter: str = None,
    decideur=Depends(auth.require_decideur),
):
    """Upload a document to the knowledge base. Réservé aux comptes décideur : modifie la base
    de connaissances servie à tous les élèves, et écrit un fichier sur le disque du serveur."""
    try:
        # os.path.basename() neutralise toute tentative de traversée de chemin (ex: filename
        # contenant "../../" ou un chemin absolu) : on n'écrit jamais hors de DATA_DIR.
        safe_filename = os.path.basename(file.filename or "")
        ext = os.path.splitext(safe_filename)[1].lower()
        if not safe_filename or ext not in ALLOWED_UPLOAD_EXTENSIONS:
            raise HTTPException(status_code=400, detail="Unsupported file format")

        os.makedirs(config.DATA_DIR, exist_ok=True)

        file_path = os.path.join(config.DATA_DIR, safe_filename)
        with open(file_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)

        processor = DocumentProcessor(config.DATA_DIR)
        metadata = {"class": class_level, "chapter": chapter}
        if ext == ".pdf":
            doc = processor.process_pdf(file_path, metadata)
        elif ext == ".docx":
            doc = processor.process_docx(file_path, metadata)
        else:
            doc = processor.process_txt(file_path, metadata)

        if doc:
            rag_system.add_documents([doc], doc["metadata"])
            return {
                "message": "Document uploaded and processed successfully",
                "filename": safe_filename,
                "metadata": doc["metadata"]
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to process document")

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] /api/documents/upload: {e}")
        raise HTTPException(status_code=500, detail="Une erreur interne est survenue, réessaie.")

@app.post("/api/documents/initialize-sample")
def initialize_sample_documents(decideur=Depends(auth.require_decideur)):
    """Initialize the knowledge base with sample documents. Réservé aux comptes décideur."""
    try:
        processor = DocumentProcessor(config.DATA_DIR)
        sample_docs = processor.create_sample_documents()

        rag_system.add_documents(sample_docs)

        return {
            "message": f"Initialized {len(sample_docs)} sample documents",
            "documents_count": len(sample_docs)
        }
    except Exception as e:
        print(f"[ERROR] /api/documents/initialize-sample: {e}")
        raise HTTPException(status_code=500, detail="Une erreur interne est survenue, réessaie.")

MIN_PASSWORD_LENGTH = 8
VALID_GENDERS = {"F", "M"}
MIN_BIRTH_YEAR = 1950
MAX_BIRTH_YEAR = 2020

# ============================================================================
# COMPTES ÉLÈVES (auth optionnelle : nom d'utilisateur/mot de passe, JWT bearer)
# ============================================================================

@app.post("/api/auth/register", response_model=AuthResponse)
@limiter.limit(AUTH_RATE_LIMIT)
def register(request: Request, payload: RegisterRequest):
    username = payload.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Nom d'utilisateur requis")
    if len(payload.password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Le mot de passe doit contenir au moins {MIN_PASSWORD_LENGTH} caractères",
        )
    if not payload.consent_accepted:
        raise HTTPException(status_code=400, detail="Le consentement est requis pour créer un compte")

    # class_code/gender/birth_year sont désormais obligatoires au niveau du type (voir
    # RegisterRequest) : Pydantic a déjà renvoyé 422 si l'un est absent. Il reste à vérifier que
    # les VALEURS fournies sont valides (une classe existante, un genre de la liste, une année
    # plausible) — ce que le type seul ne garantit pas.
    if payload.class_code not in get_classes():
        raise HTTPException(status_code=400, detail="Invalid class level")
    if payload.gender not in VALID_GENDERS:
        raise HTTPException(status_code=400, detail="Genre invalide")
    if not (MIN_BIRTH_YEAR <= payload.birth_year <= MAX_BIRTH_YEAR):
        raise HTTPException(status_code=400, detail="Année de naissance invalide")

    user = database.create_user(
        username,
        auth.hash_password(payload.password),
        class_code=payload.class_code or None,
        gender=payload.gender,
        birth_year=payload.birth_year,
        is_candidat_libre=payload.is_candidat_libre,
        # Le champ établissement n'a pas de sens pour un candidat libre : on l'ignore plutôt que
        # de laisser une saisie incohérente traîner en base.
        school_name=None if payload.is_candidat_libre else payload.school_name,
        region=payload.region,
        consent_version=CONSENT_VERSION,
    )
    if not user:
        raise HTTPException(status_code=409, detail="Ce nom d'utilisateur est déjà pris")

    # Un compte fraîchement créé par cette route a nécessairement les champs requis (Pydantic +
    # les vérifications ci-dessus) et vient d'accepter le consentement courant : les deux valent
    # toujours True ici (voir les défauts de AuthResponse). Explicité quand même pour ne pas
    # dépendre silencieusement des défauts si le modèle évolue.
    return AuthResponse(
        token=auth.create_token(user["id"], user["username"]),
        username=user["username"],
        role=user["role"],
        public_code=user["public_code"],
        consent_ok=True,
        profile_complete=True,
    )

@app.post("/api/auth/login", response_model=AuthResponse)
@limiter.limit(AUTH_RATE_LIMIT)
def login(request: Request, payload: LoginRequest):
    user = database.get_user_by_username(payload.username.strip())
    if not user or not auth.verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Nom d'utilisateur ou mot de passe incorrect")

    try:
        database.touch_last_login(user["id"])
    except Exception as e:
        print(f"[WARN] touch_last_login échoué pour {user['id']}: {e}")

    # Contrairement à register(), un compte existant peut être un compte migré depuis SQLite
    # (voir migrate_sqlite_to_pg.py) : consent_ok/profile_complete peuvent valoir False, ce que
    # le frontend utilise pour afficher ConsentNotice / ProfileCompletionGate sans attendre un
    # premier appel à une route métier qui échouerait en 428.
    return AuthResponse(
        token=auth.create_token(user["id"], user["username"]),
        username=user["username"],
        role=user["role"],
        public_code=user["public_code"],
        consent_ok=auth.is_consent_ok(user),
        profile_complete=auth.is_profile_complete(user),
    )

@app.get("/api/auth/me")
def get_me(user=Depends(auth.get_current_user)):
    return {
        "username": user["username"],
        "role": user["role"],
        "public_code": user["public_code"],
        "consent_ok": auth.is_consent_ok(user),
        "profile_complete": auth.is_profile_complete(user),
    }


# ---- Consentement (RGPD-like) ----

@app.get("/api/consent")
def get_consent():
    """Texte et version courante du consentement (voir consent_text.py). Public : affiché à
    l'inscription avant même la création du compte."""
    return {"version": CONSENT_VERSION, "text": CONSENT_TEXT}

@app.post("/api/consent/accept")
def accept_consent(user=Depends(auth.get_current_user)):
    """Enregistre l'acceptation de la version courante du consentement. Sert principalement aux
    comptes migrés depuis l'ancienne base SQLite (consent_version = NULL, voir
    migrate_sqlite_to_pg.py) et aux comptes inscrits sous un texte antérieur si celui-ci a changé
    depuis — un nouveau compte a déjà consenti à l'inscription (voir /api/auth/register)."""
    with database.get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            f"""UPDATE {database.SCHEMA}.users
                SET consent_version = %s, consent_at = now(), updated_at = now()
                WHERE id = %s""",
            (CONSENT_VERSION, user["id"]),
        )
    return {"ok": True, "consent_version": CONSENT_VERSION}


# ---- Établissements (autocomplétion à l'inscription) ----

@app.get("/api/schools/search")
@limiter.limit(SEARCH_RATE_LIMIT)
def search_schools(request: Request, q: str = ""):
    return {"schools": database.search_schools(q)}


# ---- Profil (complétion différée de la fiche) ----

@app.patch("/api/profile")
def update_profile(payload: ProfileUpdateRequest, user=Depends(auth.get_current_user)):
    if payload.class_code and payload.class_code not in get_classes():
        raise HTTPException(status_code=400, detail="Invalid class level")
    if payload.gender is not None and payload.gender not in VALID_GENDERS:
        raise HTTPException(status_code=400, detail="Genre invalide")
    if payload.birth_year is not None and not (MIN_BIRTH_YEAR <= payload.birth_year <= MAX_BIRTH_YEAR):
        raise HTTPException(status_code=400, detail="Année de naissance invalide")

    fields = payload.dict(exclude_unset=True)
    updated = database.update_profile_fields(user["id"], **fields)
    if not updated:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return {
        "class_code": updated.get("class_code"),
        "gender": updated.get("gender"),
        "birth_year": updated.get("birth_year"),
        "is_candidat_libre": updated.get("is_candidat_libre"),
        "region": updated.get("region"),
        "school_raw": updated.get("school_raw"),
    }


# ---- Conversations / historique ----

@app.get("/api/conversations")
def get_conversations(user=Depends(auth.get_current_user)):
    return {"conversations": database.list_conversations(user["id"])}

@app.post("/api/conversations")
def create_conversation(request: CreateConversationRequest, user=Depends(auth.get_current_user)):
    conv = database.create_conversation(user["id"], request.class_level, request.chapter)
    return {"id": conv["id"]}

@app.get("/api/conversations/{conversation_id}")
def get_conversation_detail(conversation_id: str, user=Depends(auth.get_current_user)):
    conversation = database.get_conversation(conversation_id, user["id"])
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return {**conversation, "messages": database.get_messages(conversation_id, user["id"])}

@app.delete("/api/conversations/{conversation_id}")
def delete_conversation_route(conversation_id: str, user=Depends(auth.get_current_user)):
    if not database.delete_conversation(conversation_id, user["id"]):
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return {"deleted": True}

@app.post("/api/conversations/{conversation_id}/messages")
def add_message_route(conversation_id: str, request: AppendMessageRequest, user=Depends(auth.get_current_user)):
    """DÉPRÉCIÉE : la persistance des messages se fait désormais côté serveur, directement dans
    /api/chat, /api/chat/stream, /api/exercise, /api/remediation, /api/summary, /api/simplify et
    /api/exercise/photo (voir conversation_id dans leurs payloads respectifs). Le frontend
    n'appelle plus cette route ; elle reste disponible pour ne pas casser un client externe qui
    l'utiliserait encore, adaptée aux nouvelles signatures de database.py (role/kind/payload au
    lieu de type/sources/data)."""
    if not database.get_conversation(conversation_id, user["id"]):
        raise HTTPException(status_code=404, detail="Conversation introuvable")

    role = "user" if request.type == "user" else "assistant"
    kind = request.kind if request.kind in database.MESSAGE_KINDS else (
        request.type if request.type in database.MESSAGE_KINDS else "chat"
    )
    payload_data = request.data
    if payload_data is None and request.sources:
        payload_data = {"sources": request.sources}

    message = database.add_message(
        conversation_id, user["id"], role, request.text or "", kind=kind, payload=payload_data,
    )
    if not message:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return {"ok": True}


# ---- Export de l'historique complet (réservé à son propriétaire) ----

@app.get("/api/export/history")
def export_history(user=Depends(auth.get_current_user)):
    return {"conversations": database.export_user_history(user["id"])}


# ---- Signaux de lacunes (alimentent l'accueil personnalisé) ----

@app.post("/api/remediation/results")
def post_remediation_results(request: RemediationResultsRequest, user=Depends(auth.get_current_user)):
    database.add_remediation_answers(
        user["id"], request.class_level, request.chapter, [a.dict() for a in request.answers]
    )
    return {"ok": True}

@app.post("/api/struggles")
def post_struggle(request: StruggleRequest, user=Depends(auth.get_current_user)):
    database.add_struggle(user["id"], request.question, request.class_level, request.chapter)
    return {"ok": True}


@app.get("/api/profile")
def get_student_profile(user=Depends(auth.get_current_user)):
    """Profil de progression de l'élève connecté (sujets récents, notions à revoir), reconstruit
    depuis son historique serveur — contrairement au profil "invité" du frontend (localStorage),
    ceci est propre à CE compte : se déconnecter puis se reconnecter (même sur un autre appareil,
    ou avec un compte différent sur le même navigateur) affiche toujours les bonnes données."""
    topics = [
        {
            "key": f"{r['class_code']}||{r['chapter']}",
            "classCode": r["class_code"],
            "chapitre": r["chapter"],
            "classeNom": get_class_name(r["class_code"]),
            "lastVisited": int(r["updated_at"].timestamp() * 1000) if r.get("updated_at") else 0,
        }
        for r in database.get_recent_topics(user["id"])
    ]
    struggles = [
        {
            # database.get_recent_struggles ne sélectionne pas class_code (voir RAPPORT_MIGRATION.md,
            # bug signalé) : accès défensif via .get() plutôt que r["class_code"], qui lèverait
            # KeyError et casserait toute cette route pour un élève ayant des notions à revoir.
            "classCode": r.get("class_code"),
            "chapitre": r["chapter"],
            "question": r["notion"],
            "classeNom": get_class_name(r["class_code"]) if r.get("class_code") else "",
            "timestamp": int(r["created_at"].timestamp() * 1000) if r.get("created_at") else 0,
        }
        for r in database.get_recent_struggles(user["id"])
    ]
    return {"topics": topics, "struggles": struggles}


# ---- Accueil personnalisé ----

def _adapt_history_rows_for_welcome_message(weak_notions_rows, struggles_rows, topics_rows):
    """rag_system.generate_welcome_message() attend des clés (chapter, class_level, wrong_count,
    question, visits) héritées de l'ancien schéma SQLite. Le nouveau database.py (fourni, non
    modifié — voir RAPPORT_MIGRATION.md) ne les fournit pas toutes : get_weak_notions() ne
    regroupe que par "notion" (pas de chapter/class_level dans le résultat), et
    get_recent_struggles() ne renvoie ni "question" ni "class_code". On complète ici avec des
    valeurs par défaut plutôt que de modifier rag_system.py ou database.py — au prix d'un message
    d'accueil moins précis que ce que permettait l'ancien schéma (voir le rapport)."""
    weak_notions = [
        {
            "notion": r["notion"],
            "chapter": r.get("chapter", ""),
            "class_level": r.get("class_level", ""),
            "wrong_count": r.get("misses", 0),
        }
        for r in weak_notions_rows
    ]
    struggles = [
        {
            "question": r.get("question", r["notion"]),
            "chapter": r.get("chapter", ""),
            "class_level": r.get("class_level", ""),
        }
        for r in struggles_rows
    ]
    topics = [
        {
            "chapter": r["chapter"],
            "class_level": r.get("class_code", ""),
            "visits": r.get("visits", 1),
        }
        for r in topics_rows
    ]
    return weak_notions, struggles, topics


@app.get("/api/greeting")
def get_greeting(user=Depends(auth.get_current_user)):
    if not database.has_any_history(user["id"]):
        return {"message": None}

    weak_notions, struggles, topics = _adapt_history_rows_for_welcome_message(
        database.get_weak_notions(user["id"]),
        database.get_recent_struggles(user["id"]),
        database.get_recent_topics(user["id"]),
    )
    message = rag_system.generate_welcome_message(user["username"], weak_notions, struggles, topics)
    return {"message": message}


# ============================================================================
# TABLEAU DE BORD DÉCIDEURS (statistiques agrégées, jamais nominatives)
# ============================================================================

@app.get("/api/admin/overview")
def admin_overview(decideur=Depends(auth.require_decideur)):
    return database.get_admin_overview()

@app.get("/api/admin/success-by-chapter")
def admin_success_by_chapter(class_level: str = "", decideur=Depends(auth.require_decideur)):
    return {"chapters": database.get_success_by_chapter(class_level or None)}

@app.get("/api/admin/weak-notions")
def admin_weak_notions(class_level: str = "", decideur=Depends(auth.require_decideur)):
    return {"notions": database.get_weak_notions_global(class_level or None)}

@app.get("/api/admin/trend")
def admin_trend(class_level: str = "", decideur=Depends(auth.require_decideur)):
    return {"trend": database.get_success_trend(class_level or None)}

@app.get("/api/admin/activity")
def admin_activity(class_level: str = "", decideur=Depends(auth.require_decideur)):
    return {"activity": database.get_activity_trend(class_level or None)}

@app.get("/api/admin/demographics")
def admin_demographics(class_level: str = "", decideur=Depends(auth.require_decideur)):
    return database.get_demographics(class_level or None)


@app.get("/api/rag/status")
def rag_status(decideur=Depends(auth.require_decideur)):
    """Diagnostic rapide du RAG : permet de verifier que les documents sont indexes.
    Réservé aux comptes décideur : expose des détails internes (chemins sur le serveur)."""
    return {
        "initialized": bool(rag_system.index),
        "table": rag_system.table_name,
        "chunks_indexed": rag_system.collection_count(),
        "documents_dir": config.DATA_DIR,
    }


@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "rag_system": "initialized" if rag_system.index else "not initialized",
        "rag_chunks": rag_system.collection_count(),
        "model": config.ANTHROPIC_MODEL,
        "llm_configured": bool(rag_system.anthropic_client),
        # Nombre d'échecs d'écriture de la persistance best-effort (voir
        # _persist_exchange_best_effort/_persist_message_best_effort) depuis le démarrage du
        # process. Une valeur qui grimpe en continu signale un problème de sauvegarde silencieux.
        "persistence_failures": _persistence_failure_count,
    }


# ============================================================================
# FRONTEND (optionnel, suite) — _FRONTEND_DIST défini en haut du fichier.
# DOIT rester en dernier dans ce fichier : la route générique "/{full_path}"
# capturerait sinon les routes /api/* définies plus haut.
# ============================================================================

if os.path.isdir(_FRONTEND_DIST):
    _assets_dir = os.path.join(_FRONTEND_DIST, "assets")
    if os.path.isdir(_assets_dir):
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="frontend-assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        """Sert index.html pour toute route qui n'est ni /api/* ni un fichier statique
        existant (le routage côté client — React Router — gère le reste dans le navigateur)."""
        candidate = os.path.join(_FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(_FRONTEND_DIST, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.APP_HOST, port=config.APP_PORT)
