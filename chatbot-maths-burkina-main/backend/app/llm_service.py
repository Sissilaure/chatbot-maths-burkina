"""Service de génération de réponses (LLM local + fallback web search)"""

import json
import re
from typing import List, Dict, Optional
from pathlib import Path

import httpx

from .config import USE_WEB_SEARCH


class LLMService:
    """
    Service de génération de réponses pédagogiques.
    
    Utilise un LLM local (gratuit) ou une API gratuite.
    Stratégie:
    1. Rechercher dans la base documentaire (RAG)
    2. Si pas de réponse fiable → recherche web
    3. Si toujours pas → réponse indiquant les limites
    """

    def __init__(self):
        # Par défaut, on utilise un prompt structuré
        # et un LLM via HuggingFace Inference API (gratuit sans clé pour modèles publics)
        self.api_url = "https://api-inference.huggingface.co/models/HuggingFaceH4/zephyr-7b-beta"
        self.headers = {}  # Pas de clé nécessaire pour les modèles publics
        
        # Fallback: API gratuite de Mistral (très bon en français)
        self.fallback_api_url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.2"
        
        self.use_api = True  # True = API distante, False = modèle local (si installé)

    def generate_response(self, 
                          question: str, 
                          context_chunks: List[Dict],
                          classe: str,
                          chapitre: str) -> Dict:
        """
        Génère une réponse pédagogique à partir du contexte.
        
        Args:
            question: La question de l'utilisateur
            context_chunks: Les chunks pertinents de la base documentaire
            classe: La classe sélectionnée
            chapitre: Le chapitre sélectionné
            
        Returns:
            Dict avec réponse, sources, et métadonnées
        """
        
        # Construire le contexte à partir des chunks
        context_text = self._build_context(context_chunks)
        
        # Vérifier si on a un contexte suffisant
        has_sufficient_context = len(context_chunks) >= 2 and any(
            c["score"] > 0.5 for c in context_chunks
        )
        
        if not has_sufficient_context and context_text.strip():
            # Contexte faible mais existant - on essaie quand même
            pass
        elif not context_text.strip():
            # Pas de contexte du tout → recherche web
            return self._handle_no_context(question, classe, chapitre)
        
        # Construire le prompt
        prompt = self._build_prompt(question, context_text, classe, chapitre)
        
        # Générer la réponse
        response_text = self._call_llm(prompt)
        
        if response_text is None:
            # Si le LLM a échoué, essayer la recherche web
            return self._handle_no_context(question, classe, chapitre)
        
        # Formater la réponse
        return self._format_response(response_text, context_chunks)

    def _build_context(self, chunks: List[Dict]) -> str:
        """Construit le texte de contexte à partir des chunks."""
        if not chunks:
            return ""
        
        context_parts = []
        for i, chunk in enumerate(chunks):
            source = chunk["metadata"].get("filename", "source inconnue")
            context_parts.append(f"[Document {i+1}: {source}]\n{chunk['text']}")
        
        return "\n\n".join(context_parts)

    def _build_prompt(self, question: str, context: str, classe: str, chapitre: str) -> str:
        """Construit le prompt pour le LLM."""
        
        prompt = f"""Tu es un professeur de mathématiques au Burkina Faso. Tu aides un élève de {classe} sur le chapitre "{chapitre}".

RÈGLES IMPORTANTES:
1. Réponds UNIQUEMENT à partir des documents fournis ci-dessous
2. Si les documents ne contiennent pas la réponse, dis-le clairement
3. Adapte ton langage au niveau {classe}
4. Explique les étapes une par une
5. Cite la source de ta réponse (manuel, page)
6. Si c'est un exercice, détaille la résolution étape par étape
7. Utilise des exemples concrets adaptés au Burkina Faso

CONTEXTE (documents officiels du programme burkinabè):
{context}

QUESTION DE L'ÉLÈVE:
{question}

RÉPONSE PÉDAGOGIQUE:"""

        return prompt

    def _call_llm(self, prompt: str, max_retries: int = 2) -> Optional[str]:
        """Appelle le LLM via API."""
        
        if not self.use_api:
            return self._call_local_llm(prompt)
        
        for attempt in range(max_retries):
            try:
                response = httpx.post(
                    self.api_url,
                    json={
                        "inputs": prompt,
                        "parameters": {
                            "max_new_tokens": 1024,
                            "temperature": 0.3,
                            "do_sample": True,
                            "top_p": 0.95,
                            "return_full_text": False
                        },
                        "options": {"wait_for_model": True}
                    },
                    headers=self.headers,
                    timeout=60.0
                )
                
                if response.status_code == 200:
                    result = response.json()
                    if isinstance(result, list) and len(result) > 0:
                        return result[0].get("generated_text", "")
                    elif isinstance(result, dict):
                        return result.get("generated_text", "")
                    return str(result)
                elif response.status_code == 503:
                    print(f"Modèle en chargement, tentative {attempt+1}...")
                    continue
                else:
                    print(f"Erreur API: {response.status_code}")
                    
                    # Tentative avec l'API fallback
                    if attempt == max_retries - 1:
                        response = httpx.post(
                            self.fallback_api_url,
                            json={
                                "inputs": prompt,
                                "parameters": {
                                    "max_new_tokens": 1024,
                                    "temperature": 0.3
                                },
                                "options": {"wait_for_model": True}
                            },
                            timeout=60.0
                        )
                        if response.status_code == 200:
                            result = response.json()
                            if isinstance(result, list) and len(result) > 0:
                                return result[0].get("generated_text", "")
                    
            except httpx.TimeoutException:
                print(f"Timeout, tentative {attempt+1}...")
                continue
            except Exception as e:
                print(f"Erreur LLM: {e}")
                continue
        
        return None

    def _call_local_llm(self, prompt: str) -> Optional[str]:
        """Appelle un modèle local (si installé)."""
        try:
            # Essayer d'utiliser un modèle local avec transformers
            from transformers import pipeline
            
            generator = pipeline(
                "text-generation",
                model="microsoft/phi-2",
                device=-1  # CPU
            )
            
            result = generator(
                prompt,
                max_length=1024,
                temperature=0.3,
                do_sample=True
            )
            
            return result[0]["generated_text"]
            
        except ImportError:
            print("transformers non installé, impossible d'utiliser le mode local")
            return None
        except Exception as e:
            print(f"Erreur modèle local: {e}")
            return None

    def _handle_no_context(self, question: str, classe: str, chapitre: str) -> Dict:
        """Gère le cas où aucun contexte n'est disponible."""
        
        if USE_WEB_SEARCH:
            # Tenter une recherche web
            web_results = self._web_search(f"mathématiques {classe} {chapitre} {question}")
            
            if web_results:
                # Générer une réponse à partir des résultats web
                prompt = self._build_prompt(question, web_results, classe, chapitre)
                response_text = self._call_llm(prompt)
                
                if response_text:
                    return self._format_response(
                        response_text + "\n\n---\n⚠️ **Source**: Recherche internet (non vérifiée par le programme officiel)",
                        [],
                        source_type="web"
                    )
        
        return {
            "reponse": (
                f"😔 Désolé, je n'ai pas trouvé de réponse fiable dans ma base documentaire "
                f"pour ta question sur le chapitre « {chapitre} » de {classe}.\n\n"
                f"**Suggestions:**\n"
                f"1. Reformule ta question différemment\n"
                f"2. Vérifie que tu as bien sélectionné la bonne classe et le bon chapitre\n"
                f"3. Consulte ton manuel scolaire ou demande à ton professeur\n\n"
                f"*Je ne donne que des réponses vérifiées par rapport aux programmes officiels "
                f"du Burkina Faso pour éviter les erreurs.*"
            ),
            "sources": [],
            "statut": "non_trouve"
        }

    def _web_search(self, query: str) -> Optional[str]:
        """Effectue une recherche web simple."""
        try:
            # Utilisation de DuckDuckGo (gratuit, sans clé API)
            from bs4 import BeautifulSoup
            from urllib.parse import quote_plus
            
            encoded_query = quote_plus(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"
            
            response = httpx.get(url, timeout=10.0, follow_redirects=True)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                results = soup.find_all('a', class_='result__a', limit=3)
                
                web_texts = []
                for result in results:
                    link = result.get('href', '')
                    if link:
                        web_texts.append(f"Résultat web: {result.get_text()}")
                
                return "\n".join(web_texts) if web_texts else None
            
            return None
            
        except Exception as e:
            print(f"Erreur recherche web: {e}")
            return None

    def _format_response(self, response_text: str, chunks: List[Dict], 
                         source_type: str = "documentaire") -> Dict:
        """Formate la réponse avec les sources."""
        
        # Extraire les sources des chunks
        sources = []
        seen_sources = set()
        for chunk in chunks:
            source = chunk["metadata"].get("filename", "source inconnue")
            classe = chunk["metadata"].get("classe", "")
            chapitre = chunk["metadata"].get("chapitre", "")
            source_key = f"{source}_{classe}_{chapitre}"
            
            if source_key not in seen_sources:
                sources.append({
                    "fichier": source,
                    "classe": classe,
                    "chapitre": chapitre,
                    "score": round(chunk.get("score", 0), 3)
                })
                seen_sources.add(source_key)
        
        return {
            "reponse": response_text.strip(),
            "sources": sources,
            "statut": source_type
        }

    def generate_exercise(self, classe: str, chapitre: str, difficulty: str = "moyen") -> Dict:
        """Génère un exercice d'entraînement."""
        
        prompt = f"""Génère UN EXERCICE de mathématiques pour un élève de {classe} au Burkina Faso sur le chapitre "{chapitre}".

L'exercice doit être:
- Niveau {difficulty}
- Adapté au programme burkinabè
- Avec un contexte réaliste (prix au marché, agriculture, etc.)
- Suivi de la solution détaillée

Format:
EXERCICE: [énoncé]
SOLUTION: [solution détaillée étape par étape]"""

        response_text = self._call_llm(prompt)
        
        if response_text:
            return {
                "statut": "succès",
                "exercice": response_text
            }
        
        return {
            "statut": "erreur",
            "exercice": "Impossible de générer un exercice pour le moment."
        }

    def simplify_response(self, question: str, previous_response: str) -> Dict:
        """Reformule une réponse de façon plus simple."""
        
        prompt = f"""Reformule la réponse suivante de façon PLUS SIMPLE, comme si tu expliquais à un élève qui n'a pas compris:

MESSAGE ORIGINAL:
{previous_response}

QUESTION INITIALE:
{question}

EXPLICATION SIMPLIFIÉE:"""

        response_text = self._call_llm(prompt)
        
        if response_text:
            return {
                "statut": "succès",
                "reponse": response_text.strip()
            }
        
        return {
            "statut": "erreur",
            "reponse": "Désolé, je n'ai pas pu simplifier davantage. Consulte ton professeur."
        }