import React from "react"
import { motion } from "framer-motion"
import { Sparkles, HelpCircle, ChevronRight } from "lucide-react"
import Card from "./ui/Card"
import MathContent from "./MathContent"
import { ONBOARDING_STEPS } from "../lib/onboardingSteps"
import { buildSuggestions } from "../lib/suggestions"
import { useIsMobile } from "../lib/useMediaQuery"

const stepVariants = {
  hidden: { opacity: 0, y: 12 },
  show: (i) => ({ opacity: 1, y: 0, transition: { duration: 0.3, delay: 0.15 + i * 0.08, ease: "easeOut" } }),
}

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

export default function WelcomeCard({ personalizedMessage, chapitre, onSuggestionClick, onOpenHowItWorks }) {
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
              <p className="font-heading mb-1 flex items-center gap-1.5 text-xl font-extrabold">
                <Sparkles size={20} className="text-accent motion-safe:animate-pulse-slow" />
                Salut, prêt à progresser en maths ?
              </p>
              <p className="mb-4 text-base text-base-content/70">
                Pose n'importe quelle question de maths, du niveau 6ème à la Terminale. Je m'adapte à toi.
              </p>
            </>
          )}

          <SuggestionButtons suggestions={suggestions} onSuggestionClick={onSuggestionClick} />

          {isMobile ? (
            <button
              type="button"
              onClick={onOpenHowItWorks}
              className="flex w-full items-center justify-between rounded-lg border border-base-300/50 bg-base-100/70 px-3.5 py-3 text-sm font-medium text-base-content/70 transition-colors hover:border-primary/40 hover:text-primary"
            >
              <span className="flex items-center gap-2">
                <HelpCircle size={16} />
                Comment ça marche ?
              </span>
              <ChevronRight size={16} />
            </button>
          ) : (
            <div className="grid gap-3 sm:grid-cols-3">
              {ONBOARDING_STEPS.map((step, i) => (
                <motion.div
                  key={i}
                  custom={i}
                  initial="hidden"
                  animate="show"
                  variants={stepVariants}
                  whileHover={{ y: -4 }}
                  transition={{ duration: 0.2, ease: "easeOut" }}
                  className="card-interactive rounded-xl border border-base-300/50 bg-base-100/70 p-3.5"
                >
                  <div className={`mb-2 inline-flex h-8 w-8 items-center justify-center rounded-lg ${step.color}`}>
                    <step.icon size={16} />
                  </div>
                  <p className="font-heading text-base font-semibold">{step.title}</p>
                  <p className="mt-0.5 text-sm leading-relaxed text-base-content/60">{step.text}</p>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </Card>
    </motion.div>
  )
}
