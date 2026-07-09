# Chatbot Maths Burkina Faso

Assistant éducatif en mathématiques pour les élèves et enseignants du Burkina Faso, basé sur une architecture RAG (Retrieval-Augmented Generation).

## 🎯 Objectifs

- Fournir un accompagnement en mathématiques adapté au programme burkinabè
- Couvrir les niveaux de la 6ème à la Terminale
- Offrir des réponses pédagogiques basées sur les supports officiels
- Être accessible même avec une connectivité limitée

## 🏗️ Architecture

### Backend (FastAPI)
- **Framework**: FastAPI
- **RAG System**: LlamaIndex + ChromaDB
- **LLM**: Hugging Face Inference API (Mistral-7B) - gratuit via API
- **Embeddings**: Sentence Transformers (paraphrase-multilingual-MiniLM-L12-v2)
- **Base vectorielle**: ChromaDB (stockage local)

### Frontend (React + Vite)
- **Framework**: React 18 avec Vite
- **Styling**: TailwindCSS
- **Math rendering**: KaTeX
- **Icons**: Lucide React

## 📋 Prérequis

### Logiciels requis
- Python 3.9 ou supérieur
- Node.js 18 ou supérieur
- Git (optionnel)

### Configuration Hugging Face (Optionnel mais recommandé)
1. Créez un compte gratuit sur [Hugging Face](https://huggingface.co)
2. Générez un token API : https://huggingface.co/settings/tokens
3. Ajoutez le token dans le fichier `.env` (voir configuration ci-dessous)

**Note** : Le système fonctionne sans API key en utilisant le tier gratuit de Hugging Face, mais avec des limitations de rate.

## 🚀 Installation et Lancement

### 1. Cloner le projet
```bash
git clone <repository-url>
cd chatbot-maths-burkina
```

### 2. Configuration du Backend

#### Windows (PowerShell)
```powershell
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

#### Linux/Mac
```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Configuration des variables d'environnement
```bash
# Copier le fichier d'exemple
copy .env.example .env

# Éditer .env et ajouter votre clé API Hugging Face (optionnel)
# HUGGINGFACE_API_KEY=votre_clé_ici
```

### 3. Lancer le Backend

#### Windows (PowerShell)
```powershell
python main.py
```

#### Linux/Mac
```bash
python main.py
```

Le backend sera accessible sur `http://localhost:8000`

### 4. Configuration du Frontend

#### Ouvrir un nouveau terminal
```bash
cd frontend
npm install
```

### 5. Lancer le Frontend

```bash
npm run dev
```

Le frontend sera accessible sur `http://localhost:5173`

## 📁 Structure du Projet

```
chatbot-maths-burkina/
├── backend/
│   ├── main.py                 # API FastAPI
│   ├── config.py               # Configuration
│   ├── rag_system.py           # Système RAG
│   ├── document_processor.py   # Traitement des documents
│   ├── curriculum_data.py      # Données du programme
│   ├── requirements.txt        # Dépendances Python
│   ├── .env.example           # Exemple de configuration
│   └── data/
│       ├── documents/         # Documents PDF/DOCX/TXT
│       └── chroma_db/         # Base vectorielle ChromaDB
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ClassSelector.jsx
│   │   │   ├── ChapterSelector.jsx
│   │   │   └── ChatInterface.jsx
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── index.css
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
├── docs/
│   └── documentation_technique.md
└── README.md
```

## 📚 Ajout de Documents

### Via l'interface API
```bash
curl -X POST "http://localhost:8000/api/documents/upload" \
  -F "file=@votre_document.pdf" \
  -F "class_level=3ème" \
  -F "chapter=Théorème de Thalès"
```

### Formats supportés
- PDF (.pdf)
- Word (.docx)
- Texte (.txt)

### Initialisation avec des documents exemples
```bash
curl -X POST "http://localhost:8000/api/documents/initialize-sample"
```

## 🔧 API Endpoints

### GET `/api/classes`
Retourne la liste de toutes les classes disponibles

### GET `/api/classes/{class_code}/chapters`
Retourne les chapitres pour une classe spécifique

### POST `/api/chat`
Pose une question au chatbot
```json
{
  "question": "Qu'est-ce que le théorème de Pythagore ?",
  "class_level": "4ème",
  "chapter": "Théorème de Pythagore"
}
```

### POST `/api/exercise`
Génère un exercice pour un chapitre
```json
{
  "class_level": "4ème",
  "chapter": "Théorème de Pythagore"
}
```

### POST `/api/simplify`
Simplifie une réponse
```json
{
  "answer": "réponse à simplifier",
  "class_level": "4ème"
}
```

## 🎨 Fonctionnalités de l'Interface

- **Sélection de classe** : De la 6ème à la Terminale
- **Sélection de chapitre** : Chapitres adaptés à chaque classe
- **Chat interactif** : Interface de conversation intuitive
- **Support mathématique** : Rendu des formules mathématiques avec KaTeX
- **Simplification** : Bouton pour obtenir une explication plus simple
- **Génération d'exercices** : Création d'exercices personnalisés
- **Sources citées** : Affichage des sources documentaires
- **Recherche internet** : Fallback automatique si pas de réponse dans la base

## 🔒 Sécurité et Confidentialité

- Aucune donnée personnelle n'est stockée de manière permanente
- Les conversations ne sont pas conservées après la session
- Les documents uploadés sont traités localement
- Pas de transmission de données vers des serveurs externes (sauf recherche internet fallback)

## 📊 Performance

- **Temps de réponse** : < 5 secondes (objectif)
- **Chunk size** : 700 tokens
- **Chunk overlap** : 150 tokens
- **Top-K retrieval** : 4 documents

## 🐛 Dépannage

### Erreur de connexion Hugging Face
- Vérifiez votre connexion internet
- Si vous utilisez une API key, vérifiez qu'elle est correcte dans `.env`
- Sans API key, le système utilise le tier gratuit (rate limits possibles)

### Erreur de connexion au backend
- Vérifiez que le backend tourne sur le port 8000
- Vérifiez les CORS dans `config.py`
- Vérifiez que les dépendances Python sont installées

### Problèmes avec les embeddings
- Vérifiez que les dépendances sont installées
- Le premier téléchargement du modèle d'embeddings peut prendre du temps
- Assurez-vous d'avoir assez d'espace disque (~500MB pour le modèle)

### Réponses lentes
- Le premier appel peut être plus lent (chargement du modèle)
- Utilisez une API key Hugging Face pour de meilleures performances
- Vérifiez votre connexion internet

## 🤝 Contribution

Ce projet est développé pour le système éducatif burkinabè. Pour contribuer :

1. Ajoutez des documents officiels du programme
2. Améliorez les prompts pédagogiques
3. Signalez les bugs et suggestions d'amélioration

## 📄 Licence

Ce projet est développé dans le cadre éducatif pour le Burkina Faso.

## 👥 Équipe

- Développement : Équipe technique
- Validation pédagogique : Enseignants référents
- Support : Direction du projet

## 📞 Contact

Pour toute question ou problème technique, contactez l'équipe de développement.

---

**Version** : 1.0  
**Date** : Juillet 2026  
**Statut** : Prototype fonctionnel (MVP)
