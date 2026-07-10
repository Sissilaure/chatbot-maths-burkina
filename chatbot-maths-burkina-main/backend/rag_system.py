import os
import shutil
import chromadb
from chromadb.config import Settings
from llama_index.core import VectorStoreIndex, StorageContext, Document, Settings as LlamaSettings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.vector_stores import MetadataFilters, ExactMatchFilter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore
from config import config
from curriculum_data import CURRICULUM
import requests
from bs4 import BeautifulSoup
import json
import anthropic
import re

class RAGSystem:
    def __init__(self):
        self.embed_model = HuggingFaceEmbedding(
            model_name="sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        )
        LlamaSettings.embed_model = self.embed_model
        
        # Configuration Anthropic Claude
        self.anthropic_api_key = config.ANTHROPIC_API_KEY
        self.anthropic_model = config.ANTHROPIC_MODEL
        self.anthropic_client = None
        if self.anthropic_api_key:
            try:
                self.anthropic_client = anthropic.Anthropic(api_key=self.anthropic_api_key)
                print(f"[OK] Anthropic Claude API configuree avec le modele {self.anthropic_model}")
            except Exception as e:
                print(f"[WARN] Erreur initialisation Anthropic: {e}")
        
        self.chroma_client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)
        self.collection_name = "maths_burkina"
        self.index = None
        self.storage_context = None
        
    def _build_index(self, collection):
        vector_store = ChromaVectorStore(chroma_collection=collection)
        self.storage_context = StorageContext.from_defaults(vector_store=vector_store)
        self.index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            embed_model=self.embed_model
        )

    def _get_or_create_collection(self):
        try:
            return self.chroma_client.get_collection(name=self.collection_name)
        except Exception:
            return self.chroma_client.create_collection(name=self.collection_name)

    def _reset_store(self):
        shutil.rmtree(config.CHROMA_PERSIST_DIR, ignore_errors=True)
        os.makedirs(config.CHROMA_PERSIST_DIR, exist_ok=True)
        self.chroma_client = chromadb.PersistentClient(path=config.CHROMA_PERSIST_DIR)

    def initialize_vector_store(self):
        try:
            collection = self._get_or_create_collection()
            self._build_index(collection)
            print("Vector store loaded successfully")
        except Exception as e:
            print(f"Existing vector store is incompatible, resetting it: {e}")
            self._reset_store()
            collection = self._get_or_create_collection()
            self._build_index(collection)
            print("Vector store initialized")
    
    def add_documents(self, documents, metadata=None):
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
        if top_k is None:
            top_k = config.TOP_K
        
        exact_filters = []
        if class_level:
            exact_filters.append(ExactMatchFilter(key="class", value=class_level))
        if chapter:
            exact_filters.append(ExactMatchFilter(key="chapter", value=chapter))
        
        metadata_filters = MetadataFilters(filters=exact_filters) if exact_filters else None
        retriever = self.index.as_retriever(
            similarity_top_k=top_k,
            filters=metadata_filters
        )
        
        return retriever.retrieve(question)
    
    def search_internet(self, query):
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

    def _call_claude(self, system_prompt: str, user_message: str, max_tokens: int = 1024) -> str:
        """Appelle l'API Claude d'Anthropic et retourne la réponse texte."""
        if not self.anthropic_client:
            print("⚠️ Anthropic client non initialisé (clé API manquante ?)")
            return None
        
        try:
            response = self.anthropic_client.messages.create(
                model=self.anthropic_model,
                max_tokens=max_tokens,
                temperature=0.3,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": user_message}
                ]
            )
            # Extraire le texte de la réponse
            text = ""
            for block in response.content:
                if hasattr(block, 'text'):
                    text += block.text
                elif isinstance(block, dict) and 'text' in block:
                    text += block['text']
            return text.strip() if text.strip() else None
        
        except anthropic.APIError as e:
            print(f"⚠️ Erreur API Anthropic: {e}")
            return None
        except anthropic.RateLimitError as e:
            print(f"⚠️ Rate limit Anthropic: {e}")
            return None
        except Exception as e:
            print(f"⚠️ Erreur Anthropic: {e}")
            return None

    # ========================================================================
    # GÉNÉRATION DE RÉPONSES (chat)
    # ========================================================================
    
    def generate_response(self, question, class_level, chapter):
        """Génère une réponse pédagogique via Claude + RAG."""
        try:
            context = ""
            sources = []
            
            try:
                nodes = self.query(question, class_level, chapter)
                if nodes:
                    context = "\n".join([node.get_content()[:500] for node in nodes])
                    sources = [node.metadata for node in nodes]
            except Exception as e:
                print(f"RAG retrieval failed: {e}")
            
            # Essayer Claude d'abord
            answer = self._generate_with_claude(question, context, class_level, chapter)
            
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
    
    def _generate_with_claude(self, question, context, class_level, chapter):
        """Utilise Claude pour générer une réponse pédagogique de qualité."""
       
        system_prompt = """Tu es un professeur de mathématiques au Burkina Faso, expert du programme officiel burkinabè.

RÈGLES À SUIVRE ABSOLUMENT :
1. Réponds UNIQUEMENT à la question posée par l'élève
2. Base-toi sur le contexte fourni (documents officiels)
3. Adapte ton langage au niveau de la classe (6ème=simple, Terminale=avancé)
4. Explique les concepts étape par étape
5. Donne toujours un exemple concret adapté au Burkina Faso
6. Utilise un ton encourageant et bienveillant
7. Cite les formules mathématiques clairement
8. Si le contexte ne contient pas la réponse, explique ce que tu sais sur le sujet
9. NE DIS PAS que tu ne peux pas répondre - utilise tes connaissances en maths
10. Inclus le **formatage Markdown** pour la lisibilité (gras pour les concepts clés)

Ton objectif : que l'élève comprenne et progresse !"""
        
        context_text = context if context else "Aucun document spécifique disponible pour ce chapitre."
        user_message = f"""Contexte documentaire (programme Burkina Faso):
{context_text}

Chapitre: {chapter}
Classe: {class_level}

Question de l'élève: {question}

Réponds de façon claire et pédagogique:"""
        
        response = self._call_claude(system_prompt, user_message, max_tokens=1200)
        if response:
            return response
        
        # Fallback si Claude indisponible
        print("⚠️ Claude indisponible, utilisation du fallback local...")
        return self._generate_local_response(question, class_level, chapter, context)
    
    # ========================================================================
    # SIMPLIFICATION
    # ========================================================================
    
    def simplify_answer(self, question: str, original_answer: str, class_level: str) -> str:
        """Utilise Claude pour simplifier une réponse."""
        
        system_prompt = """Tu es professeur de maths au Burkina Faso. Tu dois RÉEXPLIQUER simplement.

RÈGLES :
- L'élève n'a PAS compris la première explication
- Utilise des mots TRÈS SIMPLES, comme si tu parlais à un élève de 10-12 ans
- Donne un exemple concret du quotidien au Burkina Faso
- Sois encourageant : "Ce n'est pas grave, je vais t'expliquer autrement"
- Évite le jargon technique, simplifie les formules
- Structure en étapes claires et courtes"""

        user_message = f"""Niveau de l'élève: {class_level}

Question initiale: {question}

Explication à simplifier:
{original_answer[:1500]}

Réécris cette explication de façon beaucoup plus simple:"""
        
        response = self._call_claude(system_prompt, user_message, max_tokens=800)
        if response:
            return response
        
        # Fallback
        return self._local_simplify(question, original_answer, class_level)
    
    # ========================================================================
    # GÉNÉRATION D'EXERCICES
    # ========================================================================
    
    def generate_exercise(self, class_level, chapter):
        """Génère un exercice via Claude."""
        
        system_prompt = """Tu es professeur de mathématiques au Burkina Faso. Génère un EXERCICE.

RÈGLES :
- Contexte réaliste du Burkina Faso (marché, agriculture, élevage, construction, tissage...)
- Adapté au niveau de la classe
- Inclus ÉNONCÉ + SOLUTION DÉTAILLÉE étape par étape
- Encourage l'élève à essayer par lui-même
- Termine par la réponse finale claire
- Format Markdown"""

        user_message = f"""Classe: {class_level}
Chapitre: {chapter}

Génère un exercice original et intéressant sur ce chapitre pour cette classe:"""
        
        response = self._call_claude(system_prompt, user_message, max_tokens=1200)
        if response:
            return {
                "exercise": response,
                "chapter": chapter,
                "class_level": class_level
            }
        
        # Fallback local
        print("⚠️ Claude indisponible pour l'exercice, utilisation du fallback...")
        return self._local_generate_exercise(class_level, chapter)

    # ========================================================================
    # FALLBACKS LOCAUX (quand Claude est indisponible)
    # ========================================================================
    
    def _generate_local_response(self, question, class_level, chapter, context):
        """Fallback local pour les réponses."""
        # Détection du thème
        chapter_lower = chapter.lower()
        question_lower = question.lower()
        
        knowledge = self._get_knowledge(chapter_lower, question_lower, question, class_level, chapter)
        
        if knowledge:
            if context and context != "Aucun document spécifique disponible pour ce chapitre.":
                knowledge += f"\n\n**Extrait des documents :**\n{context[:500]}"
            return knowledge
        
        # Réponse générique
        if context and context != "Aucun document spécifique disponible pour ce chapitre.":
            return f"""
**Question :** {question}

Voici les informations disponibles sur le chapitre "{chapter}" de {class_level}.

**Documents :**
{context[:800]}

*Conseil : Pour approfondir, consulte ton manuel ou demande à ton professeur.*
"""
        return f"""
**Question :** {question}

Le chapitre "{chapter}" fait partie du programme de {class_level} au Burkina Faso.

**Pour t'aider :**
1. Relis les définitions dans ton cours
2. Fais des exercices d'application simples
3. Augmente progressivement la difficulté

*Je peux te donner des explications plus précises si tu reformules ta question.*
"""
    
    def _get_knowledge(self, chapter_lower, question_lower, question, class_level, chapter):
        """Retourne le contenu de connaissance si le thème est détecté."""
        knowledge_base = {
            "pythagore": f"""
**Question :** {question}

Le **théorème de Pythagore** est une propriété fondamentale des triangles rectangles.

**Énoncé :** Dans un triangle rectangle, le carré de l'hypoténuse est égal à la somme des carrés des deux autres côtés.

**Formule :** Si ABC est rectangle en A, alors BC² = AB² + AC²
- BC = hypoténuse (côté le plus long)
- AB et AC = cathètes (côtés de l'angle droit)

**Exemple :** AB = 3 cm, AC = 4 cm → BC = 5 cm

**Quand l'utiliser ?** Pour calculer un côté manquant dans un triangle rectangle.
""",
            "thalès": f"""
**Question :** {question}

Le **théorème de Thalès** permet de calculer des longueurs avec des parallèles.

**Énoncé :** Si deux droites parallèles coupent deux sécantes, alors les segments sont proportionnels.

**Formule :** AD/AB = AE/AC = DE/BC

**Exemple :** Si AD=2cm, AB=6cm, DE=3cm → BC = (6×3)/2 = 9cm
""",
            "fraction": f"""
**Question :** {question}

Une **fraction** a/b : a = numérateur, b = dénominateur.

**Opérations :**
- Addition : a/b + c/b = (a+c)/b
- Multiplication : (a/b) × (c/d) = (a×c)/(b×d)
- Division : (a/b) ÷ (c/d) = (a×d)/(b×c)

**Simplification :** Divise numérateur et dénominateur par leur PGCD.
""",
            "équation": f"""
**Question :** {question}

**Équation du 1er degré :** ax + b = 0

**Résolution :** 1) Isoler x → 2) Diviser

**Exemple :** 3x + 7 = 22 → 3x = 15 → x = 5

**Vérification :** 3×5 + 7 = 22 ✅
""",
            "trigonométrie": f"""
**Question :** {question}

**SOH-CAH-TOA :**
- sin(Â) = opposé/hypoténuse
- cos(Â) = adjacent/hypoténuse
- tan(Â) = opposé/adjacent

**Exemple :** cos(60°) = 0,5 ; sin(30°) = 0,5
""",
            "sphère": f"""
**Question :** {question}

**Formules :**
- Aire de la sphère : A = 4πR²
- Volume de la boule : V = (4/3)πR³

**Exemple :** Pour R = 3 cm : Volume = 36π ≈ 113 cm³
""",
            "fonction": f"""
**Question :** {question}

Fonction f : x → f(x). **Affine :** f(x) = ax + b

**Exemple :** f(x) = 2x + 3 → f(1) = 5, f(-2) = -1
""",
            "dériv": f"""
**Question :** {question}

**Dérivée :** (xⁿ)' = n × xⁿ⁻¹

**Exemple :** f(x)=3x²+2x-5 → f'(x)=6x+2

**Interprétation :** f'(a) = pente de la tangente en x=a
""",
            "statistique": f"""
**Question :** {question}

**Moyenne =** somme/effectif
**Médiane =** valeur centrale
**Étendue =** max - min

**Exemple :** {2,5,5,7,9} → moyenne=5,6 médiane=5
""",
            "probabilité": f"""
**Question :** {question}

**P =** cas favorables / cas possibles

**Propriétés :** 0 ≤ P ≤ 1

**Exemple :** P(6 avec un dé) = 1/6 ≈ 0,167
""",
            "suite": f"""
**Question :** {question}

**Arithmétique :** uₙ = u₁ + (n-1)r (on ajoute r)
**Géométrique :** uₙ = u₁ × qⁿ⁻¹ (on multiplie par q)
""",
            "vecteur": f"""
**Question :** {question}

**AB→ = (xB-xA, yB-yA)**
**Addition :** AB→ + BC→ = AC→ (Chasles)
""",
            "racine": f"""
**Question :** {question}

√a = b si b² = a

**Exemple :** √25 = 5, √144 = 12

**Propriétés :** √(a×b) = √a × √b
""",
            "identité": f"""
**Question :** {question}

1. (a+b)² = a²+2ab+b²
2. (a-b)² = a²-2ab+b²
3. (a+b)(a-b) = a²-b²
""",
            "second degré": f"""
**Question :** {question}

**Δ = b²-4ac**
- Δ>0 : 2 solutions x = (-b±√Δ)/(2a)
- Δ=0 : 1 solution x = -b/(2a)
- Δ<0 : pas de solution
""",
            "exponentielle": f"""
**Question :** {question}

**eˣ :** e⁰=1, eˣ>0
**(eˣ)' = eˣ**
**ln(x) :** ln(eˣ)=x, e^(ln x)=x
""",
            "intégration": f"""
**Question :** {question}

**∫ f(x) dx** de a à b = aire sous la courbe

Si F'(x)=f(x), alors ∫f(x)dx = F(b)-F(a)
""",
            "complexe": f"""
**Question :** {question}

z = a+ib (i²=-1)
|z| = √(a²+b²) = module
""",
            "limite": f"""
**Question :** {question}

lim 1/x (x→∞) = 0
lim x² (x→∞) = ∞
Asymptote : droite approchée par la courbe
"""
        }
        
        for key, value in knowledge_base.items():
            if key in chapter_lower or key in question_lower:
                return value
        return None

    def _local_simplify(self, question: str, original_answer: str, class_level: str) -> str:
        """Fallback simplification locale."""
        answer_lower = original_answer.lower()
        
        simplifications = {
            "pythagore": f"""
👋 **Je te résume simplement :**

Le théorème de Pythagore dit que dans un triangle rectangle, le côté le plus long au carré est égal à la somme des carrés des deux autres côtés.

**Formule :** BC² = AB² + AC²

**Exemple :** Si les petits côtés font 3 et 4 cm, le grand fait 5 cm (3²+4²=25, √25=5)

**À retenir :** On l'utilise pour calculer un côté quand on connaît les deux autres.
""",
            "thalès": f"""
👋 **Je te résume simplement :**

Le théorème de Thalès sert à calculer des longueurs quand on a des parallèles.

**Principe :** Les segments sont proportionnels.

**Formule :** AD/AB = AE/AC = DE/BC

**À retenir :** Cherche des droites parallèles et pose les rapports égaux.
""",
            "fraction": f"""
👋 **Je te résume simplement :**

Une fraction a/b = a parts sur b parts.

**Pour additionner :** Il faut le même dénominateur en bas.
Ex : 1/4 + 2/4 = 3/4 (on ajoute seulement les chiffres du haut)

**Pour simplifier :** Divise le haut et le bas par le même nombre.
Ex : 4/8 = 1/2
""",
            "équation": f"""
👋 **Je te résume simplement :**

Une équation, c'est comme une balance : égal des deux côtés.

**Méthode :**
1. Regroupe les x d'un côté
2. Regroupe les nombres de l'autre
3. Divise pour trouver x

**Exemple :** 2x + 3 = 7 → 2x = 4 → x = 2 ✅
""",
            "fonction": f"""
👋 **Je te résume simplement :**

Une fonction f(x), c'est une machine : tu mets x, tu obtiens f(x).

**Exemple :** f(x) = 2x + 3 → f(1) = 5, f(5) = 13

**Graphiquement :** c'est une droite ou une courbe.
""",
            "dériv": f"""
👋 **Je te résume simplement :**

La dérivée mesure la vitesse de changement d'une fonction.

**Exemples :**
- f(x) = 3x → f'(x) = 3 (pente constante)
- f(x) = x² → f'(x) = 2x (pente qui augmente)

**Formule :** (xⁿ)' = n × xⁿ⁻¹
"""
        }
        
        for key, value in simplifications.items():
            if key in answer_lower:
                return value
        
        # Simplification générique
        key_points = []
        for line in original_answer.split('\n'):
            line = line.strip()
            if line and len(line) > 20 and not line.startswith('**') and not line.startswith('#'):
                line = line.replace('**', '').replace('*', '')
                key_points.append(line)
        
        text = '\n'.join(key_points[:4]) if key_points else original_answer[:300]
        return f"""
👋 **Pas de panique ! Je t'explique autrement :**

{text}

**Conseil :** En {class_level}, il faut apprendre les formules par cœur et faire beaucoup d'exercices.
"""

    def _local_generate_exercise(self, class_level, chapter):
        """Fallback exercice local."""
        chapter_lower = chapter.lower()
        
        exercises = {
            "pythagore": f"""
**📐 Exercice - {class_level} - Théorème de Pythagore**

**Énoncé :**
Un menuisier burkinabè vérifie une planche : côtés 30 cm, 40 cm, et 50 cm.
A-t-elle un angle droit ?

**Solution :**
1. Le plus long côté (50) est l'hypoténuse potentielle
2. 50² = 2500 ; 30²+40² = 900+1600 = 2500
3. 2500 = 2500 ✅

**✅ Réponse :** Oui, l'angle est parfaitement droit !
""",
            "thalès": f"""
**📐 Exercice - {class_level} - Théorème de Thalès**

**Énoncé :**
Au marché de Ouaga, un poteau de 3 m est à 2 m du mur.
Un second poteau est à 6 m. Quelle est sa hauteur ?

**Solution :**
3/2 = h/6 → h = 3×6/2 = 9 m

**✅ Réponse :** 9 mètres
""",
            "fraction": f"""
**📝 Exercice - {class_level} - Fractions**

**Énoncé :**
Au marché, Mamadi achète 3/4 kg de riz et 2/3 kg de haricots.
Masse totale ?

**Solution :**
3/4 + 2/3 = 9/12 + 8/12 = 17/12 ≈ 1,42 kg

**✅ Réponse :** 17/12 kg
""",
            "équation": f"""
**📝 Exercice - {class_level} - Équations**

**Énoncé :**
3 ananas + 500 F = 2 ananas + 1500 F. Prix d'un ananas ?

**Solution :**
3x + 500 = 2x + 1500 → x = 1000

**✅ Réponse :** 1000 F CFA
""",
            "trigonométrie": f"""
**📐 Exercice - {class_level} - Trigonométrie**

**Énoncé :**
Arbre avec ombre de 12 m. Soleil à 60°. Hauteur ?

**Solution :**
tan(60°) = h/12 → h = 12×1,732 ≈ 20,8 m

**✅ Réponse :** ≈ 20,8 mètres
""",
            "puissance": f"""
**📝 Exercice - {class_level} - Puissances**

**Énoncé :**
5 rangées de 5 arbres, chaque arbre donne 5 fruits.
Combien de fruits ?

**Solution :**
5³ = 5×5×5 = 125 fruits

**✅ Réponse :** 125 fruits
""",
            "fonction": f"""
**📝 Exercice - {class_level} - Fonctions**

**Énoncé :**
Vendeur de dolo : 200 F/litre + 1000 F fixe/jour.
Gain pour x litres ?

**Solution :**
f(x) = 200x + 1000

Ex: f(5) = 2000 F, f(10) = 3000 F
""",
            "statistique": f"""
**📊 Exercice - {class_level} - Statistiques**

**Énoncé :**
Notes : 12, 8, 15, 10, 14, 6, 18, 11, 13, 9
Moyenne, médiane, étendue ?

**Solution :**
Moyenne = 116/10 = 11,6
Médiane = 11,5
Étendue = 12
""",
            "probabilité": f"""
**🎲 Exercice - {class_level} - Probabilités**

**Énoncé :**
3 billes rouges + 5 bleues. P(rouge) ?

**Solution :**
P = 3/8 = 0,375 = 37,5%

**✅ Réponse :** 37,5% de chance
""",
            "vecteur": f"""
**📐 Exercice - {class_level} - Vecteurs**

**Énoncé :**
A(1,2) → B(4,6) → C(7,5). Vecteur total ?

**Solution :**
AB→=(3,4), BC→=(3,-1), AC→=(6,3)

**✅ Réponse :** (6, 3)
""",
            "racine": f"""
**📝 Exercice - {class_level} - Racines carrées**

**Énoncé :**
Champ carré de 144 m². Longueur du côté ?

**Solution :**
c = √144 = 12 m

**✅ Réponse :** 12 mètres
""",
            "dériv": f"""
**📝 Exercice - {class_level} - Dérivation**

**Énoncé :**
f(x) = 3x² + 2x - 5. Calcule f'(x).

**Solution :**
f'(x) = 6x + 2

**✅ Réponse :** f'(x) = 6x + 2
""",
            "suite": f"""
**📝 Exercice - {class_level} - Suites**

**Énoncé :**
50 arbres la 1ʳᵉ année, +30 chaque année.
Arbres la 5ᵉ année ?

**Solution :**
u₅ = 50 + 4×30 = 170

**✅ Réponse :** 170 arbres
"""
        }
        
        for key, value in exercises.items():
            if key in chapter_lower:
                return {
                    "exercise": value,
                    "chapter": chapter,
                    "class_level": class_level
                }
        
        return {
            "exercise": f"""
**📝 Exercice - {class_level} - {chapter}**

Entraîne-toi sur le chapitre "{chapter}" :
1. Relis ton cours
2. Identifie les formules importantes
3. Applique-les étape par étape
4. Vérifie tes résultats

*Tu peux aussi me poser une question précise sur ce chapitre !*
""",
            "chapter": chapter,
            "class_level": class_level
        }