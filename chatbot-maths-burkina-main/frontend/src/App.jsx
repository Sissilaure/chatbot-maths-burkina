import React, { useState, useEffect, useRef } from 'react'
import { checkHealth, getProgramme, getChapters, askQuestion, simplifyResponse, generateExercise } from './api.js'

const QUESTIONS_EXEMPLES = {
  "Fractions": [
    "Comment simplifier une fraction ?",
    "Comment additionner deux fractions ?",
    "Comment calculer une fraction d'un nombre ?"
  ],
  "Theoreme de Pythagore": [
    "Comment calculer l'hypotenuse d'un triangle rectangle ?",
    "Quand utiliser le theoreme de Pythagore ?"
  ],
  "Equations": [
    "Comment resoudre une equation du 1er degre ?",
    "Comment verifier une solution ?"
  ],
  "Fonctions": [
    "Comment calculer l'image d'un nombre ?",
    "Comment tracer une fonction affine ?"
  ],
  "Probabilites": [
    "Comment calculer une probabilite simple ?",
    "Qu'est-ce qu'une experience aleatoire ?"
  ],
  "Derivation": [
    "Comment calculer une derivee ?",
    "A quoi sert la derivee ?"
  ],
  "Suites numeriques": [
    "Comment calculer les termes d'une suite arithmetique ?",
    "Suite arithmetique ou geometrique ?"
  ],
  "Trigonometric": [
    "Comment calculer un angle avec le cosinus ?",
    "Quand utiliser sinus, cosinus ou tangente ?"
  ],
  "default": [
    "Explique-moi ce chapitre",
    "Donne-moi un exemple concret",
    "Quels sont les points importants ?"
  ]
}

export default function App() {
  const [programme, setProgramme] = useState(null)
  const [classeKey, setClasseKey] = useState('')
  const [chapitre, setChapitre] = useState('')
  const [chapitres, setChapitres] = useState([])
  const [messages, setMessages] = useState([])
  const [question, setQuestion] = useState('')
  const [loading, setLoading] = useState(false)
  const [serverOnline, setServerOnline] = useState(false)
  const [currentResponse, setCurrentResponse] = useState('')
  const chatRef = useRef(null)

  useEffect(() => { checkServer(); loadProgramme(); }, [])

  useEffect(() => { 
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight 
  }, [messages])

  useEffect(() => {
    if (classeKey) {
      loadChapters(classeKey)
    } else {
      setChapitres([])
      setChapitre('')
    }
  }, [classeKey])

  function addBotMessage(msg) {
    // msg peut être un objet { text, sources } ou une chaîne (compatibilité)
    const message = typeof msg === 'string' ? { text: msg, sources: [] } : msg
    setMessages(prev => [...prev, { type: 'bot', ...message }])
  }

  function addUserMessage(text) {
    setMessages(prev => [...prev, { type: 'user', text, sources: [] }])
  }

  async function checkServer() {
    const h = await checkHealth()
    setServerOnline(h.status === 'healthy' || h.status === 'degraded')
  }

  async function loadProgramme() {
    try {
      const p = await getProgramme()
      setProgramme(p)
    } catch {
      addBotMessage("\u26a0\ufe0f **Erreur de connexion**\n\nImpossible de charger le programme. Verifie que le serveur backend est lance.")
    }
  }

  async function loadChapters(classCode) {
    try {
      const chapters = await getChapters(classCode)
      setChapitres(chapters)
    } catch {
      addBotMessage("\u26a0\ufe0f **Erreur de connexion**\n\nImpossible de charger les chapitres.")
    }
  }

  const questionsSugg = QUESTIONS_EXEMPLES[chapitre] || QUESTIONS_EXEMPLES["default"]
  const classeNom = programme && classeKey ? programme[classeKey].nom : ''

  async function handleSend() {
    if (!question.trim() || !classeKey || !chapitre) return
    const q = question.trim()
    setQuestion('')
    addUserMessage(q)
    setLoading(true)
    try {
      const res = await askQuestion(q, classeKey, chapitre)
      const reponse = res.reponse || 'Pas de reponse disponible.'
      // Stocker les sources séparément pour ne pas les passer dans formatText
      const sources = res.sources?.length ? res.sources : []
      addBotMessage({ text: reponse, sources })
      setCurrentResponse(res.reponse || '')
    } catch (err) {
      addBotMessage({ text: "❌ **Erreur**\n\n" + (err.message.includes('Failed to fetch') 
        ? "Impossible de contacter le serveur." : `Erreur: ${err.message}`), sources: [] })
    }
    setLoading(false)
  }

  async function handleSimplify() {
    if (!currentResponse) return
    setLoading(true)
    try {
      const res = await simplifyResponse(question || '', currentResponse)
      const reponse = res.reponse || res.statut || 'Pas de simplification disponible.'
      addBotMessage({ text: "👶 **Version simplifiee:**\n\n" + reponse, sources: [] })
    } catch {
      addBotMessage({ text: "❌ Impossible de simplifier la reponse.", sources: [] })
    }
    setLoading(false)
  }

  async function handleExercise() {
    if (!classeKey || !chapitre) return
    setLoading(true)
    try {
      const res = await generateExercise(classeKey, chapitre)
      const exo = res.exercice || res.statut || 'Pas d\'exercice disponible.'
      addBotMessage({ text: "📝 **Exercice genere:**\n\n" + exo, sources: [] })
    } catch {
      addBotMessage({ text: "❌ Impossible de generer un exercice.", sources: [] })
    }
    setLoading(false)
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
  }

  const isReady = classeKey && chapitre

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="logo">
          <span className="logo-icon">📐</span>
          <div className="logo-text">
            <h1>Chat'Maths Burkina</h1>
            <p className="subtitle">Assistant intelligent en mathematiques</p>
          </div>
        </div>
        <div className="header-status">
          <span className={`status-dot ${serverOnline ? 'online' : 'offline'}`} />
          <span>{serverOnline ? '✅ Connecte' : '❌ Hors ligne'}</span>
        </div>
      </header>

      <div className="main-content">
        <aside className="selection-panel">
          <div className="panel-card">
            <h3><i className="fas fa-graduation-cap" /> Ma classe</h3>
            <select className="form-select" value={classeKey} onChange={e => { setClasseKey(e.target.value); setChapitre(''); setCurrentResponse('') }}>
              <option value="">-- Choisis ta classe --</option>
              {programme && Object.entries(programme).map(([key, val]) => (
                <option key={key} value={key}>{val.nom}</option>
              ))}
            </select>
          </div>

          <div className="panel-card">
            <h3><i className="fas fa-book" /> Chapitre</h3>
            <select className="form-select" value={chapitre} onChange={e => { setChapitre(e.target.value); setCurrentResponse('') }} disabled={!classeKey}>
              <option value="">{classeKey ? '-- Choisis un chapitre --' : 'Selectionne d abord une classe'}</option>
              {chapitres.map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>

          <div className="panel-card">
            <h3><i className="fas fa-question-circle" /> Questions types</h3>
            <div className="question-suggestions">
              {!chapitre ? (
                <p className="hint">Selectionne un chapitre pour voir des exemples</p>
              ) : (
                questionsSugg.map((q, i) => (
                  <button key={i} className="suggestion-chip" onClick={() => setQuestion(q)}>
                    <i className="fas fa-lightbulb" /> {q}
                  </button>
                ))
              )}
            </div>
          </div>

          <div className="panel-card">
            <button className="btn btn-outline btn-full" onClick={() => { setMessages([]); setCurrentResponse('') }}>
              <i className="fas fa-undo" /> Nouvelle session
            </button>
          </div>
        </aside>

        <main className="chat-area">
          <div className="chat-messages" ref={chatRef}>
            <div className="message bot welcome-message">
              <div className="message-avatar"><i className="fas fa-robot" /></div>
              <div className="message-content">
                <p><strong>Bienvenue sur Chat'Maths Burkina !</strong></p>
                <p>Je suis ton assistant en mathematiques.</p>
                <ol>
                  <li>Selectionne ta <strong>classe</strong> dans le panneau de gauche</li>
                  <li>Choisis le <strong>chapitre</strong> qui te pose probleme</li>
                  <li>Pose ta question ci-dessous</li>
                </ol>
                <p><em>Je reponds a partir des programmes officiels du Burkina Faso.</em></p>
              </div>
            </div>

            {messages.map((msg, i) => (
              <div key={i} className={`message ${msg.type}`}>
                <div className="message-avatar">
                  <i className={msg.type === 'user' ? 'fas fa-user-graduate' : 'fas fa-robot'} />
                </div>
                <div className="message-content">
                  <div dangerouslySetInnerHTML={{ __html: formatText(msg.text) }} />
                  {msg.sources && msg.sources.length > 0 && (
                    <details className="message-sources" style={{marginTop:'10px'}}>
                      <summary>📚 Sources ({msg.sources.length})</summary>
                      {msg.sources.map((s, si) => (
                        <div key={si} className="source-item">
                          <i className="fas fa-file-alt" />
                          {s.fichier} — {s.classe} / {s.chapitre}
                        </div>
                      ))}
                    </details>
                  )}
                </div>
              </div>
            ))}

            {loading && (
              <div className="message bot">
                <div className="message-avatar"><i className="fas fa-robot" /></div>
                <div className="message-content">
                  <div className="typing-indicator"><span /><span /><span /></div>
                </div>
              </div>
            )}
          </div>

          <div className="chat-input-area">
            <div className="input-row">
              <textarea
                className="form-input"
                placeholder={isReady ? "Pose ta question de maths ici..." : "Selectionne d'abord ta classe et ton chapitre"}
                rows={2}
                value={question}
                onChange={e => setQuestion(e.target.value)}
                onKeyDown={handleKeyDown}
                disabled={!isReady || loading}
              />
              <button className="btn btn-primary btn-send" onClick={handleSend} disabled={!isReady || !question.trim() || loading}>
                <i className="fas fa-paper-plane" />
              </button>
            </div>
            <div className="input-actions">
              <button className="btn btn-sm btn-outline" disabled={!currentResponse || loading} onClick={handleSimplify}>
                <i className="fas fa-child" /> Simplifie
              </button>
              <button className="btn btn-sm btn-outline" disabled={!isReady || loading} onClick={handleExercise}>
                <i className="fas fa-pencil-alt" /> Exercice
              </button>
              <span className="input-status">
                {!classeKey ? 'Choisis ta classe' : !chapitre ? 'Choisis le chapitre' : 'Pose ta question !'}
              </span>
            </div>
          </div>
        </main>
      </div>

      <footer className="app-footer">
        <p>Chat'Maths Burkina v1.0 | <i className="fas fa-flag" /> Programme officiel du Burkina Faso (6eme a Terminale)</p>
        <p className="footer-tech">React + Vite + FastAPI + FAISS + LLM</p>
      </footer>
    </div>
  )
}

function formatText(text) {
  if (!text) return ''
  // Découper le texte par lignes et formater chaque ligne
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code style="background:#f0f0f0;padding:1px 4px;border-radius:3px;font-family:monospace">$1</code>')
    .replace(/^(#{1,3})\s+(.+)$/gm, (_, hashes, content) => {
      const level = hashes.length
      return `<h${level + 2} style="margin:8px 0 4px">${content}</h${level + 2}>`
    })
    .replace(/^[-•]\s+(.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*<\/li>)/s, '<ul style="padding-left:18px;margin:4px 0">$1</ul>')
    .replace(/\n\n/g, '</p><p style="margin-top:8px">')
    .replace(/\n/g, '<br>')
}