"""Moteur vectoriel FAISS pour la recherche sémantique"""

import os
import json
import pickle
from pathlib import Path
from typing import List, Dict, Optional

try:
    import numpy as np
except ImportError:
    np = None

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SentenceTransformer = None
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("Warning: sentence_transformers non installé. Le système RAG sera désactivé.")

try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    faiss = None
    FAISS_AVAILABLE = False
    print("Warning: faiss non installé. La recherche vectorielle sera désactivée.")

from .config import EMBEDDING_MODEL, INDEX_DIR, TOP_K_RESULTS


class VectorStore:
    """Gère l'indexation vectorielle et la recherche sémantique."""

    def __init__(self):
        self.model = None
        self.index = None
        self.chunks = []  # Liste des chunks avec leurs métadonnées
        self.initialized = False
        self.rag_available = SENTENCE_TRANSFORMERS_AVAILABLE and FAISS_AVAILABLE
        
        if not self.rag_available:
            print("Mode dégradé: RAG non disponible. Les réponses seront générées sans contexte.")
            return
        
        # Charger l'index s'il existe
        self._load_index()

    def _get_model(self):
        """Charge le modèle d'embeddings (lazy loading)."""
        if not self.rag_available:
            return None
        if self.model is None:
            print(f"Chargement du modèle d'embeddings: {EMBEDDING_MODEL}")
            self.model = SentenceTransformer(EMBEDDING_MODEL)
        return self.model

    def _load_index(self):
        """Charge l'index FAISS et les chunks depuis le disque."""
        if not self.rag_available:
            return
        index_file = INDEX_DIR / "faiss.index"
        chunks_file = INDEX_DIR / "chunks.pkl"
        
        if index_file.exists() and chunks_file.exists():
            try:
                self.index = faiss.read_index(str(index_file))
                with open(chunks_file, 'rb') as f:
                    self.chunks = pickle.load(f)
                self.initialized = True
                print(f"Index chargé: {len(self.chunks)} chunks, dimension {self.index.d}")
            except Exception as e:
                print(f"Erreur lors du chargement de l'index: {e}")
                self.initialized = False

    def build_index(self, chunks: List[Dict]):
        """Construit l'index FAISS à partir des chunks."""
        if not self.rag_available:
            print("RAG non disponible. Impossible de construire l'index.")
            return
        model = self._get_model()
        
        if not chunks:
            print("Aucun chunk à indexer")
            return
        
        print(f"Génération des embeddings pour {len(chunks)} chunks...")
        texts = [chunk["text"] for chunk in chunks]
        embeddings = model.encode(texts, show_progress_bar=True, convert_to_numpy=True)
        
        # Normaliser pour la similarité cosinus
        faiss.normalize_L2(embeddings)
        
        dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(dimension)  # Inner Product = cosinus après normalisation
        self.index.add(embeddings)
        self.chunks = chunks
        
        # Sauvegarder
        INDEX_DIR.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(INDEX_DIR / "faiss.index"))
        with open(INDEX_DIR / "chunks.pkl", 'wb') as f:
            pickle.dump(self.chunks, f)
        
        self.initialized = True
        print(f"Index construit et sauvegardé: {len(chunks)} chunks")

    def search(self, query: str, classe: Optional[str] = None, 
               chapitre: Optional[str] = None, top_k: int = TOP_K_RESULTS) -> List[Dict]:
        """Recherche les chunks les plus pertinents."""
        if not self.rag_available or not self.initialized or self.index is None:
            return []
        
        model = self._get_model()
        
        # Encoder la requête
        query_embedding = model.encode([query], convert_to_numpy=True)
        faiss.normalize_L2(query_embedding)
        
        # Recherche
        scores, indices = self.index.search(query_embedding, top_k * 3)  # Chercher plus pour filtrer
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < 0 or idx >= len(self.chunks):
                continue
            
            chunk = self.chunks[idx]
            score = float(scores[0][i])
            
            # Filtrer par classe et chapitre si spécifiés
            if classe and chunk["metadata"].get("classe", "").lower() != classe.lower():
                continue
            if chapitre and chunk["metadata"].get("chapitre", "").lower() != chapitre.lower():
                continue
            
            results.append({
                "text": chunk["text"],
                "score": score,
                "metadata": chunk["metadata"]
            })
            
            if len(results) >= top_k:
                break
        
        return results

    def get_stats(self) -> Dict:
        """Retourne des statistiques sur l'index."""
        if not self.initialized:
            return {"status": "non initialisé", "chunks": 0}
        
        classes = {}
        for chunk in self.chunks:
            classe = chunk["metadata"].get("classe", "inconnu")
            if classe not in classes:
                classes[classe] = 0
            classes[classe] += 1
        
        return {
            "status": "initialisé",
            "chunks": len(self.chunks),
            "dimension": self.index.d if self.index else 0,
            "classes": classes
        }

    def clear_index(self):
        """Supprime l'index."""
        self.index = None
        self.chunks = []
        self.initialized = False
        
        index_file = INDEX_DIR / "faiss.index"
        chunks_file = INDEX_DIR / "chunks.pkl"
        
        if index_file.exists():
            index_file.unlink()
        if chunks_file.exists():
            chunks_file.unlink()
        
        print("Index supprimé")