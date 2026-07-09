const API_BASE = 'http://127.0.0.1:8000'

export async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/api/health`)
    return await res.json()
  } catch {
    return { status: 'error' }
  }
}

export async function getProgramme() {
  const res = await fetch(`${API_BASE}/api/classes`)
  if (!res.ok) throw new Error('Erreur chargement programme')
  const data = await res.json()
  // Convert format to match frontend expectations
  const programme = {}
  data.classes.forEach(cls => {
    programme[cls.code] = {
      nom: cls.name,
      chapitres: [] // Will be loaded separately
    }
  })
  return programme
}

export async function getChapters(classCode) {
  const res = await fetch(`${API_BASE}/api/classes/${classCode}/chapters`)
  if (!res.ok) throw new Error('Erreur chargement chapitres')
  const data = await res.json()
  return data.chapters
}

export async function askQuestion(question, classe, chapitre) {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ question, class_level: classe, chapter: chapitre })
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || `Erreur ${res.status}`)
  }
  const data = await res.json()
  // Convert format to match frontend expectations
  return {
    reponse: data.answer,
    sources: data.sources.map(s => ({
      fichier: s.source || 'Document',
      classe: s.class || classe,
      chapitre: s.chapter || chapitre
    }))
  }
}

export async function simplifyResponse(question, previousResponse) {
  const res = await fetch(`${API_BASE}/api/simplify`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ answer: previousResponse, class_level: '6ème' })
  })
  if (!res.ok) throw new Error('Erreur simplification')
  const data = await res.json()
  return {
    reponse: data.simplified_answer
  }
}

export async function generateExercise(classe, chapitre, difficulty = 'moyen') {
  const res = await fetch(`${API_BASE}/api/exercise`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ class_level: classe, chapter: chapitre })
  })
  if (!res.ok) throw new Error('Erreur génération exercice')
  const data = await res.json()
  return {
    exercice: data.exercise
  }
}