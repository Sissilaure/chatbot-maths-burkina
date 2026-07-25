import React, { useEffect, useRef, useState } from "react"
import { AnimatePresence, motion } from "framer-motion"
import { AlertTriangle, CheckCircle2, XCircle, PanelLeftClose, PanelLeftOpen } from "lucide-react"
import {
  checkHealth,
  getClasses,
  getChapters,
  askQuestionStream,
  simplifyResponse,
  generateExercise,
  explainExercisePhoto,
  generateRemediation,
  getCourseFileUrl,
  checkCourseAvailable,
  getSummary,
  listConversations,
  createConversation,
  getConversation,
  deleteConversation,
  appendMessage,
  postRemediationResults,
  postStruggle,
  getGreeting,
  getStudentProfile,
} from "./api.js"
import Header from "./components/Header.jsx"
import Sidebar from "./components/Sidebar.jsx"
import MessageBubble from "./components/MessageBubble.jsx"
import ExerciseCard from "./components/ExerciseCard.jsx"
import RemediationQuiz from "./components/RemediationQuiz.jsx"
import ChatInput from "./components/ChatInput.jsx"
import TypingIndicator from "./components/TypingIndicator.jsx"
import WelcomeCard from "./components/WelcomeCard.jsx"
import VideoGuide from "./components/VideoGuide.jsx"
import BackgroundBlobs from "./components/BackgroundBlobs.jsx"
import AuthGate from "./components/AuthGate.jsx"
import AdminDashboard from "./components/AdminDashboard.jsx"
import Button from "./components/ui/Button.jsx"
import ExportMenu from "./components/ExportMenu.jsx"
import { exportNodeToPDF } from "./lib/pdf.js"
import { exportMessagesToDocx } from "./lib/docx.js"
import { compressImageFile } from "./lib/image.js"
import { getProfile, recordTopicVisit, recordStruggle, dismissStruggle, clearProfile } from "./lib/profile.js"
import { getToken, logout as authLogout, restoreSession, AUTH_CHOICE_KEY } from "./lib/auth.js"
import { buildHistoryUpTo } from "./lib/history.js"

const STORAGE_KEY = "chatmaths-session-v1"
const EXERCISE_BATCH_SIZE = 5

function loadSavedSession() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw)
    // Une réponse laissée en plein streaming (page rechargée en cours de génération) ne doit
    // pas rester bloquée avec son curseur clignotant au prochain chargement.
    if (Array.isArray(parsed.messages)) {
      parsed.messages = parsed.messages.map((m) => (m.streaming ? { ...m, streaming: false } : m))
    }
    return parsed
  } catch {
    return null
  }
}

const saved = loadSavedSession()

/** Retrouve la dernière question/réponse d'une conversation rechargée, pour que "Simplifie"
 * fonctionne tout de suite après avoir rouvert une conversation depuis l'historique. */
function deriveLastExchange(msgs) {
  for (let i = msgs.length - 1; i >= 0; i--) {
    if (msgs[i].type === "bot" && (!msgs[i].kind || msgs[i].kind === "chat")) {
      const prevUser = msgs[i - 1]
      return { lastQuestion: prevUser?.type === "user" ? prevUser.text : "", lastAnswer: msgs[i].text || "" }
    }
  }
  return { lastQuestion: "", lastAnswer: "" }
}

export default function App() {
  const [theme, setTheme] = useState(() => localStorage.getItem("chatmaths-theme") || "chatmaths-light")
  const [sidebarOpen, setSidebarOpen] = useState(() => {
    const stored = localStorage.getItem("chatmaths-sidebar-open")
    if (stored !== null) return stored !== "false"
    // Aucune préférence enregistrée : ouvert par défaut sur grand écran, replié sur mobile (le
    // panneau s'empile AU-DESSUS du chat en dessous de lg — sans ça, l'élève doit descendre sous
    // toute la colonne classe/chapitre/profil avant de voir où poser sa question).
    return typeof window !== "undefined" ? window.matchMedia("(min-width: 1024px)").matches : true
  })

  // Comptes élèves (optionnel) : voir handleAuthenticated/handleContinueAsGuest plus bas.
  const [authChecking, setAuthChecking] = useState(() => localStorage.getItem(AUTH_CHOICE_KEY) === "authenticated")
  const [showAuthGate, setShowAuthGate] = useState(() => {
    const choice = localStorage.getItem(AUTH_CHOICE_KEY)
    return choice !== "guest" && choice !== "authenticated"
  })
  const [user, setUser] = useState(null)
  const [role, setRole] = useState(null)
  const [conversations, setConversations] = useState([])
  const [activeConversationId, setActiveConversationId] = useState(null)
  const [greetingMessage, setGreetingMessage] = useState(null)
  const [classes, setClasses] = useState([])
  const [classCode, setClassCode] = useState(saved?.classCode || "")
  const [chapters, setChapters] = useState([])
  const [chapitre, setChapitre] = useState(saved?.chapitre || "")
  // null = automatique (le serveur déduit un niveau adapté aux questions posées, moyen par défaut)
  const [difficulty, setDifficulty] = useState(saved?.difficulty ?? null)

  const [messages, setMessages] = useState(saved?.messages || [])
  const [question, setQuestion] = useState("")
  const [loading, setLoading] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [regeneratingIndex, setRegeneratingIndex] = useState(null)
  const [serverOnline, setServerOnline] = useState(true)
  const [exportingSession, setExportingSession] = useState(false)
  const [exerciseProgress, setExerciseProgress] = useState(null)
  const [photoLoading, setPhotoLoading] = useState(false)
  // Dernière photo/PDF d'exercice envoyée : tant qu'elle est active, les messages suivants la
  // renvoient à Claude avec l'historique (voir handleSend) pour qu'il puisse continuer à "voir"
  // l'exercice sur des questions de suivi ("résous la question a"). Remise à null au démarrage
  // d'une nouvelle conversation, au changement de conversation, ou en cliquant sur "Nouveau sujet".
  const [activePhoto, setActivePhoto] = useState(null)
  const [profile, setProfile] = useState(() => getProfile())
  const [toast, setToast] = useState(null)

  // Suivi séparé de la dernière question/réponse texte pour "Simplifie"
  // (le champ de saisie est vidé après l'envoi, donc on ne peut pas s'y fier)
  const [lastQuestion, setLastQuestion] = useState(saved?.lastQuestion || "")
  const [lastAnswer, setLastAnswer] = useState(saved?.lastAnswer || "")

  const chatRef = useRef(null)
  const sessionContentRef = useRef(null)
  // Miroir synchrone de activeConversationId : évite qu'un message user + un message bot
  // envoyés coup sur coup (avant le re-render qui propage le state) créent chacun leur
  // propre conversation faute de voir l'id déjà en cours de création.
  const activeConversationIdRef = useRef(null)
  const creatingConversationRef = useRef(null)
  const classeNom = classes.find((c) => c.code === classCode)?.name || ""

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme)
    localStorage.setItem("chatmaths-theme", theme)
  }, [theme])

  useEffect(() => {
    localStorage.setItem("chatmaths-sidebar-open", String(sidebarOpen))
  }, [sidebarOpen])

  // Le backend peut mettre du temps à démarrer (première installation, chargement du modèle
  // d'embeddings...). Plutôt que d'échouer une fois pour toutes, on réessaie en tâche de fond
  // jusqu'à ce qu'il réponde, avec un délai croissant entre les tentatives.
  useEffect(() => {
    let cancelled = false
    let delay = 1000

    async function poll() {
      while (!cancelled) {
        const h = await checkHealth()
        const online = h.status === "healthy" || h.status === "degraded"
        if (cancelled) return
        setServerOnline(online)

        if (online) {
          try {
            const list = await getClasses()
            if (!cancelled) setClasses(list)
            return
          } catch {
            /* le serveur répond mais pas encore prêt à servir les classes, on reessaie */
          }
        }

        await new Promise((resolve) => setTimeout(resolve, delay))
        delay = Math.min(delay * 1.5, 5000)
      }
    }

    poll()
    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    if (chatRef.current) chatRef.current.scrollTop = chatRef.current.scrollHeight
  }, [messages, loading])

  useEffect(() => {
    if (classCode) {
      loadChapters(classCode)
    } else {
      setChapters([])
    }
  }, [classCode])

  // Sauvegarde automatique de la session invité (classe, chapitre...) dans localStorage.
  // Un élève connecté a sa conversation persistée côté serveur à la place (voir plus bas) :
  // on n'écrase pas la session invité pendant qu'il est connecté.
  useEffect(() => {
    if (user) return
    // imageUrl est une blob: URL valable seulement pour la durée de vie de la page : on ne la
    // persiste pas (elle serait cassée au prochain chargement de toute façon).
    const persistableMessages = messages.some((m) => m.imageUrl)
      ? messages.map((m) => (m.imageUrl ? { ...m, imageUrl: null } : m))
      : messages
    const payload = { classCode, chapitre, difficulty, messages: persistableMessages, lastQuestion, lastAnswer }
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
    } catch {
      /* stockage plein ou indisponible, tant pis */
    }
  }, [user, classCode, chapitre, difficulty, messages, lastQuestion, lastAnswer])

  // Au premier chargement, si un token de connexion était mémorisé, on le valide auprès du
  // backend avant d'afficher quoi que ce soit (évite un flash appli-invité puis connectée).
  useEffect(() => {
    if (localStorage.getItem(AUTH_CHOICE_KEY) !== "authenticated") return
    let cancelled = false
    restoreSession().then((session) => {
      if (cancelled) return
      if (session) {
        setUser(session.username)
        setRole(session.role)
      } else {
        setShowAuthGate(true)
      }
      setAuthChecking(false)
    })
    return () => {
      cancelled = true
    }
  }, [])

  // Une fois connecté : charge l'historique de conversations et l'accueil personnalisé.
  // Un décideur n'a pas de chat élève : il n'a pas besoin de cette donnée.
  useEffect(() => {
    if (!user || role === "decideur") return
    let cancelled = false

    async function loadUserData() {
      const token = getToken()
      try {
        const list = await listConversations(token)
        if (cancelled) return
        setConversations(list)
        if (list.length > 0) {
          await openConversation(list[0].id)
        } else {
          // Compte tout juste créé (ou sans historique) : on repart d'une page blanche plutôt
          // que de laisser traîner une éventuelle conversation invitée du même navigateur.
          setMessages([])
          setActiveConv(null)
          setLastQuestion("")
          setLastAnswer("")
        }
      } catch {
        /* historique indisponible pour le moment, on continue sans */
      }
      try {
        const greeting = await getGreeting(token)
        if (!cancelled) setGreetingMessage(greeting)
      } catch {
        /* accueil personnalisé indisponible, tant pis */
      }
      try {
        const serverProfile = await getStudentProfile(token)
        if (!cancelled) setProfile(serverProfile)
      } catch {
        /* profil indisponible pour le moment, on continue sans */
      }
    }

    loadUserData()
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [user])

  async function loadChapters(code) {
    try {
      const list = await getChapters(code)
      setChapters(list)
    } catch {
      pushBotError("Impossible de charger les chapitres pour cette classe.")
    }
  }

  function pushUserMessage(text, imageUrl = null) {
    setMessages((prev) => [...prev, { type: "user", text, sources: [], imageUrl }])
  }

  function pushBotMessage(text, sources = [], kind = "chat") {
    setMessages((prev) => [...prev, { type: "bot", text, sources, kind }])
  }

  function pushExerciseMessage(data) {
    setMessages((prev) => [...prev, { type: "exercise", data }])
  }

  function pushRemediationMessage(data) {
    setMessages((prev) => [...prev, { type: "remediation", data }])
  }

  function pushBotError(text) {
    setMessages((prev) => [...prev, { type: "bot", text, sources: [], kind: "error" }])
  }

  function showToast(text, kind = "success") {
    setToast({ text, kind, id: Date.now() })
  }

  useEffect(() => {
    if (!toast) return
    const timer = setTimeout(() => setToast(null), 4000)
    return () => clearTimeout(timer)
  }, [toast])

  /** Met à jour le dernier message de la liste (utilisé pour brancher les fragments du streaming). */
  function patchLastMessage(patch) {
    setMessages((prev) => {
      if (prev.length === 0) return prev
      const next = [...prev]
      const last = next[next.length - 1]
      next[next.length - 1] = typeof patch === "function" ? patch(last) : { ...last, ...patch }
      return next
    })
  }

  function patchMessageAt(index, patch) {
    setMessages((prev) => prev.map((m, i) => (i === index ? { ...m, ...patch } : m)))
  }

  /** Élève connecté : profil reconstruit depuis SON historique serveur (propre à ce compte).
   * Invité : profil local (localStorage), remis à zéro à la déconnexion — voir handleLogout. */
  async function refreshProfile() {
    if (user) {
      try {
        setProfile(await getStudentProfile(getToken()))
      } catch {
        /* on garde le profil precedent si la requete echoue */
      }
    } else {
      setProfile(getProfile())
    }
  }

  // ==========================================================================
  // Comptes élèves : chargement/écriture de l'historique côté serveur
  // ==========================================================================

  function setActiveConv(id) {
    activeConversationIdRef.current = id
    setActiveConversationId(id)
  }

  async function openConversation(id) {
    const token = getToken()
    const conv = await getConversation(token, id)
    setMessages(conv.messages)
    setActiveConv(id)
    setActivePhoto(null)
    if (conv.class_level) setClassCode(conv.class_level)
    if (conv.chapter) setChapitre(conv.chapter)
    const { lastQuestion: lq, lastAnswer: la } = deriveLastExchange(conv.messages)
    setLastQuestion(lq)
    setLastAnswer(la)
  }

  /** Crée la conversation serveur au tout premier message si elle n'existe pas encore
   * (pas de ligne vide créée pour un élève connecté qui ne discute jamais). Dédoublonne les
   * appels concurrents (ex: message user + message bot envoyés coup sur coup) sur la même
   * promesse de création plutôt que de créer deux conversations en parallèle. */
  async function ensureConversation() {
    if (!user) return null
    if (activeConversationIdRef.current) return activeConversationIdRef.current

    if (!creatingConversationRef.current) {
      creatingConversationRef.current = (async () => {
        const token = getToken()
        const id = await createConversation(token, classCode, chapitre)
        setActiveConv(id)
        setConversations((prev) => [
          { id, title: classCode && chapitre ? `${classCode} · ${chapitre}` : "Discussion libre", class_level: classCode, chapter: chapitre, updated_at: new Date().toISOString() },
          ...prev,
        ])
        return id
      })().finally(() => {
        creatingConversationRef.current = null
      })
    }
    return creatingConversationRef.current
  }

  /** Persiste un message côté serveur pour un élève connecté ; best-effort (n'interrompt
   * jamais l'expérience de chat si la sauvegarde échoue). */
  async function persistMessage(message) {
    if (!user) return
    try {
      const id = await ensureConversation()
      if (!id) return
      const result = await appendMessage(getToken(), id, message)
      // Le serveur renomme la conversation avec le début de la première question posée (voir
      // database.add_message) : on répercute ce nouveau titre dans la liste affichée.
      if (result?.title) {
        setConversations((prev) => prev.map((c) => (c.id === id ? { ...c, title: result.title } : c)))
      }
    } catch {
      /* la conversation reste utilisable localement même si la sauvegarde échoue */
    }
  }

  function handleAuthenticated({ username, role: userRole }) {
    setUser(username)
    setRole(userRole)
    setShowAuthGate(false)
  }

  function handleContinueAsGuest() {
    localStorage.setItem(AUTH_CHOICE_KEY, "guest")
    setShowAuthGate(false)
  }

  function handleLoginClick() {
    setShowAuthGate(true)
  }

  function handleLogout() {
    authLogout()
    localStorage.setItem(AUTH_CHOICE_KEY, "guest")
    setUser(null)
    setRole(null)
    setConversations([])
    setActiveConv(null)
    setGreetingMessage(null)
    setMessages([])
    setLastQuestion("")
    setLastAnswer("")
    // Le profil du compte qui vient de se déconnecter (sujets/notions) ne doit pas continuer à
    // s'afficher pour la session invité qui suit, ni pour un autre compte connecté ensuite sur
    // ce même navigateur : voir refreshProfile(), qui utilise ce stockage local uniquement
    // en mode invité (les comptes utilisent leur propre profil serveur, propre à chacun).
    setProfile(clearProfile())
  }

  async function handleSelectConversation(id) {
    if (loading || streaming || id === activeConversationId) return
    try {
      await openConversation(id)
    } catch {
      showToast("Impossible de charger cette conversation.", "error")
    }
  }

  async function handleDeleteConversation(id) {
    try {
      await deleteConversation(getToken(), id)
      setConversations((prev) => prev.filter((c) => c.id !== id))
      if (id === activeConversationId) {
        setMessages([])
        setActiveConv(null)
        setLastQuestion("")
        setLastAnswer("")
        setActivePhoto(null)
      }
    } catch {
      showToast("Impossible de supprimer cette conversation.", "error")
    }
  }

  function handleNewConversation() {
    setMessages([])
    setActiveConv(null)
    setLastQuestion("")
    setLastAnswer("")
    setActivePhoto(null)
  }

  async function handleRemediationResults(remediationData, answers) {
    if (!user) return
    try {
      await postRemediationResults(getToken(), remediationData.class_level, remediationData.chapter, answers)
    } catch {
      /* signal de lacune non enregistré, tant pis pour l'accueil personnalisé la prochaine fois */
    }
  }

  /** overrides permet d'envoyer une question précise avec une classe/un chapitre précis sans
   * dépendre du state React (qui ne serait pas encore à jour si on venait de faire setClassCode
   * juste avant) — utilisé par "Notions à revoir" pour renvoyer directement la question posée. */
  async function handleSend(overrides = {}) {
    const q = (overrides.question ?? question).trim()
    if (!q || loading || streaming) return
    const sendClassCode = overrides.classCode ?? classCode
    const sendChapitre = overrides.chapitre ?? chapitre
    const sendClasseNom = classes.find((c) => c.code === sendClassCode)?.name || classeNom
    const history = buildHistoryUpTo(messages)

    setQuestion("")
    pushUserMessage(q)
    persistMessage({ type: "user", text: q, sources: [] })

    // Une photo d'exercice est "active" (envoyée plus tôt dans cette conversation, jamais
    // remplacée depuis) : on la renvoie avec ce message plutôt que de faire un chat texte normal,
    // sinon Claude ne "voit" plus l'image et ne peut pas répondre à un suivi comme "résous le a".
    // Pas de streaming ici : c'est le même appel non-streamé que l'envoi initial de la photo.
    if (activePhoto) {
      setLoading(true)
      try {
        const answer = await explainExercisePhoto(activePhoto, sendClassCode, sendChapitre, q, history)
        pushBotMessage(answer, [], "chat")
        persistMessage({ type: "bot", text: answer, sources: [], kind: "chat" })
        setLastQuestion(q)
        setLastAnswer(answer)
        recordTopicVisit(sendClassCode, sendChapitre, sendClasseNom)
        refreshProfile()
      } catch (err) {
        pushBotError("Impossible de continuer sur cette photo pour le moment. Réessaie, ou renvoie la photo.")
      } finally {
        setLoading(false)
      }
      return
    }

    pushBotMessage("", [], "chat")
    setLoading(true)
    setStreaming(true)
    patchLastMessage({ streaming: true })

    let fullText = ""
    let firstChunk = true

    try {
      await askQuestionStream(q, sendClassCode, sendChapitre, history, {
        onDelta: (delta) => {
          if (firstChunk) {
            setLoading(false)
            firstChunk = false
          }
          fullText += delta
          patchLastMessage((last) => ({ ...last, text: fullText }))
        },
        onDone: ({ sources }) => {
          patchLastMessage((last) => ({ ...last, sources, streaming: false }))
          setLastQuestion(q)
          setLastAnswer(fullText)
          persistMessage({ type: "bot", text: fullText, sources, kind: "chat" })
          recordTopicVisit(sendClassCode, sendChapitre, sendClasseNom)
          refreshProfile()
        },
        onError: (message) => {
          patchLastMessage((last) => ({
            ...last,
            streaming: false,
            text: fullText || (message?.includes("Failed to fetch") ? "Impossible de contacter le serveur backend." : message),
            kind: fullText ? last.kind : "error",
          }))
        },
      })
    } finally {
      setLoading(false)
      setStreaming(false)
    }
  }

  async function handleRegenerate(index) {
    const userMsg = messages[index - 1]
    if (!userMsg || userMsg.type !== "user" || loading || streaming || regeneratingIndex !== null) return

    const history = buildHistoryUpTo(messages.slice(0, index - 1))
    setRegeneratingIndex(index)
    patchMessageAt(index, { text: "", sources: [], kind: "chat", streaming: true })

    let fullText = ""
    await askQuestionStream(userMsg.text, classCode, chapitre, history, {
      onDelta: (delta) => {
        fullText += delta
        patchMessageAt(index, { text: fullText })
      },
      onDone: ({ sources }) => {
        patchMessageAt(index, { sources, streaming: false })
        setLastQuestion(userMsg.text)
        setLastAnswer(fullText)
      },
      onError: () => {
        patchMessageAt(index, { streaming: false, text: fullText || "" })
        pushBotError("Impossible de régénérer cette réponse pour le moment.")
      },
    })

    setRegeneratingIndex(null)
  }

  async function handleSimplify() {
    if (!lastAnswer || loading || streaming) return
    setLoading(true)
    try {
      const simplified = await simplifyResponse(lastQuestion, lastAnswer, classCode, chapitre)
      pushBotMessage(simplified, [], "simplify")
      persistMessage({ type: "bot", text: simplified, kind: "simplify" })
      setLastAnswer(simplified)
      recordStruggle(classCode, chapitre, lastQuestion, classeNom)
      if (user) postStruggle(getToken(), classCode, chapitre, lastQuestion).catch(() => {})
      refreshProfile()
    } catch (err) {
      pushBotError("Impossible de simplifier la réponse pour le moment.")
    }
    setLoading(false)
  }

  async function handleExercise() {
    if (!classCode || loading || streaming) return
    setLoading(true)
    const total = EXERCISE_BATCH_SIZE
    setExerciseProgress({ current: 0, total })
    // On réinjecte chaque exercice déjà généré dans l'historique envoyé au tour suivant,
    // pour que Claude évite de proposer deux fois le même énoncé dans la série.
    let history = buildHistoryUpTo(messages)
    let successCount = 0
    for (let i = 0; i < total; i++) {
      setExerciseProgress({ current: i + 1, total })
      try {
        const exercise = await generateExercise(classCode, chapitre, difficulty, history)
        pushExerciseMessage(exercise)
        persistMessage({ type: "exercise", data: exercise })
        recordTopicVisit(classCode, exercise.chapter || chapitre, classeNom)
        const summary =
          exercise.enonce || (exercise.qcm || []).map((q) => q.question).join(" / ") || `Exercice ${i + 1}`
        history = [...history, { role: "assistant", content: `Exercice déjà proposé dans cette série : ${summary}` }]
        successCount++
      } catch (err) {
        // Un échec isolé ne doit pas interrompre le reste de la série.
      }
    }
    if (successCount === 0) {
      pushBotError("Impossible de générer des exercices pour le moment.")
    }
    refreshProfile()
    setExerciseProgress(null)
    setLoading(false)
  }

  async function handlePhotoExercise(file) {
    if (loading || streaming || photoLoading) return
    setPhotoLoading(true)
    const isImage = file.type.startsWith("image/")
    // Ce que l'élève a éventuellement déjà tapé dans le champ de saisie accompagne la photo
    // (ex: "vérifie juste la question 2") : comme un message normal, le champ est vidé après envoi.
    const accompanyingPrompt = question.trim()
    setQuestion("")
    // Toujours un texte non vide, même sans consigne tapée par l'élève : ce texte alimente aussi
    // l'historique envoyé à Claude pour les messages suivants (voir buildHistoryUpTo). Un texte
    // vide y créerait un tour "élève" fantôme, sans aucune trace qu'une photo a été envoyée — le
    // modèle perd alors le fil dès que la question suivante s'éloigne de sa réponse précédente.
    const displayText =
      accompanyingPrompt || (isImage ? "[Photo d'exercice envoyée]" : `[Fichier envoyé : ${file.name || "exercice.pdf"}]`)
    // Un PDF n'est pas affichable dans une balise <img> (icône cassée) : on ne prévisualise
    // que les vraies images, un PDF envoyé apparaît juste comme un message texte.
    const imageUrl = isImage ? URL.createObjectURL(file) : null
    pushUserMessage(displayText, imageUrl)
    persistMessage({
      type: "user",
      text: accompanyingPrompt || (isImage ? "[Photo d'exercice envoyée]" : `[Fichier envoyé : ${file.name}]`),
      sources: [],
    })
    try {
      const toSend = isImage ? await compressImageFile(file) : file
      const answer = await explainExercisePhoto(toSend, classCode, chapitre, accompanyingPrompt)
      pushBotMessage(answer, [], "chat")
      persistMessage({ type: "bot", text: answer, sources: [], kind: "chat" })
      setLastQuestion(accompanyingPrompt || "Photo d'exercice envoyée")
      setLastAnswer(answer)
      // Reste "active" pour les messages suivants (voir handleSend) : Claude pourra continuer à
      // voir cette même photo tant qu'une nouvelle photo ne la remplace pas ou que l'élève ne
      // change pas de conversation/sujet.
      setActivePhoto(toSend)
      if (classCode) recordTopicVisit(classCode, chapitre, classeNom)
      refreshProfile()
    } catch (err) {
      pushBotError("Impossible d'analyser ce fichier pour le moment. Réessaie avec une photo plus nette et bien cadrée, ou un autre fichier.")
    }
    setPhotoLoading(false)
  }

  async function handleCourse() {
    if (!classCode || !chapitre || loading || streaming) return
    const available = await checkCourseAvailable(classCode, chapitre)
    if (!available) {
      showToast("Cours non disponible pour ce chapitre pour le moment.", "error")
      return
    }
    window.open(getCourseFileUrl(classCode, chapitre), "_blank")
  }

  async function handleRemediation() {
    if (!classCode || !chapitre || loading || streaming) return
    setLoading(true)
    try {
      const history = buildHistoryUpTo(messages)
      const remediation = await generateRemediation(classCode, chapitre, history)
      pushRemediationMessage(remediation)
      persistMessage({ type: "remediation", data: remediation })
      recordTopicVisit(classCode, chapitre, classeNom)
      refreshProfile()
    } catch (err) {
      pushBotError("Impossible de générer le QCM de remédiation pour le moment.")
    }
    setLoading(false)
  }

  async function handleSummary() {
    if (loading || streaming) return
    setLoading(true)
    try {
      const history = buildHistoryUpTo(messages)
      const content = await getSummary(history, classCode, chapitre)
      pushBotMessage(content, [], "summary")
      persistMessage({ type: "bot", text: content, kind: "summary" })
    } catch (err) {
      pushBotError("Impossible de générer le résumé pour le moment.")
    }
    setLoading(false)
  }

  function handleReset() {
    setMessages([])
    setLastQuestion("")
    setLastAnswer("")
    setActivePhoto(null)
  }

  function handleSuggestionClick(q) {
    setQuestion(q)
  }

  function handleResumeTopic(topic) {
    setClassCode(topic.classCode)
    setChapitre(topic.chapitre)
  }

  function handleReviewStruggle(struggle) {
    // Re-pose directement la question (plutôt que de juste pré-remplir le champ) : cliquer sur
    // une notion à revoir doit amener une explication, pas juste préparer la saisie en silence.
    setClassCode(struggle.classCode)
    setChapitre(struggle.chapitre)
    handleSend({ question: struggle.question, classCode: struggle.classCode, chapitre: struggle.chapitre })
  }

  function handleDismissStruggle(index) {
    if (user) {
      // Profil serveur (propre au compte) : pas d'endpoint de suppression dédié, on masque
      // juste côté client — elle peut réapparaître à un prochain rafraîchissement du profil.
      setProfile((p) => ({ ...p, struggles: p.struggles.filter((_, i) => i !== index) }))
    } else {
      dismissStruggle(index)
      refreshProfile()
    }
  }

  async function handleDownloadSession(format = "pdf") {
    if (messages.length === 0) {
      showToast("Pose au moins une question avant de télécharger la session — il n'y a rien à exporter pour l'instant.", "error")
      return
    }
    if (exportingSession) return
    setExportingSession(true)
    try {
      const title = "Prof Amira — Session complète"
      const subtitle = `${classeNom || ""}${chapitre ? " · " + chapitre : ""}`.trim()
      let filename
      if (format === "docx") {
        filename = `chatmaths-session-${Date.now()}.docx`
        await exportMessagesToDocx(messages, { filename, title, subtitle })
      } else {
        if (!sessionContentRef.current) return
        filename = `chatmaths-session-${Date.now()}.pdf`
        await exportNodeToPDF(sessionContentRef.current, { filename, title, subtitle })
      }
      // Le téléchargement se fait silencieusement (aucune fenêtre ne s'ouvre) : sans ce message,
      // on ne peut pas savoir si ça a marché. Le fichier atterrit dans le dossier Téléchargements.
      showToast(`Fichier téléchargé : ${filename} (dossier Téléchargements)`, "success")
    } catch (err) {
      console.error("Export de session échoué:", err)
      showToast("Le téléchargement a échoué. Réessaie, ou recharge la page si le problème persiste.", "error")
    } finally {
      setExportingSession(false)
    }
  }

  // Le chapitre est facultatif pour générer un exercice (le serveur en choisit un lui-même sinon) :
  // seule la classe est nécessaire. Voir le cours et la remédiation ciblent un chapitre précis,
  // donc restent conditionnés aux deux.
  const canGenerateExercise = Boolean(classCode)
  const canUseChapterFeatures = Boolean(classCode && chapitre)

  if (authChecking) {
    return (
      <div className="relative flex min-h-screen items-center justify-center bg-base-200">
        <BackgroundBlobs />
        <div className="relative flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-primary via-secondary to-accent text-white shadow-glow motion-safe:animate-pulse-slow" />
      </div>
    )
  }

  if (showAuthGate) {
    return <AuthGate onAuthenticated={handleAuthenticated} onContinueAsGuest={handleContinueAsGuest} />
  }

  if (role === "decideur") {
    return (
      <AdminDashboard
        token={getToken()}
        username={user}
        theme={theme}
        onToggleTheme={() => setTheme((t) => (t === "chatmaths-dark" ? "chatmaths-light" : "chatmaths-dark"))}
        onLogout={handleLogout}
      />
    )
  }

  return (
    <div className="relative flex min-h-screen flex-col bg-base-200 text-base-content">
      <BackgroundBlobs />
      <Header
        theme={theme}
        onToggleTheme={() => setTheme((t) => (t === "chatmaths-dark" ? "chatmaths-light" : "chatmaths-dark"))}
        user={user}
        onLoginClick={handleLoginClick}
        onLogout={handleLogout}
      />

      {!serverOnline && (
        <div className="mx-auto mt-3 flex w-full max-w-7xl items-center gap-2 px-3 text-sm text-error sm:px-4 lg:px-6">
          <div className="flex w-full items-center gap-2 rounded-xl border border-error/30 bg-error/10 px-4 py-2">
            <AlertTriangle size={15} />
            Le serveur ne répond pas pour le moment. Vérifie qu'il est bien lancé.
          </div>
        </div>
      )}

      <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col gap-4 p-3 sm:p-4 lg:flex-row lg:p-6">
        <AnimatePresence initial={false}>
          {sidebarOpen && (
            <motion.div
              key="sidebar"
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: "auto" }}
              exit={{ opacity: 0, width: 0 }}
              transition={{ duration: 0.2, ease: "easeOut" }}
              className="shrink-0 overflow-hidden"
            >
              <Sidebar
                classes={classes}
                classCode={classCode}
                setClassCode={(c) => {
                  setClassCode(c)
                  setChapitre("")
                }}
                chapters={chapters}
                chapitre={chapitre}
                setChapitre={setChapitre}
                difficulty={difficulty}
                setDifficulty={setDifficulty}
                onSuggestionClick={handleSuggestionClick}
                onReset={handleReset}
                profile={profile}
                onResumeTopic={handleResumeTopic}
                onReviewStruggle={handleReviewStruggle}
                onDismissStruggle={handleDismissStruggle}
                user={user}
                conversations={conversations}
                activeConversationId={activeConversationId}
                onSelectConversation={handleSelectConversation}
                onDeleteConversation={handleDeleteConversation}
                onNewConversation={handleNewConversation}
              />
            </motion.div>
          )}
        </AnimatePresence>

        <main className="flex min-h-[70vh] flex-1 flex-col overflow-hidden rounded-2xl border border-base-300/60 bg-base-100/60 shadow-sm">
          <div className="flex items-center justify-between border-b border-base-300/50 px-4 py-2 sm:px-6">
            <div className="flex min-w-0 items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setSidebarOpen((o) => !o)}
                title={sidebarOpen ? "Réduire le panneau latéral" : "Afficher le panneau latéral"}
              >
                {sidebarOpen ? <PanelLeftClose size={16} /> : <PanelLeftOpen size={16} />}
              </Button>
              <p className="truncate text-xs font-medium text-base-content/50">
                {classeNom ? `${classeNom}${chapitre ? " · " + chapitre : ""}` : "Discussion libre"}
              </p>
            </div>
            <ExportMenu onExport={handleDownloadSession} exporting={exportingSession} label="Télécharger" />
          </div>

          <div ref={chatRef} className="scrollbar-thin flex-1 overflow-y-auto p-4 sm:p-6">
            <VideoGuide />
            <div ref={sessionContentRef} className="space-y-4">
              {messages.length === 0 && <WelcomeCard personalizedMessage={user ? greetingMessage : null} />}

              <AnimatePresence initial={false}>
                {messages.map((msg, i) =>
                  msg.type === "exercise" ? (
                    <ExerciseCard key={i} exercise={msg.data} />
                  ) : msg.type === "remediation" ? (
                    <RemediationQuiz
                      key={i}
                      data={msg.data}
                      onSubmitResults={(answers) => handleRemediationResults(msg.data, answers)}
                    />
                  ) : (
                    <MessageBubble
                      key={i}
                      message={msg}
                      onRegenerate={msg.type === "bot" && i > 0 && messages[i - 1]?.type === "user" ? () => handleRegenerate(i) : null}
                      regenerating={regeneratingIndex === i}
                    />
                  )
                )}
              </AnimatePresence>
            </div>

            {loading && (
              <div className="mt-4">
                <TypingIndicator />
              </div>
            )}
          </div>

          <ChatInput
            question={question}
            setQuestion={setQuestion}
            onSend={handleSend}
            onSimplify={handleSimplify}
            onExercise={handleExercise}
            onCourse={handleCourse}
            onRemediation={handleRemediation}
            onSummary={handleSummary}
            onDownloadSession={handleDownloadSession}
            onPhotoSelected={handlePhotoExercise}
            activePhoto={Boolean(activePhoto)}
            onClearActivePhoto={() => setActivePhoto(null)}
            canSimplify={Boolean(lastAnswer)}
            canExercise={canGenerateExercise}
            canChapterFeatures={canUseChapterFeatures}
            loading={loading || streaming}
            exerciseProgress={exerciseProgress}
            exportingSession={exportingSession}
            photoLoading={photoLoading}
          />
        </main>
      </div>

      <footer className="px-4 pb-4 text-center text-xs text-base-content/40">
        Prof Amira · Programme officiel du Burkina Faso (6ème à Terminale)
        <br />
        Un produit Hakili Lab
      </footer>

      <AnimatePresence>
        {toast && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: 20 }}
            className={`fixed bottom-4 left-1/2 z-50 flex -translate-x-1/2 items-center gap-2 rounded-xl border px-4 py-2.5 text-sm font-medium shadow-lg ${
              toast.kind === "error"
                ? "border-error/30 bg-error/10 text-error"
                : "border-success/30 bg-success/10 text-success"
            }`}
          >
            {toast.kind === "error" ? <XCircle size={16} /> : <CheckCircle2 size={16} />}
            {toast.text}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
