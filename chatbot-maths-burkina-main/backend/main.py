from fastapi import Depends, FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel
from typing import Optional, List
import os
import json
import sqlite3
from datetime import datetime, timezone
from config import config
from curriculum_data import get_classes, get_class_name, get_chapters
from rag_system import RAGSystem
from document_processor import DocumentProcessor, find_course_file
import database
import auth

app = FastAPI(title="Chatbot Maths Burkina Faso API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG system
rag_system = RAGSystem()
rag_system.initialize_vector_store()

# Initialize accounts database (SQLite, comptes élèves optionnels)
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

class ExerciseRequest(BaseModel):
    class_level: str
    chapter: str = ""
    difficulty: Optional[int] = None
    history: List[HistoryTurn] = []

class SimplifyRequest(BaseModel):
    answer: str
    class_level: str
    question: str = ""
    chapter: str = ""

class RemediationRequest(BaseModel):
    class_level: str
    chapter: str
    history: List[HistoryTurn] = []

class SummaryRequest(BaseModel):
    history: List[HistoryTurn] = []
    class_level: str = ""
    chapter: str = ""

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

class LoginRequest(BaseModel):
    username: str
    password: str

class AuthResponse(BaseModel):
    token: str
    username: str
    role: str = "eleve"

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

@app.get("/")
def read_root():
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

@app.post("/api/chat", response_model=ChatResponse)
def ask_question(request: QuestionRequest):
    """Ask a question to the chatbot. La classe et le chapitre sont optionnels :
    si l'élève ne les précise pas, Claude répond en mode général."""
    try:
        class_level = request.class_level.strip()
        chapter = request.chapter.strip()

        if class_level and class_level not in get_classes():
            raise HTTPException(status_code=400, detail="Invalid class level")

        if chapter and class_level and chapter not in get_chapters(class_level):
            raise HTTPException(status_code=400, detail="Invalid chapter for this class")

        history = [turn.dict() for turn in request.history]
        response = rag_system.generate_response(
            request.question,
            class_level,
            chapter,
            history=history
        )

        return ChatResponse(**response)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat/stream")
def ask_question_stream(request: QuestionRequest):
    """Variante en streaming de /api/chat : renvoie la réponse au fil de l'eau (Server-Sent Events)
    afin que l'élève voie le texte s'écrire progressivement plutôt que d'attendre le bloc complet."""
    class_level = request.class_level.strip()
    chapter = request.chapter.strip()

    if class_level and class_level not in get_classes():
        raise HTTPException(status_code=400, detail="Invalid class level")
    if chapter and class_level and chapter not in get_chapters(class_level):
        raise HTTPException(status_code=400, detail="Invalid chapter for this class")

    history = [turn.dict() for turn in request.history]

    def event_stream():
        try:
            for event in rag_system.generate_response_stream(
                request.question, class_level, chapter, history=history
            ):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

@app.post("/api/remediation", response_model=RemediationResponse)
def get_remediation(request: RemediationRequest):
    """QCM diagnostique de 8 questions sur le chapitre : vérifie que l'élève a compris le cours
    avant de continuer, et pointe les notions précises à revoir sinon."""
    try:
        class_level = request.class_level.strip()
        chapter = request.chapter.strip()

        if class_level not in get_classes():
            raise HTTPException(status_code=400, detail="Invalid class level")
        if chapter not in get_chapters(class_level):
            raise HTTPException(status_code=400, detail="Invalid chapter for this class")

        history = [turn.dict() for turn in request.history]
        questions = rag_system.generate_remediation(class_level, chapter, history=history)
        return RemediationResponse(chapter=chapter, class_level=class_level, questions=questions)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
def get_summary(request: SummaryRequest):
    """Résumé des points essentiels : de la séance en cours si une conversation existe,
    sinon du chapitre choisi."""
    try:
        class_level = request.class_level.strip()
        chapter = request.chapter.strip()

        if class_level and class_level not in get_classes():
            raise HTTPException(status_code=400, detail="Invalid class level")
        if chapter and class_level and chapter not in get_chapters(class_level):
            raise HTTPException(status_code=400, detail="Invalid chapter for this class")

        history = [turn.dict() for turn in request.history]
        content = rag_system.generate_summary(history, class_level, chapter)
        return {"content": content}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/exercise", response_model=ExerciseResponse)
def generate_exercise(request: ExerciseRequest):
    """Generate a practice exercise. Le chapitre et la difficulté sont facultatifs : sans eux,
    un chapitre pertinent et une difficulté adaptée sont déduits (conversation récente, ou
    valeurs par défaut sinon)."""
    try:
        if request.class_level not in get_classes():
            raise HTTPException(status_code=400, detail="Invalid class level")

        chapter = request.chapter.strip()
        if chapter and chapter not in get_chapters(request.class_level):
            raise HTTPException(status_code=400, detail="Invalid chapter for this class")

        history = [turn.dict() for turn in request.history]
        response = rag_system.generate_exercise(
            request.class_level,
            chapter,
            request.difficulty,
            history=history
        )

        return ExerciseResponse(**response)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/simplify")
def simplify_answer(request: SimplifyRequest):
    """Simplify an answer for better understanding"""
    try:
        simplified = rag_system.simplify_answer(
            request.question,
            request.answer,
            request.class_level,
            request.chapter
        )

        return {
            "simplified_answer": simplified,
            "original_answer": request.answer
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
        raise HTTPException(status_code=500, detail=str(e))

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
        raise HTTPException(status_code=500, detail=str(e))

MIN_PASSWORD_LENGTH = 6

# ============================================================================
# COMPTES ÉLÈVES (auth optionnelle : nom d'utilisateur/mot de passe, JWT bearer)
# ============================================================================

@app.post("/api/auth/register", response_model=AuthResponse)
def register(request: RegisterRequest):
    username = request.username.strip()
    if not username:
        raise HTTPException(status_code=400, detail="Nom d'utilisateur requis")
    if len(request.password) < MIN_PASSWORD_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Le mot de passe doit contenir au moins {MIN_PASSWORD_LENGTH} caractères",
        )

    try:
        user_id = database.create_user(username, auth.hash_password(request.password))
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="Ce nom d'utilisateur est déjà pris")

    return AuthResponse(token=auth.create_token(user_id, username), username=username, role="eleve")

@app.post("/api/auth/login", response_model=AuthResponse)
def login(request: LoginRequest):
    user = database.get_user_by_username(request.username.strip())
    if not user or not auth.verify_password(request.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Nom d'utilisateur ou mot de passe incorrect")

    return AuthResponse(
        token=auth.create_token(user["id"], user["username"]), username=user["username"], role=user["role"]
    )

@app.get("/api/auth/me")
def get_me(user=Depends(auth.get_current_user)):
    return {"username": user["username"], "role": user["role"]}


# ---- Conversations / historique ----

@app.get("/api/conversations")
def get_conversations(user=Depends(auth.get_current_user)):
    return {"conversations": [dict(r) for r in database.list_conversations(user["id"])]}

@app.post("/api/conversations")
def create_conversation(request: CreateConversationRequest, user=Depends(auth.get_current_user)):
    return {"id": database.create_conversation(user["id"], request.class_level, request.chapter)}

@app.get("/api/conversations/{conversation_id}")
def get_conversation_detail(conversation_id: int, user=Depends(auth.get_current_user)):
    conversation = database.get_conversation(conversation_id, user["id"])
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return {**dict(conversation), "messages": database.get_messages(conversation_id)}

@app.delete("/api/conversations/{conversation_id}")
def delete_conversation_route(conversation_id: int, user=Depends(auth.get_current_user)):
    if not database.delete_conversation(conversation_id, user["id"]):
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return {"deleted": True}

@app.post("/api/conversations/{conversation_id}/messages")
def add_message_route(conversation_id: int, request: AppendMessageRequest, user=Depends(auth.get_current_user)):
    if not database.get_conversation(conversation_id, user["id"]):
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    new_title = database.add_message(
        conversation_id, request.type, request.text, request.kind, request.sources, request.data
    )
    return {"ok": True, "title": new_title}


# ---- Signaux de lacunes (alimentent l'accueil personnalisé) ----

@app.post("/api/remediation/results")
def post_remediation_results(request: RemediationResultsRequest, user=Depends(auth.get_current_user)):
    database.add_remediation_answers(
        user["id"], request.class_level, request.chapter, [a.dict() for a in request.answers]
    )
    return {"ok": True}

@app.post("/api/struggles")
def post_struggle(request: StruggleRequest, user=Depends(auth.get_current_user)):
    database.add_struggle(user["id"], request.class_level, request.chapter, request.question)
    return {"ok": True}


def _sqlite_to_epoch_ms(value: str) -> int:
    """Convertit un datetime('now') SQLite ("YYYY-MM-DD HH:MM:SS", UTC implicite) en epoch ms,
    pour que le frontend puisse réutiliser sa fonction timeAgo() existante (identique au
    traitement déjà fait côté JS pour updated_at des conversations)."""
    if not value:
        return 0
    try:
        return int(datetime.strptime(value, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp() * 1000)
    except ValueError:
        return 0


@app.get("/api/profile")
def get_student_profile(user=Depends(auth.get_current_user)):
    """Profil de progression de l'élève connecté (sujets récents, notions à revoir), reconstruit
    depuis son historique serveur — contrairement au profil "invité" du frontend (localStorage),
    ceci est propre à CE compte : se déconnecter puis se reconnecter (même sur un autre appareil,
    ou avec un compte différent sur le même navigateur) affiche toujours les bonnes données."""
    topics = [
        {
            "key": f"{r['class_level']}||{r['chapter']}",
            "classCode": r["class_level"],
            "chapitre": r["chapter"],
            "classeNom": get_class_name(r["class_level"]),
            "count": r["visits"],
            "lastVisited": _sqlite_to_epoch_ms(r["last_visited"]),
        }
        for r in database.get_recent_topics(user["id"])
    ]
    struggles = [
        {
            "classCode": r["class_level"],
            "chapitre": r["chapter"],
            "question": r["question"],
            "classeNom": get_class_name(r["class_level"]),
            "timestamp": _sqlite_to_epoch_ms(r["created_at"]),
        }
        for r in database.get_recent_struggles(user["id"])
    ]
    return {"topics": topics, "struggles": struggles}


# ---- Accueil personnalisé ----

@app.get("/api/greeting")
def get_greeting(user=Depends(auth.get_current_user)):
    if not database.has_any_history(user["id"]):
        return {"message": None}

    weak_notions = [dict(r) for r in database.get_weak_notions(user["id"])]
    struggles = [dict(r) for r in database.get_recent_struggles(user["id"])]
    topics = [dict(r) for r in database.get_recent_topics(user["id"])]
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


@app.get("/api/rag/status")
def rag_status():
    """Diagnostic rapide du RAG : permet de verifier que les documents sont indexes."""
    return {
        "initialized": bool(rag_system.index),
        "collection": rag_system.collection_name,
        "chunks_indexed": rag_system.collection_count(),
        "documents_dir": config.DATA_DIR,
        "chroma_dir": config.CHROMA_PERSIST_DIR,
    }


@app.get("/api/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "rag_system": "initialized" if rag_system.index else "not initialized",
        "rag_chunks": rag_system.collection_count(),
        "model": config.ANTHROPIC_MODEL,
        "llm_configured": bool(rag_system.anthropic_client)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.APP_HOST, port=config.APP_PORT)
