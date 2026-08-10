import React from "react"
import BottomSheet from "./ui/BottomSheet.jsx"
import VideoGuide from "./VideoGuide.jsx"
import { ONBOARDING_STEPS } from "../lib/onboardingSteps.js"

/**
 * Feuille modale mobile regroupant ce qui occupait auparavant le haut de l'écran en permanence :
 * la vidéo de démo (VideoGuide, avec sa propre logique de fermeture définitive inchangée) et les
 * 3 cartes explicatives — voir RAPPORT_MOBILE.md §1. Sur bureau, ce contenu reste affiché en
 * ligne (VideoGuide dans App.jsx, cartes dans WelcomeCard) : cette feuille n'est montée que sur
 * mobile, via le lien « Comment ça marche ? » de WelcomeCard.
 */
export default function HowItWorksSheet({ open, onClose }) {
  return (
    <BottomSheet open={open} onClose={onClose} title="Comment ça marche ?">
      <div className="flex flex-col gap-4">
        <VideoGuide />

        <div className="flex flex-col gap-3">
          {ONBOARDING_STEPS.map((step, i) => (
            <div key={i} className="rounded-xl border border-base-300/50 bg-base-100/70 p-3.5">
              <div className={`mb-2 inline-flex h-8 w-8 items-center justify-center rounded-lg ${step.color}`}>
                <step.icon size={16} />
              </div>
              <p className="font-heading text-base font-semibold">{step.title}</p>
              <p className="mt-0.5 text-sm leading-relaxed text-base-content/60">{step.text}</p>
            </div>
          ))}
        </div>
      </div>
    </BottomSheet>
  )
}
