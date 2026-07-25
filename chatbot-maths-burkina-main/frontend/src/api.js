const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"

async function handleJson(res, fallbackMessage) {
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || fallbackMessage || `Erreur ${res.status}`)
  }
  return res.json()
}

function authHeaders(token) {
  return { "Content-Type": "application/json", Authorization: `Bearer ${token}` }
}

export async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`)
    return await res.json()
  } catch {
    return { status: "error" }
  }
}

export async function getClasses() {
  const res = await fetch(`${API_BASE}/api/classes`)
  const data = await handleJson(res, "Erreur chargement des classes")
  return data.classes // [{ code, name }]
}

export async function getChapters(classCode) {
  const res = await fetch(`${API_BASE}/api/classes/${encodeURIComponent(classCode)}/chapters`)
  const data = await handleJson(res, "Erreur chargement des chapitres")
  return data.chapters
}

/**
 * Pose une question au chatbot.
 * @param {string} question
 * @param {string} classCode
 * @param {string} chapter
 * @param {Array<{role: 'user'|'assistant', content: string}>} history - derniers échanges pour la mémoire de conversation
 */
export async function askQuestion(question, classCode, chapter, history = []) {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      question,
      class_level: classCode,
      chapter,
      history,
    }),
  })
  const data = await handleJson(res, "Erreur lors de la génération de la réponse")
  return {
    answer: data.answer,
    fromRag: data.from_rag,
    sources: mapSources(data.sources, classCode, chapter),
  }
}

/** Nettoie un nom de fichier brut (ex: "Chapitre_3_Vecteurs_du_plan.pdf") en un titre lisible
 * ("Vecteurs du plan"), pour les cas où le chapitre n'est pas renseigné dans les métadonnées. */
function cleanFileTitle(rawPath) {
  if (!rawPath) return ""
  const base = rawPath.split(/[\\/]/).pop() || rawPath
  return base
    .replace(/\.[a-zA-Z0-9]+$/, "")
    .replace(/^chapitre[_\-\s]*\d+[_\-\s]*/i, "")
    .replace(/^chap[_\-\s]*\d+[_\-\s]*/i, "")
    .replace(/[_\-]+/g, " ")
    .replace(/\s+/g, " ")
    .trim()
}

/** Convertit les métadonnées brutes des chunks récupérés en une liste de sources lisible et
 * dédupliquée (plusieurs chunks proviennent souvent du même document) : jamais de chemin de
 * fichier brut affiché à l'élève. */
function mapSources(sources, classCode, chapter) {
  const seen = new Set()
  const result = []
  for (const s of sources || []) {
    const classe = s.class || classCode
    const chapitre = s.chapter || chapter || cleanFileTitle(s.source)
    if (!classe && !chapitre) continue
    const key = `${classe}|${chapitre}`
    if (seen.has(key)) continue
    seen.add(key)
    result.push({ classe, chapitre })
  }
  return result
}

/**
 * Pose une question au chatbot en streaming (Server-Sent Events) : la réponse arrive
 * fragment par fragment plutôt qu'en un seul bloc à la fin.
 * @param {string} question
 * @param {string} classCode
 * @param {string} chapter
 * @param {Array<{role: 'user'|'assistant', content: string}>} history
 * @param {{onDelta?: (text: string) => void, onDone?: (result: {sources: object[], fromRag: boolean}) => void, onError?: (message: string) => void}} callbacks
 */
export async function askQuestionStream(question, classCode, chapter, history = [], { onDelta, onDone, onError } = {}) {
  try {
    const res = await fetch(`${API_BASE}/api/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        question,
        class_level: classCode,
        chapter,
        history,
      }),
    })

    if (!res.ok || !res.body) {
      const err = await res.json().catch(() => ({}))
      throw new Error(err.detail || `Erreur ${res.status}`)
    }

    const reader = res.body.getReader()
    const decoder = new TextDecoder("utf-8")
    let buffer = ""
    let sources = []
    let fromRag = false
    let streamError = null

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      const events = buffer.split("\n\n")
      buffer = events.pop() ?? ""

      for (const raw of events) {
        const line = raw.trim()
        if (!line.startsWith("data:")) continue
        const jsonStr = line.slice(5).trim()
        if (!jsonStr) continue

        let evt
        try {
          evt = JSON.parse(jsonStr)
        } catch {
          continue
        }

        if (evt.error) {
          streamError = evt.error
        } else if (typeof evt.delta === "string") {
          onDelta?.(evt.delta)
        } else if (evt.done) {
          sources = evt.sources || []
          fromRag = Boolean(evt.from_rag)
        }
      }
    }

    if (streamError) throw new Error(streamError)

    onDone?.({ sources: mapSources(sources, classCode, chapter), fromRag })
  } catch (err) {
    onError?.(err.message || "Erreur pendant la génération de la réponse")
  }
}

export async function simplifyResponse(question, previousResponse, classCode, chapter) {
  const res = await fetch(`${API_BASE}/api/simplify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      answer: previousResponse,
      class_level: classCode,
      question,
      chapter,
    }),
  })
  const data = await handleJson(res, "Erreur lors de la simplification")
  return data.simplified_answer
}

/**
 * Génère un exercice structuré : { enonce, indices[], solution, reponse_finale, chapter, difficulty, qcm? }
 * @param {string} classCode
 * @param {string} chapter - facultatif : si vide, le serveur choisit un chapitre pertinent
 *   (à partir de `history`, ou un chapitre de base sinon) et le renvoie dans la réponse.
 * @param {number|null} difficulty - 1 à 4 étoiles (1 = QCM d'application directe, 4 = situation
 *   d'intégration), ou null pour laisser le serveur déduire un niveau adapté.
 * @param {Array<{role: 'user'|'assistant', content: string}>} history
 */
export async function generateExercise(classCode, chapter, difficulty = null, history = []) {
  const res = await fetch(`${API_BASE}/api/exercise`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ class_level: classCode, chapter, difficulty, history }),
  })
  return handleJson(res, "Erreur lors de la génération de l'exercice")
}

/**
 * Envoie la photo d'un exercice (papier, manuscrit ou imprimé) et récupère l'explication +
 * la correction. `classCode`/`chapter`/`prompt` sont facultatifs et passés en query string :
 * l'appel est un multipart/form-data (fichier image), pas un JSON. `prompt` est la consigne
 * tapée par l'élève en même temps que sa photo (ex: "vérifie juste la question 2").
 * `history` (facultatif) : renvoyer la MÊME photo avec les échanges déjà tenus à son sujet,
 * pour les questions de suivi (ex: "résous la question a") — voir App.jsx::activePhoto.
 * Envoyé en champ de formulaire (pas en query string, qui a une limite de taille).
 */
export async function explainExercisePhoto(file, classCode = "", chapter = "", prompt = "", history = []) {
  const params = new URLSearchParams()
  if (classCode) params.set("class_level", classCode)
  if (chapter) params.set("chapter", chapter)
  if (prompt) params.set("prompt", prompt)

  const formData = new FormData()
  formData.append("file", file)
  if (history.length > 0) formData.append("history", JSON.stringify(history))

  const res = await fetch(`${API_BASE}/api/exercise/photo?${params.toString()}`, {
    method: "POST",
    body: formData,
  })
  const data = await handleJson(res, "Erreur lors de l'analyse de la photo")
  return data.answer
}

/**
 * QCM diagnostique de remédiation (8 questions) sur le chapitre choisi.
 */
export async function generateRemediation(classCode, chapter, history = []) {
  const res = await fetch(`${API_BASE}/api/remediation`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ class_level: classCode, chapter, history }),
  })
  return handleJson(res, "Erreur lors de la génération du QCM de remédiation")
}

/**
 * URL du document de cours (PDF/DOCX/TXT) fourni pour ce chapitre, à ouvrir directement
 * (pas de fetch ici : voir checkCourseAvailable pour vérifier sa disponibilité avant ouverture).
 */
export function getCourseFileUrl(classCode, chapter) {
  return `${API_BASE}/api/course/${encodeURIComponent(classCode)}/${encodeURIComponent(chapter)}`
}

/**
 * Vérifie que le document de cours existe avant d'ouvrir un nouvel onglet dessus.
 */
export async function checkCourseAvailable(classCode, chapter) {
  try {
    const res = await fetch(getCourseFileUrl(classCode, chapter), { method: "HEAD" })
    return res.ok
  } catch {
    return false
  }
}

/**
 * Résumé des points essentiels : de la séance en cours si des échanges existent,
 * sinon du chapitre choisi.
 */
export async function getSummary(history, classCode, chapter) {
  const res = await fetch(`${API_BASE}/api/summary`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ history, class_level: classCode, chapter }),
  })
  const data = await handleJson(res, "Erreur lors de la génération du résumé")
  return data.content
}

// ---------------------------------------------------------------------------
// Comptes élèves (auth optionnelle) : inscription/connexion, historique, accueil
// ---------------------------------------------------------------------------

export async function registerAccount(username, password) {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  })
  return handleJson(res, "Erreur lors de l'inscription")
}

export async function loginAccount(username, password) {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  })
  return handleJson(res, "Erreur lors de la connexion")
}

export async function getMe(token) {
  const res = await fetch(`${API_BASE}/api/auth/me`, { headers: authHeaders(token) })
  return handleJson(res, "Session invalide")
}

export async function listConversations(token) {
  const res = await fetch(`${API_BASE}/api/conversations`, { headers: authHeaders(token) })
  const data = await handleJson(res, "Erreur chargement de l'historique")
  return data.conversations
}

export async function createConversation(token, classCode, chapter) {
  const res = await fetch(`${API_BASE}/api/conversations`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({ class_level: classCode, chapter }),
  })
  const data = await handleJson(res, "Erreur création de la conversation")
  return data.id
}

export async function getConversation(token, conversationId) {
  const res = await fetch(`${API_BASE}/api/conversations/${conversationId}`, { headers: authHeaders(token) })
  return handleJson(res, "Erreur chargement de la conversation")
}

export async function deleteConversation(token, conversationId) {
  const res = await fetch(`${API_BASE}/api/conversations/${conversationId}`, {
    method: "DELETE",
    headers: authHeaders(token),
  })
  return handleJson(res, "Erreur suppression de la conversation")
}

/** Persiste un message côté serveur (fire-and-forget côté appelant) : mêmes champs que les
 * objets `messages` déjà utilisés côté frontend (type, text, sources, kind, data). */
export async function appendMessage(token, conversationId, message) {
  const res = await fetch(`${API_BASE}/api/conversations/${conversationId}/messages`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({
      type: message.type,
      text: message.text ?? null,
      kind: message.kind ?? null,
      sources: message.sources || [],
      data: message.data ?? null,
    }),
  })
  return handleJson(res, "Erreur enregistrement du message")
}

export async function postRemediationResults(token, classCode, chapter, answers) {
  const res = await fetch(`${API_BASE}/api/remediation/results`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({ class_level: classCode, chapter, answers }),
  })
  return handleJson(res, "Erreur enregistrement des résultats")
}

export async function postStruggle(token, classCode, chapter, question) {
  const res = await fetch(`${API_BASE}/api/struggles`, {
    method: "POST",
    headers: authHeaders(token),
    body: JSON.stringify({ class_level: classCode, chapter, question }),
  })
  return handleJson(res, "Erreur enregistrement")
}

/** Message d'accueil personnalisé (null si l'élève n'a pas encore d'historique). */
export async function getGreeting(token) {
  const res = await fetch(`${API_BASE}/api/greeting`, { headers: authHeaders(token) })
  const data = await handleJson(res, "Erreur chargement de l'accueil personnalisé")
  return data.message
}

/** Profil de progression (sujets récents, notions à revoir) reconstruit depuis l'historique
 * serveur du compte connecté — propre à ce compte, contrairement au profil "invité" local. */
export async function getStudentProfile(token) {
  const res = await fetch(`${API_BASE}/api/profile`, { headers: authHeaders(token) })
  return handleJson(res, "Erreur chargement du profil")
}

// ---------------------------------------------------------------------------
// Tableau de bord décideurs — statistiques agrégées (jamais nominatives)
// ---------------------------------------------------------------------------

function adminQuery(classLevel) {
  return classLevel ? `?class_level=${encodeURIComponent(classLevel)}` : ""
}

export async function getAdminOverview(token) {
  const res = await fetch(`${API_BASE}/api/admin/overview`, { headers: authHeaders(token) })
  return handleJson(res, "Erreur chargement des statistiques")
}

export async function getAdminSuccessByChapter(token, classLevel = "") {
  const res = await fetch(`${API_BASE}/api/admin/success-by-chapter${adminQuery(classLevel)}`, { headers: authHeaders(token) })
  const data = await handleJson(res, "Erreur chargement des statistiques par chapitre")
  return data.chapters
}

export async function getAdminWeakNotions(token, classLevel = "") {
  const res = await fetch(`${API_BASE}/api/admin/weak-notions${adminQuery(classLevel)}`, { headers: authHeaders(token) })
  const data = await handleJson(res, "Erreur chargement des notions fragiles")
  return data.notions
}

export async function getAdminTrend(token, classLevel = "") {
  const res = await fetch(`${API_BASE}/api/admin/trend${adminQuery(classLevel)}`, { headers: authHeaders(token) })
  const data = await handleJson(res, "Erreur chargement de la tendance")
  return data.trend
}

export async function getAdminActivity(token, classLevel = "") {
  const res = await fetch(`${API_BASE}/api/admin/activity${adminQuery(classLevel)}`, { headers: authHeaders(token) })
  const data = await handleJson(res, "Erreur chargement de l'activité")
  return data.activity
}
