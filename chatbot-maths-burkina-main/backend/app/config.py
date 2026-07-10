"""Configuration du chatbot maths Burkina Faso"""

import os
from pathlib import Path

# Chemins
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DOCUMENTS_DIR = DATA_DIR / "documents"
INDEX_DIR = DATA_DIR / "faiss_index"

# Configuration du modèle d'embeddings
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
# Modèle multilingue gratuit, performant en français, taille réduite

# Paramètres RAG
CHUNK_SIZE = 600
CHUNK_OVERLAP = 150
TOP_K_RESULTS = 5

# Configuration LLM - Utilisation d'un modèle local gratuit via HuggingFace
LLM_MODEL = "HuggingFaceH4/zephyr-7b-beta"  
# Modèle open source performant, ou utiliser API gratuite

# Fallback: modèle plus léger si ressources limitées
LIGHT_LLM_MODEL = "microsoft/phi-2"

# Configuration du serveur
HOST = "0.0.0.0"
PORT = 8000

# Web search fallback
USE_WEB_SEARCH = True
WEB_SEARCH_ENGINE = "duckduckgo"

# Création des dossiers
DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
INDEX_DIR.mkdir(parents=True, exist_ok=True)

# Programme scolaire Burkina Faso : classes et chapitres
PROGRAMME_SCOLAIRE = {
    "6eme": {
        "nom": "6ème",
        "chapitres": [
            "Nombres entiers et décimaux",
            "Opérations fondamentales",
            "Fractions",
            "Nombres relatifs",
            "Géométrie: droites et segments",
            "Angles",
            "Triangles et quadrilatères",
            "Symétrie axiale",
            "Périmètres et aires",
            "Proportionnalité"
        ]
    },
    "5eme": {
        "nom": "5ème",
        "chapitres": [
            "Nombres relatifs: opérations",
            "Fractions: opérations",
            "Écritures fractionnaires",
            "Calcul littéral",
            "Équations",
            "Géométrie: parallélisme",
            "Triangles: inégalité triangulaire",
            "Parallélogrammes",
            "Symétrie centrale",
            "Aires et volumes"
        ]
    },
    "4eme": {
        "nom": "4ème",
        "chapitres": [
            "Nombres relatifs: multiplication et division",
            "Fractions: multiplication et division",
            "Puissances",
            "Calcul littéral: développement",
            "Équations et inéquations",
            "Théorème de Pythagore",
            "Théorème de Thalès",
            "Géométrie dans l'espace",
            "Statistiques",
            "Probabilités"
        ]
    },
    "3eme": {
        "nom": "3ème",
        "chapitres": [
            "Racines carrées",
            "Identités remarquables",
            "Équations et systèmes",
            "Inéquations",
            "Fonctions linéaires et affines",
            "Trigonométrie",
            "Théorème de Pythagore: réciproque",
            "Théorème de Thalès: réciproque",
            "Géométrie dans l'espace",
            "Statistiques et probabilités",
            "Préparation au BEPC"
        ]
    },
    "2nde": {
        "nom": "Seconde",
        "chapitres": [
            "Généralités sur les fonctions",
            "Fonctions de référence",
            "Équations et inéquations",
            "Vecteurs",
            "Géométrie analytique",
            "Statistiques descriptives",
            "Probabilités",
            "Algorithmique"
        ]
    },
    "1ere": {
        "nom": "Première",
        "chapitres": [
            "Second degré",
            "Dérivation",
            "Suites numériques",
            "Trigonométrie",
            "Produit scalaire",
            "Géométrie dans l'espace",
            "Probabilités conditionnelles",
            "Fonction exponentielle"
        ]
    },
    "terminale": {
        "nom": "Terminale",
        "chapitres": [
            "Fonctions: limites et continuité",
            "Dérivation et applications",
            "Fonction exponentielle et logarithme",
            "Intégration",
            "Suites numériques",
            "Trigonométrie",
            "Géométrie dans l'espace",
            "Probabilités: loi binomiale",
            "Lois de probabilité continues",
            "Préparation au Baccalauréat"
        ]
    }
}