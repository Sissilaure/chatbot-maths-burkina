import React from "react"
import { motion } from "framer-motion"
import { Sparkles, MessageCircleQuestion, PencilRuler, Baby } from "lucide-react"
import Card from "./ui/Card"
import MathContent from "./MathContent"

const stepVariants = {
  hidden: { opacity: 0, y: 12 },
  show: (i) => ({ opacity: 1, y: 0, transition: { duration: 0.3, delay: 0.15 + i * 0.08, ease: "easeOut" } }),
}

const STEPS = [
  {
    icon: MessageCircleQuestion,
    color: "bg-primary/15 text-primary",
    title: "Pose ta question",
    text: "Directement, à tout moment — choisir ta classe et ton chapitre à gauche aide à affiner la réponse, mais ce n'est pas obligatoire.",
  },
  {
    icon: Baby,
    color: "bg-secondary/15 text-secondary",
    title: "Pas compris ?",
    text: "Clique sur \"Simplifie\" pour une explication encore plus simple, avec un autre exemple.",
  },
  {
    icon: PencilRuler,
    color: "bg-accent/15 text-accent",
    title: "Entraîne-toi",
    text: "Génère un exercice sur mesure, avec des indices et une correction détaillée.",
  },
]

export default function WelcomeCard({ personalizedMessage }) {
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

          <div className="grid gap-3 sm:grid-cols-3">
            {STEPS.map((step, i) => (
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
        </div>
      </Card>
    </motion.div>
  )
}
