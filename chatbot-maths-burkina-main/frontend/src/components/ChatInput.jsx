import React, { useEffect, useRef, useState } from "react"
import {
  SendHorizontal, PencilRuler, BookOpen, ListChecks, ClipboardCheck, Camera, ImageOff,
  MoreHorizontal, FileDown, FileText, GraduationCap,
} from "lucide-react"
import Button from "./ui/Button"
import ExportMenu from "./ExportMenu"
import BottomSheet from "./ui/BottomSheet"
import { useIsMobile } from "../lib/useMediaQuery"

// Hauteur automatique du textarea : une ligne au repos, jusqu'à 4 lignes maximum, pas de barre
// de défilement visible avant cette limite (voir RAPPORT_MOBILE.md §6).
const TEXTAREA_MAX_LINES = 4

function useAutoResizeTextarea(value) {
  const ref = useRef(null)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = "auto"
    const styles = getComputedStyle(el)
    const lineHeight = parseFloat(styles.lineHeight) || 24
    const verticalPadding = parseFloat(styles.paddingTop) + parseFloat(styles.paddingBottom) || 0
    const verticalBorder = parseFloat(styles.borderTopWidth) + parseFloat(styles.borderBottomWidth) || 0
    const maxHeight = lineHeight * TEXTAREA_MAX_LINES + verticalPadding + verticalBorder
    const next = Math.min(el.scrollHeight, maxHeight)
    el.style.height = `${next}px`
    el.style.overflowY = el.scrollHeight > maxHeight ? "auto" : "hidden"
  }, [value])
  return ref
}

/** Une entrée de la feuille "⋯" (mobile) : cible large (min 44px), icône + libellé + description
 * facultative, désactivée avec la même logique que le bouton bureau équivalent. */
function SheetAction({ icon: Icon, label, hint, onClick, disabled }) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={hint}
      className="flex min-h-[44px] w-full items-center gap-3 rounded-xl px-3 py-3 text-left text-sm font-medium text-base-content transition-colors hover:bg-base-200 disabled:opacity-40"
    >
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-primary/10 text-primary">
        <Icon size={16} />
      </span>
      <span className="min-w-0 flex-1">
        <span className="block">{label}</span>
        {hint && <span className="block truncate text-xs font-normal text-base-content/50">{hint}</span>}
      </span>
    </button>
  )
}

/** Pastille compacte classe/chapitre au-dessus du champ de saisie (mobile) : ouvre l'onglet
 * Réglages de la sidebar au clic, voir RAPPORT_MOBILE.md §5. */
function InfoPill({ text, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex min-h-[32px] items-center gap-1 rounded-full border border-base-300/70 bg-base-100 px-2.5 py-1 text-xs font-medium text-base-content/70"
    >
      <GraduationCap size={11} />
      <span className="max-w-[38vw] truncate">{text}</span>
    </button>
  )
}

export default function ChatInput({
  question,
  setQuestion,
  onSend,
  onExercise,
  onCourse,
  onRemediation,
  onSummary,
  onDownloadSession,
  onPhotoSelected,
  activePhoto,
  onClearActivePhoto,
  canExercise,
  canChapterFeatures,
  loading,
  exerciseProgress,
  exportingSession,
  photoLoading,
  classeNom,
  chapitre,
  onOpenSettings,
}) {
  const photoInputRef = useRef(null)
  const isMobile = useIsMobile()
  const [sheetOpen, setSheetOpen] = useState(false)
  const textareaRef = useAutoResizeTextarea(question)

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

  function runFromSheet(action) {
    setSheetOpen(false)
    action()
  }

  const exerciseLabel = exerciseProgress ? `Exercice ${exerciseProgress.current}/${exerciseProgress.total}…` : "5 exercices"

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

      {/* Pastilles classe/chapitre : uniquement sur mobile, où la sidebar (et donc ce contexte)
          n'est pas visible en permanence — voir RAPPORT_MOBILE.md §5. */}
      {isMobile && (classeNom || chapitre) && (
        <div className="mb-2 flex items-center gap-1.5">
          <InfoPill text={classeNom || "Classe"} onClick={onOpenSettings} />
          {chapitre && <InfoPill text={chapitre} onClick={onOpenSettings} />}
        </div>
      )}

      <div className="flex items-end gap-2">
        {isMobile && (
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSheetOpen(true)}
            title="Plus d'actions"
            className="min-h-[44px] min-w-[44px] shrink-0"
          >
            <MoreHorizontal size={20} />
          </Button>
        )}

        <input
          ref={photoInputRef}
          type="file"
          accept="image/*,application/pdf"
          className="hidden"
          onChange={handlePhotoChange}
        />
        {/* Bouton photo/fichier : visible en permanence à côté du champ sur mobile (voir
            RAPPORT_MOBILE.md §5) ; sur bureau il reste dans la barre d'outils inchangée
            ci-dessous, avec son libellé texte. */}
        {isMobile && (
          <Button
            variant="outline"
            size="icon"
            onClick={() => photoInputRef.current?.click()}
            disabled={loading || photoLoading}
            title="Prends en photo un exercice (ou choisis une photo/un fichier existant). Astuce : tape une consigne dans le champ ci-dessus avant de cliquer pour l'envoyer avec la photo."
            className="min-h-[44px] min-w-[44px] shrink-0"
          >
            <Camera size={18} className={photoLoading ? "animate-pulse" : ""} />
          </Button>
        )}

        <textarea
          ref={textareaRef}
          className="textarea textarea-bordered w-full flex-1 resize-none rounded-xl bg-base-100 text-base leading-6"
          rows={1}
          placeholder="Pose ta question"
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
          className="min-h-[44px] min-w-[44px] shrink-0"
        >
          <SendHorizontal size={18} />
        </Button>
      </div>

      {/* Bureau (>=768px) : barre d'outils inline inchangée, hors "Simplifie" (déplacé sous
          chaque réponse, voir MessageBubble.jsx). Mobile : ces actions vivent dans la feuille
          "⋯" ouverte ci-dessus, voir plus bas. */}
      <div className="mt-2 hidden flex-wrap items-center gap-2 md:flex">
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
        <Button
          variant="outline"
          size="sm"
          onClick={onExercise}
          disabled={!canExercise || loading}
          title={!canExercise ? "Choisis une classe pour générer 5 exercices" : "Chapitre non choisi ? Un chapitre adapté sera proposé automatiquement."}
        >
          <PencilRuler size={14} />
          {exerciseLabel}
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
        <span className="ml-auto hidden text-sm text-base-content/50 lg:inline">
          Entrée pour envoyer · Maj+Entrée pour une nouvelle ligne
        </span>
      </div>

      <BottomSheet open={sheetOpen} onClose={() => setSheetOpen(false)} title="Plus d'actions">
        <div className="flex flex-col gap-1">
          <SheetAction
            icon={PencilRuler}
            label={exerciseProgress ? exerciseLabel : "Un exercice"}
            hint={!canExercise ? "Choisis une classe pour générer un exercice" : "Chapitre non choisi ? Un chapitre adapté sera proposé automatiquement."}
            onClick={() => runFromSheet(onExercise)}
            disabled={!canExercise || loading}
          />
          <SheetAction
            icon={ClipboardCheck}
            label="Test de remédiation"
            hint={!canChapterFeatures ? "Choisis une classe et un chapitre" : "QCM diagnostique sur ce chapitre"}
            onClick={() => runFromSheet(onRemediation)}
            disabled={!canChapterFeatures || loading}
          />
          <SheetAction
            icon={BookOpen}
            label="Voir le cours"
            hint={!canChapterFeatures ? "Choisis une classe et un chapitre" : "Ouvrir le document de cours de ce chapitre"}
            onClick={() => runFromSheet(onCourse)}
            disabled={!canChapterFeatures || loading}
          />
          <SheetAction
            icon={ListChecks}
            label="Résumé de la séance"
            onClick={() => runFromSheet(onSummary)}
            disabled={loading}
          />

          <div className="my-2 border-t border-base-300/60" />

          <p className="px-3 pb-1 text-xs font-semibold uppercase tracking-wide text-base-content/40">Télécharger</p>
          <SheetAction
            icon={FileDown}
            label="PDF"
            onClick={() => runFromSheet(() => onDownloadSession("pdf"))}
            disabled={exportingSession}
          />
          <SheetAction
            icon={FileText}
            label="Word (.docx)"
            onClick={() => runFromSheet(() => onDownloadSession("docx"))}
            disabled={exportingSession}
          />
        </div>
      </BottomSheet>
    </div>
  )
}
