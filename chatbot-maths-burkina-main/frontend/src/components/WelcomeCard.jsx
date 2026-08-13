import React from "react"
import { motion } from "framer-motion"
import { Sparkles, HelpCircle } from "lucide-react"
import Card from "./ui/Card"
import MathContent from "./MathContent"
import { buildSuggestions } from "../lib/suggestions"
import { useIsMobile } from "../lib/useMediaQuery"

// Sur mobile, au plus 2 suggestions (densité réduite, voir RAPPORT_MOBILE.md §4) ; sur bureau,
// toutes celles que buildSuggestions renvoie (4 aujourd'hui).
const MOBILE_SUGGESTION_LIMIT = 2

function SuggestionButtons({ suggestions, onSuggestionClick }) {
  if (suggestions.length === 0) return null
  return (
    <div className="mb-4 flex flex-col gap-1.5">
      {suggestions.map((q, i) => (
        <motion.button
          key={q}
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.25, delay: i * 0.05, ease: "easeOut" }}
          onClick={() => onSuggestionClick(q)}
          className="rounded-lg border border-base-300/60 bg-base-100 px-3 py-2.5 text-left text-sm transition-colors hover:border-primary/50 hover:bg-primary/5"
        >
          {q}
        </motion.button>
      ))}
    </div>
  )
}

export default function WelcomeCard({ personalizedMessage, chapitre, onSuggestionClick, onOpenAbout }) {
  const isMobile = useIsMobile()
  const allSuggestions = buildSuggestions(chapitre)
  const suggestions = isMobile ? allSuggestions.slice(0, MOBILE_SUGGESTION_LIMIT) : allSuggestions

  return (
    <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.35, ease: "easeOut" }}>
      <Card glow className="overflow-hidden">
        <div className="bg-gradient-to-br from-primary/10 via-secondary/5 to-transparent p-5 sm:p-6">
          {personalizedMessage ? (
            <div className="prose-chat mb-4 max-w-none">
              <p className="font-heading mb-2 flex items-center gap-1.5 text-xl font-extrabold">
                <Sparkles size={20} className="text-accent motion-safe:animate-pulse-slow" />
                Bon retour !
              </p>
              <MathContent>{personalizedMessage}</MathContent>
            </div>
          ) : (
            <>
              {/* <p className="font-heading mb-1 flex items-center gap-1.5 text-xl font-extrabold">
                <Sparkles size={20} className="text-accent motion-safe:animate-pulse-slow" />
                Salut, prêt à progresser en maths ?
              </p> */}
              <p className="mb-4 text-base text-base-content/70">
                Pose n'importe quelle question de maths, du niveau 6ème à la Terminale. Je m'adapte à toi.
              </p>
            </>
          )}

          <SuggestionButtons suggestions={suggestions} onSuggestionClick={onSuggestionClick} />

          {/* Vidéo de démo, 3 cartes explicatives, présentation du projet et rappel du
              consentement ont rejoint AboutPanel (voir App.jsx) : un seul lien discret,
              identique sur les deux tailles d'écran, plutôt qu'un contenu affiché en permanence
              à chaque ouverture (voir RAPPORT_MOBILE.md/RAPPORT_MIGRATION.md). */}
          <button
            type="button"
            onClick={onOpenAbout}
            className="flex items-center gap-1.5 text-sm font-medium text-base-content/50 transition-colors hover:text-primary"
          >
            <HelpCircle size={14} />
            Comment ça marche ?
          </button>
        </div>
      </Card>
    </motion.div>
  )
}
