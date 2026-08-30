import React, { useEffect, useState } from "react"
import { ChevronLeft, ChevronRight, Loader2, AlertTriangle, RotateCw, HelpCircle, CheckCircle2 } from "lucide-react"
import Modal from "./ui/Modal.jsx"
import BottomSheet from "./ui/BottomSheet.jsx"
import Badge from "./ui/Badge.jsx"
import MathContent from "./MathContent.jsx"
import { getFlashcards } from "../api.js"
import { useIsMobile } from "../lib/useMediaQuery.js"

/**
 * Jeu de flashcards "recto/verso" façon Quizlet : une carte à la fois, clic (ou touche Espace)
 * pour la retourner et voir la réponse, flèches pour naviguer. Voir get_flashcards côté backend
 * pour le format JSON attendu (un fichier par chapitre, déposé par l'équipe pédagogique).
 */
export default function FlashcardsViewer({ open, onClose, classCode, chapter }) {
  const isMobile = useIsMobile()
  const Container = isMobile ? BottomSheet : Modal
  const [cards, setCards] = useState([])
  const [index, setIndex] = useState(0)
  const [flipped, setFlipped] = useState(false)
  const [status, setStatus] = useState("loading") // "loading" | "ready" | "error" | "unavailable"

  useEffect(() => {
    if (!open) return
    let cancelled = false
    setStatus("loading")
    setIndex(0)
    setFlipped(false)

    getFlashcards(classCode, chapter)
      .then((data) => {
        if (cancelled) return
        if (!data || data.length === 0) {
          setStatus("unavailable")
          return
        }
        setCards(data)
        setStatus("ready")
      })
      .catch((err) => {
        if (cancelled) return
        setStatus(err?.status === 404 ? "unavailable" : "error")
      })

    return () => {
      cancelled = true
    }
  }, [open, classCode, chapter])

  function goTo(next) {
    setFlipped(false)
    setIndex(next)
  }

  function handleKeyDown(e) {
    if (e.key === " " || e.key === "Enter") {
      e.preventDefault()
      setFlipped((f) => !f)
    } else if (e.key === "ArrowRight" && index < cards.length - 1) {
      goTo(index + 1)
    } else if (e.key === "ArrowLeft" && index > 0) {
      goTo(index - 1)
    }
  }

  const card = cards[index]

  return (
    <Container open={open} onClose={onClose} title={`Flashcards : ${chapter}`}>
      <div className="flex flex-col items-center gap-4" onKeyDown={handleKeyDown} tabIndex={-1}>
        {status === "loading" && (
          <div className="flex min-h-[40vh] flex-col items-center justify-center gap-2 text-base-content/50">
            <Loader2 size={22} className="animate-spin" />
            Chargement des flashcards…
          </div>
        )}

        {status === "unavailable" && (
          <div className="flex min-h-[40vh] flex-col items-center justify-center gap-2 text-center text-base-content/60">
            <AlertTriangle size={22} />
            Pas encore de flashcards disponibles pour ce chapitre.
          </div>
        )}

        {status === "error" && (
          <div className="flex min-h-[40vh] flex-col items-center justify-center gap-2 text-center text-error">
            <AlertTriangle size={22} />
            Impossible de charger les flashcards pour le moment. Réessaie plus tard.
          </div>
        )}

        {status === "ready" && card && (
          <>
            <div className="w-full max-w-md">
              <div className="mb-2 flex items-center justify-between text-sm text-base-content/50">
                <span>Carte {index + 1} / {cards.length}</span>
                {flipped && (
                  <span className="flex items-center gap-1 text-xs font-medium text-primary">
                    <CheckCircle2 size={13} /> Réponse
                  </span>
                )}
              </div>
              <div className="h-1.5 w-full overflow-hidden rounded-full bg-base-200">
                <div
                  className="h-full rounded-full bg-primary transition-all duration-300 ease-out"
                  style={{ width: `${((index + 1) / cards.length) * 100}%` }}
                />
              </div>
            </div>

            {/* Perspective sur le conteneur externe, rotation sur l'interne : les deux faces sont
                superposées (absolute inset-0) et chacune masquée quand elle regarde "vers
                l'intérieur" (backface-visibility), donnant l'effet de retournement 3D. */}
            <div
              className="w-full max-w-md [perspective:1200px]"
              role="button"
              tabIndex={0}
              onClick={() => setFlipped((f) => !f)}
              title="Cliquer pour retourner la carte"
            >
              <div
                className="relative h-72 w-full transition-transform duration-500 ease-out [transform-style:preserve-3d]"
                style={{ transform: flipped ? "rotateY(180deg)" : "rotateY(0deg)" }}
              >
                <div className="absolute inset-0 flex cursor-pointer flex-col items-center justify-center gap-4 overflow-y-auto rounded-2xl border border-primary/20 bg-gradient-to-br from-base-100 to-primary/[0.06] p-7 text-center shadow-md [backface-visibility:hidden]">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-primary/15 text-primary">
                    <HelpCircle size={20} />
                  </div>
                  <Badge variant="primary">Question</Badge>
                  <div className="font-heading text-lg font-semibold leading-snug text-base-content">
                    <MathContent>{card.front}</MathContent>
                  </div>
                  <span className="mt-1 flex shrink-0 items-center gap-1.5 rounded-full bg-base-200/70 px-3 py-1.5 text-xs font-medium text-base-content/55">
                    <RotateCw size={12} /> Clique pour voir la réponse
                  </span>
                </div>
                <div
                  className="absolute inset-0 flex cursor-pointer flex-col items-center justify-center gap-4 overflow-y-auto rounded-2xl border border-primary/40 bg-gradient-to-br from-primary/[0.12] to-primary/5 p-7 text-center shadow-md [backface-visibility:hidden]"
                  style={{ transform: "rotateY(180deg)" }}
                >
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-primary/20 text-primary">
                    <CheckCircle2 size={20} />
                  </div>
                  <Badge variant="success">Réponse</Badge>
                  <div className="font-heading text-lg font-semibold leading-snug text-primary">
                    <MathContent>{card.back}</MathContent>
                  </div>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => goTo(index - 1)}
                disabled={index <= 0}
                className="flex h-10 w-10 items-center justify-center rounded-full border border-base-300/60 text-base-content/70 hover:bg-base-200 disabled:pointer-events-none disabled:opacity-30"
                title="Carte précédente"
              >
                <ChevronLeft size={18} />
              </button>
              <button
                type="button"
                onClick={() => goTo(index + 1)}
                disabled={index >= cards.length - 1}
                className="flex h-10 w-10 items-center justify-center rounded-full border border-base-300/60 text-base-content/70 hover:bg-base-200 disabled:pointer-events-none disabled:opacity-30"
                title="Carte suivante"
              >
                <ChevronRight size={18} />
              </button>
            </div>
          </>
        )}
      </div>
    </Container>
  )
}
