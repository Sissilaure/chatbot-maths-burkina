import React from "react"
import { motion } from "framer-motion"
import { GraduationCap, BookOpen, Lightbulb, RotateCcw, Gauge, Info, Star } from "lucide-react"
import Card from "./ui/Card"
import Button from "./ui/Button"
import ProfilePanel from "./ProfilePanel"
import ConversationList from "./ConversationList"
import { cn } from "../lib/utils"

const STAR_LABELS = {
  1: "QCM d'application",
  2: "Application guidée",
  3: "Notions combinées",
  4: "Situation d'intégration",
  5: "Type olympiades",
}

function buildSuggestions(chapitre) {
  if (!chapitre) return []
  return [
    `Explique-moi simplement le chapitre "${chapitre}"`,
    `Donne-moi un exemple concret sur "${chapitre}"`,
    `Quelles sont les formules importantes de "${chapitre}" ?`,
    `Quelles erreurs faut-il éviter sur "${chapitre}" ?`,
  ]
}

function SectionLabel({ icon: Icon, color, children }) {
  return (
    <label className="font-heading mb-2 flex items-center gap-2 text-sm font-semibold text-base-content/80">
      <span className={cn("flex h-6 w-6 items-center justify-center rounded-lg", color)}>
        <Icon size={13} />
      </span>
      {children}
    </label>
  )
}

export default function Sidebar({
  classes,
  classCode,
  setClassCode,
  chapters,
  chapitre,
  setChapitre,
  difficulty,
  setDifficulty,
  onSuggestionClick,
  onReset,
  profile,
  onResumeTopic,
  onReviewStruggle,
  onDismissStruggle,
  user,
  conversations,
  activeConversationId,
  onSelectConversation,
  onDeleteConversation,
  onNewConversation,
}) {
  const suggestions = buildSuggestions(chapitre)

  return (
    <aside className="flex w-full shrink-0 flex-col gap-4 lg:w-80">
      <Card className="flex items-start gap-2 border-primary/20 bg-primary/5 p-3.5 text-sm text-base-content/70">
        <Info size={15} className="mt-0.5 shrink-0 text-primary" />
        <span>Choisir ta classe et ton chapitre est <strong>facultatif</strong> — ça aide juste à affiner les réponses.</span>
      </Card>

      {user && (
        <ConversationList
          conversations={conversations}
          activeConversationId={activeConversationId}
          onSelect={onSelectConversation}
          onDelete={onDeleteConversation}
          onNew={onNewConversation}
        />
      )}

      <ProfilePanel
        profile={profile}
        onResumeTopic={onResumeTopic}
        onReviewStruggle={onReviewStruggle}
        onDismissStruggle={onDismissStruggle}
      />

      <Card className="p-4">
        <SectionLabel icon={GraduationCap} color="bg-primary/15 text-primary">
          Ma classe
        </SectionLabel>
        <select
          className="select select-bordered w-full rounded-xl bg-base-100"
          value={classCode}
          onChange={(e) => setClassCode(e.target.value)}
        >
          <option value="">-- Optionnel --</option>
          {classes.map((c) => (
            <option key={c.code} value={c.code}>
              {c.name}
            </option>
          ))}
        </select>
      </Card>

      <Card className="p-4">
        <SectionLabel icon={BookOpen} color="bg-secondary/15 text-secondary">
          Chapitre
        </SectionLabel>
        <select
          className="select select-bordered w-full rounded-xl bg-base-100"
          value={chapitre}
          onChange={(e) => setChapitre(e.target.value)}
          disabled={!classCode}
        >
          <option value="">{classCode ? "-- Optionnel --" : "Choisis d'abord une classe"}</option>
          {chapters.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </Card>

      <Card className="p-4">
        <SectionLabel icon={Gauge} color="bg-accent/15 text-accent">
          Difficulté des exercices
        </SectionLabel>
        <div className="flex items-center gap-1">
          {[1, 2, 3, 4, 5].map((level) => (
            <button
              key={level}
              onClick={() => setDifficulty(level === difficulty ? null : level)}
              title={STAR_LABELS[level]}
              className="rounded-lg p-1 transition-transform hover:scale-110"
            >
              <Star
                size={22}
                className={
                  level === 5
                    ? difficulty === 5
                      ? "fill-accent text-accent"
                      : "text-accent/40"
                    : difficulty && level <= difficulty
                      ? "fill-primary text-primary"
                      : "text-base-content/25"
                }
              />
            </button>
          ))}
          <button
            onClick={() => setDifficulty(null)}
            className={cn(
              "ml-2 rounded-full border px-2.5 py-1 text-xs font-medium transition-colors",
              difficulty === null
                ? "border-primary/40 bg-primary/10 text-primary"
                : "border-base-300/60 text-base-content/50 hover:border-primary/30"
            )}
          >
            Auto
          </button>
        </div>
        <p className="mt-1.5 text-sm text-base-content/60">
          {difficulty ? STAR_LABELS[difficulty] : "Automatique — adaptée à tes questions (moyen par défaut)"}
        </p>
      </Card>

      <Card className="p-4">
        <SectionLabel icon={Lightbulb} color="bg-accent/15 text-accent">
          Questions suggérées
        </SectionLabel>
        <div className="flex flex-col gap-1.5">
          {suggestions.length === 0 ? (
            <p className="text-sm text-base-content/50">Choisis un chapitre pour voir des suggestions, ou pose ta question directement en bas.</p>
          ) : (
            suggestions.map((q, i) => (
              <motion.button
                key={q}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.25, delay: i * 0.05, ease: "easeOut" }}
                whileHover={{ x: 3 }}
                onClick={() => onSuggestionClick(q)}
                className="rounded-lg border border-base-300/60 bg-base-100 px-3 py-2 text-left text-sm transition-colors hover:border-primary/50 hover:bg-primary/5"
              >
                {q}
              </motion.button>
            ))
          )}
        </div>
      </Card>

      {!user && (
        <Button variant="outline" size="md" onClick={onReset} className="w-full">
          <RotateCcw size={15} /> Nouvelle conversation
        </Button>
      )}
    </aside>
  )
}
