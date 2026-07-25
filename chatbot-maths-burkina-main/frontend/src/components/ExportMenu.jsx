import React, { useState } from "react"
import { FileDown, FileText, ChevronDown } from "lucide-react"
import Button from "./ui/Button"

/**
 * Bouton "Télécharger" avec un petit menu pour choisir le format (PDF ou Word).
 * Se ferme automatiquement quand le focus quitte le composant (clic ailleurs, Échap+Tab...).
 */
export default function ExportMenu({ onExport, exporting, label = "Télécharger", align = "right" }) {
  const [open, setOpen] = useState(false)

  return (
    <div
      className="relative"
      tabIndex={-1}
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget)) setOpen(false)
      }}
    >
      <Button
        variant="soft"
        size="sm"
        onClick={() => setOpen((o) => !o)}
        disabled={exporting}
        title="Télécharger toute la conversation (PDF ou Word)"
      >
        <FileDown size={14} className={exporting ? "animate-pulse" : ""} />
        {exporting ? "Génération…" : label}
        <ChevronDown size={12} className={`transition-transform ${open ? "rotate-180" : ""}`} />
      </Button>
      {open && (
        <div
          className={`absolute z-20 mt-1 w-44 overflow-hidden rounded-xl border border-base-300 bg-base-100 shadow-lg ${
            align === "right" ? "right-0" : "left-0"
          }`}
        >
          <button
            type="button"
            className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-base-200"
            onClick={() => {
              setOpen(false)
              onExport("pdf")
            }}
          >
            <FileDown size={14} /> PDF
          </button>
          <button
            type="button"
            className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-base-200"
            onClick={() => {
              setOpen(false)
              onExport("docx")
            }}
          >
            <FileText size={14} /> Word (.docx)
          </button>
        </div>
      )}
    </div>
  )
}
