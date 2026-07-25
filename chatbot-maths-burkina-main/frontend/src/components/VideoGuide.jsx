import React, { useState } from "react"
import { motion } from "framer-motion"
import { PlayCircle, X, Maximize2, Minimize2 } from "lucide-react"
import Card from "./ui/Card"

// "-v2" : changer ce suffixe fait réapparaître le guide pour tout le monde (y compris ceux qui
// l'avaient déjà fermé), utile après une mise à jour de la vidéo ou pour la remettre en avant.
const DISMISSED_KEY = "chatmaths-video-guide-dismissed-v2"

/**
 * Petit onglet toujours visible en haut du chat (épinglé, ne défile pas avec les messages) :
 * la démo se lance seule (muette, en boucle — autoplay navigateur oblige) dans un format compact.
 * L'élève peut l'agrandir s'il veut la regarder avec le son via les contrôles, ou la fermer si elle
 * ne l'intéresse pas (le choix est mémorisé, elle ne revient pas au rechargement).
 */
export default function VideoGuide() {
  const [dismissed, setDismissed] = useState(() => localStorage.getItem(DISMISSED_KEY) === "true")
  const [expanded, setExpanded] = useState(false)

  function handleDismiss() {
    localStorage.setItem(DISMISSED_KEY, "true")
    setDismissed(true)
  }

  if (dismissed) return null

  return (
    <Card className="sticky top-0 z-10 mb-3 overflow-hidden shadow-md">
      <div className="flex items-center justify-between gap-2 px-4 py-2 text-sm font-semibold text-primary">
        <span className="flex items-center gap-2">
          <PlayCircle size={16} />
          Comment ça marche ?
        </span>
        <div className="flex items-center gap-1">
          <button
            onClick={() => setExpanded((e) => !e)}
            className="rounded-lg p-1 text-base-content/50 transition-colors hover:bg-primary/10 hover:text-primary"
            title={expanded ? "Réduire la vidéo" : "Agrandir la vidéo"}
          >
            {expanded ? <Minimize2 size={15} /> : <Maximize2 size={15} />}
          </button>
          <button
            onClick={handleDismiss}
            className="rounded-lg p-1 text-base-content/50 transition-colors hover:bg-error/10 hover:text-error"
            title="Fermer"
          >
            <X size={15} />
          </button>
        </div>
      </div>

      <motion.div
        animate={{ height: expanded ? 420 : 140 }}
        transition={{ duration: 0.25, ease: "easeOut" }}
        className="overflow-hidden border-t border-base-300/60 bg-black"
      >
        <video
          src="/demo/comment-ca-marche.webm"
          className="mx-auto h-full w-full object-contain"
          autoPlay
          muted
          loop
          controls={expanded}
          playsInline
          preload="metadata"
        />
      </motion.div>
    </Card>
  )
}
