import React, { useRef } from "react"
import { SendHorizontal, Baby, PencilRuler, BookOpen, ListChecks, ClipboardCheck, Camera, ImageOff } from "lucide-react"
import Button from "./ui/Button"
import ExportMenu from "./ExportMenu"

export default function ChatInput({
  question,
  setQuestion,
  onSend,
  onSimplify,
  onExercise,
  onCourse,
  onRemediation,
  onSummary,
  onDownloadSession,
  onPhotoSelected,
  activePhoto,
  onClearActivePhoto,
  canSimplify,
  canExercise,
  canChapterFeatures,
  loading,
  exerciseProgress,
  exportingSession,
  photoLoading,
}) {
  const photoInputRef = useRef(null)

  function handleKeyDown(e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      onSend()
    }
  }

  function handlePhotoChange(e) {
    const file = e.target.files?.[0]
    e.target.value = "" // permet de reprendre la même photo une deuxième fois
    if (file) onPhotoSelected(file)
  }

  return (
    <div className="border-t border-base-300/60 bg-base-100/80 p-3 backdrop-blur-md sm:p-4">
      {activePhoto && (
        <div className="mb-2 flex items-center gap-2 rounded-lg bg-primary/10 px-3 py-1.5 text-xs font-medium text-primary">
          <Camera size={13} />
          Photo active : tes prochains messages continuent sur cet exercice.
          <button
            type="button"
            onClick={onClearActivePhoto}
            className="ml-auto flex items-center gap-1 rounded-md px-1.5 py-0.5 text-primary/80 hover:bg-primary/15 hover:text-primary"
            title="Ne plus tenir compte de cette photo pour la suite"
          >
            <ImageOff size={13} /> Changer de sujet
          </button>
        </div>
      )}
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
          title={!canExercise ? "Choisis une classe pour générer 5 exercices" : "Chapitre non choisi ? Un chapitre adapté sera proposé automatiquement."}
        >
          <PencilRuler size={14} />
          {exerciseProgress ? `Exercice ${exerciseProgress.current}/${exerciseProgress.total}…` : "5 exercices"}
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
        <input
          ref={photoInputRef}
          type="file"
          accept="image/*,application/pdf"
          className="hidden"
          onChange={handlePhotoChange}
        />
        <Button
          variant="outline"
          size="sm"
          onClick={() => photoInputRef.current?.click()}
          disabled={loading || photoLoading}
          title="Prends en photo un exercice (ou choisis une photo/un fichier existant). Astuce : tape une consigne dans le champ ci-dessus avant de cliquer pour l'envoyer avec la photo."
        >
          <Camera size={14} className={photoLoading ? "animate-pulse" : ""} />
          {photoLoading ? "Analyse en cours…" : "Photo / fichier d'exercice"}
        </Button>
        <ExportMenu onExport={onDownloadSession} exporting={exportingSession} label="PDF / Word" align="left" />
        <span className="ml-auto hidden text-sm text-base-content/50 sm:inline">
          Entrée pour envoyer · Maj+Entrée pour une nouvelle ligne
        </span>
      </div>
    </div>
  )
}
