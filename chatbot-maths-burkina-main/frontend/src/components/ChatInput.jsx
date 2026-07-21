import React from "react"
import { SendHorizontal, Baby, PencilRuler, BookOpen, ListChecks, ClipboardCheck } from "lucide-react"
import Button from "./ui/Button"

export default function ChatInput({
  question,
  setQuestion,
  onSend,
  onSimplify,
  onExercise,
  onCourse,
  onRemediation,
  onSummary,
  canSimplify,
  canExercise,
  canChapterFeatures,
  loading,
}) {
  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      onSend()
    }
  }

  return (
    <div className="border-t border-base-300/60 bg-base-100/80 p-3 backdrop-blur-md sm:p-4">
      <div className="flex items-end gap-2">
        <textarea
          className="textarea textarea-bordered max-h-40 min-h-[3rem] w-full flex-1 resize-none rounded-xl bg-base-100 text-base"
          rows={1}
          placeholder="Pose ta question de maths ici, à tout moment..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
        />
        <Button
          variant="primary"
          size="lg"
          onClick={() => onSend()}
          disabled={!question.trim() || loading}
          title="Envoyer"
        >
          <SendHorizontal size={18} />
        </Button>
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={onCourse}
          disabled={!canChapterFeatures || loading}
          title={!canChapterFeatures ? "Choisis une classe et un chapitre pour voir le cours" : "Ouvrir le document de cours de ce chapitre"}
        >
          <BookOpen size={14} /> Voir le cours
        </Button>
        <Button variant="outline" size="sm" onClick={onSummary} disabled={loading} title="Points essentiels de la séance ou du chapitre">
          <ListChecks size={14} /> Résumé
        </Button>
        <Button variant="outline" size="sm" onClick={onSimplify} disabled={!canSimplify || loading}>
          <Baby size={14} /> Simplifie
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={onExercise}
          disabled={!canExercise || loading}
          title={!canExercise ? "Choisis une classe pour générer un exercice" : "Chapitre non choisi ? Un chapitre adapté sera proposé automatiquement."}
        >
          <PencilRuler size={14} /> Exercice
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={onRemediation}
          disabled={!canChapterFeatures || loading}
          title={!canChapterFeatures ? "Choisis une classe et un chapitre pour la remédiation" : "QCM diagnostique sur ce chapitre"}
        >
          <ClipboardCheck size={14} /> Remédiation
        </Button>
        <span className="ml-auto hidden text-sm text-base-content/50 sm:inline">
          Entrée pour envoyer · Maj+Entrée pour une nouvelle ligne
        </span>
      </div>
    </div>
  )
}
