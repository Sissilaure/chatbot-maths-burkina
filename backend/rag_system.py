import os
import chromadb
from chromadb.config import Settings
from llama_index.core import VectorStoreIndex, StorageContext, Document, Settings as LlamaSettings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from config import config
from curriculum_data import CURRICULUM
import requests
from bs4 import BeautifulSoup
import json

class RAGSystem:
    def __init__(self):
        self.embed_model = HuggingFaceEmbedding(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        LlamaSettings.embed_model = self.embed_model
        
        self.hf_api_key = config.HUGGINGFACE_API_KEY
        self.hf_model = config.HUGGINGFACE_MODEL
        
        self.chroma_client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)
        self.collection_name = "maths_burkina"
        self.index = None
        self.storage_context = None
        
    def initialize_vector_store(self):
        """Initialize or load the vector store"""
        try:
            collection = self.chroma_client.get_collection(name=self.collection_name)
            vector_store = ChromaVectorStore(chroma_collection=collection)
            self.storage_context = StorageContext.from_defaults(vector_store=vector_store)
            self.index = VectorStoreIndex.from_vector_store(
                vector_store=vector_store,
                embed_model=self.embed_model
            )
            print("Vector store loaded successfully")
        except Exception as e:
            print(f"Creating new vector store: {e}")
            try:
                collection = self.chroma_client.create_collection(name=self.collection_name)
            except:
                collection = self.chroma_client.get_collection(name=self.collection_name)
            vector_store = ChromaVectorStore(chroma_collection=collection)
            self.storage_context = StorageContext.from_defaults(vector_store=vector_store)
            self.index = VectorStoreIndex.from_vector_store(
                vector_store=vector_store,
                embed_model=self.embed_model
            )
            print("Vector store initialized")
    
    def add_documents(self, documents, metadata=None):
        """Add documents to the vector store"""
        if metadata is None:
            metadata = {}
        
        docs = []
        for doc in documents:
            doc_metadata = metadata.copy()
            if isinstance(doc, dict):
                docs.append(Document(
                    text=doc.get("text", ""),
                    metadata=doc.get("metadata", doc_metadata)
                ))
            else:
                docs.append(Document(text=doc, metadata=doc_metadata))
        
        splitter = SentenceSplitter(
            chunk_size=config.CHUNK_SIZE,
            chunk_overlap=config.CHUNK_OVERLAP
        )
        
        for doc in docs:
            nodes = splitter.get_nodes_from_documents([doc])
            self.index.insert_nodes(nodes)
        
        print(f"Added {len(docs)} documents to vector store")
    
    def query(self, question, class_level=None, chapter=None, top_k=None):
        """Query the RAG system"""
        if top_k is None:
            top_k = config.TOP_K
        
        filters = {}
        if class_level:
            filters["class"] = class_level
        if chapter:
            filters["chapter"] = chapter
        
        query_engine = self.index.as_query_engine(
            similarity_top_k=top_k,
            filters=filters if filters else None
        )
        
        response = query_engine.query(question)
        return response
    
    def search_internet(self, query):
        """Fallback internet search using DuckDuckGo"""
        try:
            url = "https://duckduckgo.com/html/"
            params = {"q": f"mathématiques {query}"}
            headers = {"User-Agent": "Mozilla/5.0"}
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            results = []
            for result in soup.find_all('a', class_='result__url', limit=5):
                title = result.get_text()
                link = result.get('href')
                results.append({"title": title, "link": link})
            
            return results
        except Exception as e:
            print(f"Internet search error: {e}")
            return []
    
    def generate_response(self, question, class_level, chapter):
        """Generate a response with RAG and internet fallback"""
        try:
            # Try RAG first
            context = ""
            sources = []
            
            try:
                response = self.query(question, class_level, chapter)
                if response and len(response.source_nodes) > 0:
                    context = "\n".join([node.text for node in response.source_nodes])
                    sources = [node.metadata for node in response.source_nodes]
            except:
                pass  # RAG failed, continue without context
            
            # Generate answer using Hugging Face API
            answer = self._generate_with_hf(question, context, class_level, chapter)
            
            return {
                "answer": answer,
                "sources": sources,
                "from_rag": len(sources) > 0
            }
        except Exception as e:
            print(f"Error generating response: {e}")
            return {
                "answer": f"Une erreur s'est produite. Erreur: {str(e)}",
                "sources": [],
                "from_rag": False,
                "error": str(e)
            }
    
    def _generate_with_hf(self, question, context, class_level, chapter):
        """Generate answer using local knowledge base (no external API dependency)"""
        try:
            # Use local knowledge base instead of external API
            context_text = context if context else "Aucun contexte documentaire disponible."
            
            # Generate response based on curriculum knowledge
            response = self._generate_local_response(question, class_level, chapter, context_text)
            return response
            
        except Exception as e:
            print(f"Generation error: {e}")
            return self._generate_local_response(question, class_level, chapter, "")
    
    def _generate_local_response(self, question, class_level, chapter, context):
        """Generate response using local curriculum knowledge"""
        
        # Knowledge base for key chapters
        knowledge_base = {
            "Théorème de Pythagore": """
Le théorème de Pythagore est un résultat fondamental en géométrie. Il s'applique aux triangles rectangles.

**Énoncé :** Dans un triangle rectangle, le carré de la longueur de l'hypoténuse est égal à la somme des carrés des longueurs des deux autres côtés.

**Formule :** Si ABC est un triangle rectangle en A, alors BC² = AB² + AC²
- BC est l'hypoténuse (le côté opposé à l'angle droit)
- AB et AC sont les cathètes (les côtés de l'angle droit)

**Utilisation :** Ce théorème permet de calculer la longueur d'un côté d'un triangle rectangle quand on connaît les deux autres.

**Exemple :** Si AB = 3 cm et AC = 4 cm, alors BC² = 3² + 4² = 9 + 16 = 25, donc BC = 5 cm.
""",
            "Théorème de Thalès": """
Le théorème de Thalès permet de calculer des longueurs dans des configurations de triangles emboîtés ou coupés par une parallèle.

**Énoncé :** Si deux droites parallèles coupent deux sécantes, alors elles déterminent sur ces sécantes des segments proportionnels.

**Formule :** Dans un triangle ABC, si une droite parallèle à BC coupe AB en D et AC en E, alors :
AD/AB = AE/AC = DE/BC

**Utilisation :** Calculer une longueur manquante dans une configuration de Thalès.

**Exemple :** Si AD = 2 cm, AB = 6 cm et DE = 3 cm, alors AE/AC = 2/6 = 1/3, donc AC = 3 × AE.
""",
            "Fractions": """
Une fraction représente une partie d'un tout.

**Définition :** Une fraction a/b représente a parts égales d'un tout divisé en b parts.

**Opérations :**
- **Addition/Soustraction :** Il faut le même dénominateur. a/b + c/b = (a+c)/b
- **Multiplication :** (a/b) × (c/d) = (a×c)/(b×d)
- **Division :** (a/b) ÷ (c/d) = (a×d)/(b×c)

**Simplification :** Diviser le numérateur et le dénominateur par leur PGCD.

**Exemple :** 2/4 = 1/2 (en divisant par 2)
""",
            "Équations du premier degré": """
Une équation du premier degré à une inconnue est de la forme ax + b = 0.

**Résolution :**
1. Isoler le terme avec x : ax = -b
2. Diviser par a : x = -b/a

**Exemple :** 2x + 4 = 0
→ 2x = -4
→ x = -2

**Vérification :** Remplacer x par la solution pour vérifier.
""",
            "Géométrie dans l'espace : sphères et boules": """
**Sphère :** Surface fermée dont tous les points sont à la même distance du centre.

**Boule :** Ensemble des points situés à une distance inférieure ou égale au rayon du centre.

**Formules :**
- Aire de la sphère : A = 4πR²
- Volume de la boule : V = (4/3)πR³

**Exemple :** Pour R = 3 cm :
- Aire = 4π × 9 = 36π cm² ≈ 113 cm²
- Volume = (4/3)π × 27 = 36π cm³ ≈ 113 cm³
""",
            "Trigonométrie dans le triangle rectangle": """
La trigonométrie étudie les relations entre les angles et les côtés d'un triangle rectangle.

**Formules principales :**
- cos(Â) = côté adjacent / hypoténuse
- sin(Â) = côté opposé / hypoténuse
- tan(Â) = côté opposé / côté adjacent

**Moyen mnémotechnique :** SOH-CAH-TOA
- SOH : Sinus = Opposé/Hypoténuse
- CAH : Cosinus = Adjacent/Hypoténuse
- TOA : Tangente = Opposé/Adjacent

**Exemple :** Dans un triangle rectangle avec angle de 30°, cos(30°) ≈ 0,866
""",
            "default": f"""
Pour le chapitre "{chapter}" de niveau {class_level}, voici une explication générale :

Ce chapitre fait partie du programme officiel de mathématiques du Burkina Faso. Il est essentiel pour comprendre les concepts mathématiques fondamentaux.

**Conseils d'étude :**
1. Relisez attentivement votre cours
2. Faites des exercices d'application
3. N'hésitez pas à demander de l'aide à votre professeur

Pour une réponse plus détaillée sur votre question spécifique, je vous recommande de consulter vos manuels scolaires ou de demander à votre professeur.
"""
        }
        
        # Find matching chapter in knowledge base
        chapter_key = None
        for key in knowledge_base.keys():
            if key.lower() in chapter.lower() or chapter.lower() in key.lower():
                chapter_key = key
                break
        
        if chapter_key and chapter_key != "default":
            base_response = knowledge_base[chapter_key]
        else:
            base_response = knowledge_base["default"]
        
        # Add context if available
        if context and context != "Aucun contexte documentaire disponible.":
            return f"{base_response}\n\n**Informations supplémentaires :**\n{context[:500]}..."
        
        return base_response
    
    def generate_exercise(self, class_level, chapter):
        """Generate a practice exercise for a given class and chapter"""
        # Use local knowledge base to generate exercise
        exercises = {
            "Théorème de Pythagore": f"""
**Exercice de mathématiques - Niveau {class_level}**
**Chapitre : Théorème de Pythagore**

**Énoncé :**
Un triangle ABC est rectangle en A. On donne AB = 6 cm et AC = 8 cm.
Calcule la longueur BC.

**Étapes de résolution :**
1. Identifie le triangle rectangle : ABC est rectangle en A, donc l'hypoténuse est BC.
2. Applique le théorème de Pythagore : BC² = AB² + AC²
3. Remplace par les valeurs : BC² = 6² + 8² = 36 + 64 = 100
4. Calcule BC : BC = √100 = 10 cm

**Réponse finale :** BC = 10 cm
""",
            "Théorème de Thalès": f"""
**Exercice de mathématiques - Niveau {class_level}**
**Chapitre : Théorème de Thalès**

**Énoncé :**
Dans un triangle ABC, une droite parallèle à BC coupe AB en D et AC en E.
On donne AD = 3 cm, AB = 9 cm et AE = 4 cm. Calcule AC.

**Étapes de résolution :**
1. Identifie la configuration : (DE) // (BC)
2. Applique le théorème de Thalès : AD/AB = AE/AC
3. Remplace par les valeurs : 3/9 = 4/AC
4. Produit en croix : 3 × AC = 9 × 4 → 3AC = 36
5. Calcule AC : AC = 36/3 = 12 cm

**Réponse finale :** AC = 12 cm
""",
            "Fractions": f"""
**Exercice de mathématiques - Niveau {class_level}**
**Chapitre : Fractions**

**Énoncé :**
Calcule et simplifie le résultat : 3/4 + 5/6

**Étapes de résolution :**
1. Mets les fractions au même dénominateur : PPCM(4,6) = 12
2. 3/4 = 9/12 et 5/6 = 10/12
3. Additionne : 9/12 + 10/12 = 19/12
4. Vérifie si la fraction est simplifiable : 19 est premier, donc 19/12 est irréductible

**Réponse finale :** 19/12
""",
            "Équations du premier degré": f"""
**Exercice de mathématiques - Niveau {class_level}**
**Chapitre : Équations du premier degré**

**Énoncé :**
Résous l'équation : 3x + 7 = 22

**Étapes de résolution :**
1. Isoler le terme avec x : 3x = 22 - 7
2. Calculer : 3x = 15
3. Diviser par 3 : x = 15/3
4. Solution : x = 5

**Vérification :** 3(5) + 7 = 15 + 7 = 22 ✓

**Réponse finale :** x = 5
"""
        }
        
        # Find matching exercise
        exercise_key = None
        for key in exercises.keys():
            if key.lower() in chapter.lower() or chapter.lower() in key.lower():
                exercise_key = key
                break
        
        if exercise_key:
            return {
                "exercise": exercises[exercise_key],
                "chapter": chapter,
                "class_level": class_level
            }
        
        # Default exercise
        return {
            "exercise": f"""
**Exercice de mathématiques - Niveau {class_level}**
**Chapitre : {chapter}**

**Énoncé :**
Résous le problème suivant sur le chapitre "{chapter}" adapté au programme de {class_level}.

**Consignes :**
1. Lis attentivement l'énoncé
2. Identifie les données importantes
3. Applique les formules et méthodes vues en cours
4. Vérifie tes résultats

**Conseil :** Relis ton cours sur {chapter} et entraîne-toi avec des exercices similaires.
""",
            "chapter": chapter,
            "class_level": class_level
        }
