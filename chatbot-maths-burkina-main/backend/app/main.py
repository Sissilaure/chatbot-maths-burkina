"""API FastAPI du Chatbot Mathématiques Burkina Faso"""

import os
import sys
import json
import logging
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import PROGRAMME_SCOLAIRE, HOST, PORT
from .document_processor import DocumentProcessor
from .vector_store import VectorStore
from .llm_service import LLMService

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Services globaux
doc_processor = DocumentProcessor()
vector_store = VectorStore()
llm_service = LLMService()


# --- Modèles Pydantic ---

class QuestionRequest(BaseModel):
    question: str
    classe: str
    chapitre: str
    historique: list = []

class SimplifyRequest(BaseModel):
    question: str
    previous_response: str

class ExerciseRequest(BaseModel):
    classe: str
    chapitre: str
    difficulty: str = "moyen"

class IndexRequest(BaseModel):
    reset: bool = False


# --- Application ---

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie."""
    logger.info("=" * 50)
    logger.info("Chatbot Maths Burkina Faso - Démarrage")
    logger.info("=" * 50)
    
    # Vérifier l'état de l'index
    stats = vector_store.get_stats()
    logger.info(f"État de l'index: {stats['status']} ({stats['chunks']} chunks)")
    
    yield
    
    logger.info("Arrêt du serveur")


app = FastAPI(
    title="Chatbot Mathématiques Burkina Faso",
    description="API RAG pour l'accompagnement en mathématiques (6ème à Terminale)",
    version="1.0.0",
    lifespan=lifespan
)

# CORS pour permettre au frontend d'accéder à l'API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Endpoints ---

@app.get("/")
def root():
    """Page d'accueil de l'API."""
    return {
        "message": "Chatbot Mathématiques Burkina Faso",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "GET /programme": "Liste des classes et chapitres",
            "GET /stats": "Statistiques de l'index",
            "POST /question": "Poser une question",
            "POST /simplify": "Simplifier une réponse",
            "POST /exercise": "Générer un exercice",
            "POST /index": "Indexer/réindexer les documents",
            "POST /upload": "Uploader un document"
        }
    }


@app.get("/programme")
def get_programme():
    """Retourne la liste des classes et leurs chapitres."""
    return PROGRAMME_SCOLAIRE


@app.get("/stats")
def get_stats():
    """Retourne les statistiques de l'index et des documents."""
    index_stats = vector_store.get_stats()
    doc_stats = doc_processor.get_document_stats()
    
    return {
        "index": index_stats,
        "documents": doc_stats
    }


@app.post("/question")
def ask_question(request: QuestionRequest):
    """
    Pose une question au chatbot.
    
    Le système:
    1. Recherche les passages pertinents dans la base documentaire
    2. Filtre par classe et chapitre
    3. Génère une réponse avec le LLM
    """
    # Validation des paramètres
    classe_key = request.classe.lower().replace(" ", "")
    if classe_key not in PROGRAMME_SCOLAIRE:
        raise HTTPException(status_code=400, detail=f"Classe '{request.classe}' non trouvée")
    
    chapitre = request.chapitre
    classe_info = PROGRAMME_SCOLAIRE[classe_key]
    
    if chapitre not in classe_info["chapitres"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Chapitre '{chapitre}' non trouvé pour la classe {classe_info['nom']}"
        )
    
    # 1. Recherche vectorielle
    logger.info(f"Question: {request.question[:100]}... | Classe: {classe_info['nom']} | Chapitre: {chapitre}")
    
    context_chunks = vector_store.search(
        query=request.question,
        classe=classe_key,
        chapitre=chapitre,
        top_k=5
    )
    
    logger.info(f"Chunks trouvés: {len(context_chunks)}")
    
    # 2. Génération de la réponse
    response = llm_service.generate_response(
        question=request.question,
        context_chunks=context_chunks,
        classe=classe_info["nom"],
        chapitre=chapitre
    )
    
    # Ajouter des métadonnées
    response["classe"] = classe_info["nom"]
    response["chapitre"] = chapitre
    
    return response


@app.post("/simplify")
def simplify_response(request: SimplifyRequest):
    """Reformule une réponse de façon plus simple."""
    result = llm_service.simplify_response(
        question=request.question,
        previous_response=request.previous_response
    )
    return result


@app.post("/exercise")
def generate_exercise(request: ExerciseRequest):
    """Génère un exercice d'entraînement."""
    classe_key = request.classe.lower().replace(" ", "")
    if classe_key not in PROGRAMME_SCOLAIRE:
        raise HTTPException(status_code=400, detail=f"Classe '{request.classe}' non trouvée")
    
    result = llm_service.generate_exercise(
        classe=PROGRAMME_SCOLAIRE[classe_key]["nom"],
        chapitre=request.chapitre,
        difficulty=request.difficulty
    )
    return result


@app.post("/index")
def rebuild_index(request: IndexRequest = IndexRequest()):
    """
    Indexe ou réindexe les documents.
    
    Parcourt le dossier data/documents/ organisé par classe > chapitre,
    extrait le texte, découpe en chunks et indexe dans FAISS.
    """
    if request.reset:
        vector_store.clear_index()
        logger.info("Index existant supprimé")
    
    # Traiter tous les documents
    chunks = doc_processor.process_all_documents()
    
    if not chunks:
        logger.warning("Aucun document trouvé. Ajoute des fichiers dans data/documents/")
        return {
            "status": "warning",
            "message": "Aucun document trouvé à indexer. Place tes PDF/DOCX dans data/documents/",
            "chunks": 0,
            "organisation": {
                "6eme/": ["chapitre_nom/", "..."] ,
                "5eme/": ["chapitre_nom/", "..."],
                "...": "...",
                "data/documents/": "📁 Organise tes documents comme: data/documents/6eme/Nombres_entiers/cours.pdf"
            }
        }
    
    # Construire l'index
    vector_store.build_index(chunks)
    
    stats = vector_store.get_stats()
    
    return {
        "status": "success",
        "message": f"Indexation terminée: {len(chunks)} chunks traités",
        "chunks": len(chunks),
        "stats": stats
    }


@app.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    classe: str = Query(..., description="Classe (ex: 6eme, 5eme, ...)"),
    chapitre: str = Query(..., description="Nom du chapitre")
):
    """
    Upload un document PDF/DOCX/PPTX.
    
    Le fichier sera sauvegardé dans data/documents/{classe}/{chapitre}/
    """
    # Valider la classe
    classe_key = classe.lower().replace(" ", "")
    if classe_key not in PROGRAMME_SCOLAIRE:
        raise HTTPException(status_code=400, detail=f"Classe '{classe}' non valide")
    
    # Valider le format
    ext = Path(file.filename).suffix.lower()
    if ext not in doc_processor.SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Format non supporté: {ext}. Formats acceptés: {doc_processor.SUPPORTED_EXTENSIONS}"
        )
    
    # Créer le dossier
    dest_dir = Path("data") / "documents" / classe_key / chapitre
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    # Sauvegarder le fichier
    dest_path = dest_dir / file.filename
    content = await file.read()
    with open(dest_path, 'wb') as f:
        f.write(content)
    
    logger.info(f"Fichier uploadé: {dest_path}")
    
    # Option: réindexer automatiquement
    return {
        "status": "success",
        "message": f"Fichier '{file.filename}' uploadé dans {classe}/{chapitre}",
        "path": str(dest_path),
        "next_step": "POST /index pour réindexer les documents"
    }


@app.get("/health")
def health_check():
    """Vérifie que le service fonctionne."""
    index_ok = vector_store.initialized
    return {
        "status": "healthy" if index_ok else "degraded",
        "index_ready": index_ok,
        "message": "Le service fonctionne" if index_ok else "L'index n'est pas encore chargé. POST /index pour initialiser"
    }


# --- Point d'entrée ---

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=HOST,
        port=PORT,
        reload=True,
        log_level="info"
    )