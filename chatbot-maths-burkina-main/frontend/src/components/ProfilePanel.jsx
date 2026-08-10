import React from "react"
import { UserRound, History, AlertCircle, X } from "lucide-react"
import Card from "./ui/Card"
import Button from "./ui/Button"

function timeAgo(timestamp) {
  const diffMin = Math.round((Date.now() - timestamp) / 60000)
  if (diffMin < 1) return "à l'instant"
  if (diffMin < 60) return `il y a ${diffMin} min`
  const diffH = Math.round(diffMin / 60)
  if (diffH < 24) return `il y a ${diffH} h`
  const diffJ = Math.round(diffH / 24)
  return `il y a ${diffJ} j`
}

export default function ProfilePanel({ profile, onResumeTopic, onReviewStruggle, onDismissStruggle }) {
  const { topics = [], struggles = [] } = profile || {}

  if (topics.length === 0 && struggles.length === 0) return null

  return (
    <Card className="p-4">
      <label className="font-heading mb-2 flex items-center gap-2 text-sm font-semibold text-base-content/80">
        <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-primary/15 text-primary">
          <UserRound size={13} />
        </span>
        Ton profil
      </label>

      {topics.length > 0 && (
        <div className="mb-3">
          <p className="mb-1.5 flex items-center gap-1 text-sm font-medium text-base-content/60">
            <History size={12} /> Reprendre où tu en étais
          </p>
          <div className="flex flex-col gap-1.5">
            {topics.slice(0, 4).map((t) => (
              <button
                key={t.key}
                onClick={() => onResumeTopic(t)}
                className="rounded-lg border border-base-300/60 bg-base-100 px-3 py-2 text-left text-sm transition-colors hover:border-primary/50 hover:bg-primary/5"
                // database.get_recent_topics (Postgres) ne fournit plus de compteur de visites
                // (contrairement à l'ancien schéma SQLite) : on n'affiche que la fraîcheur.
                title={`Dernière visite ${timeAgo(t.lastVisited)}`}
              >
                <span className="font-medium">{t.classeNom || t.classCode || "Classe libre"}</span>
                {t.chapitre && <span className="text-base-content/60"> · {t.chapitre}</span>}
              </button>
            ))}
          </div>
        </div>
      )}

      {struggles.length > 0 && (
        <div>
          <p className="mb-1.5 flex items-center gap-1 text-sm font-medium text-base-content/60">
            <AlertCircle size={12} /> Notions à revoir
          </p>
          <div className="flex flex-col gap-1.5">
            {struggles.slice(0, 5).map((s, i) => (
              <div
                key={`${s.timestamp}-${i}`}
                className="flex items-start gap-1.5 rounded-lg border border-warning/30 bg-warning/5 px-3 py-2 text-sm"
              >
                <button
                  onClick={() => onReviewStruggle(s)}
                  className="flex-1 text-left leading-snug hover:underline"
                  title="Reposer cette question"
                >
                  {s.chapitre && <span className="font-medium">{s.chapitre} : </span>}
                  {s.question}
                </button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="!p-1"
                  title="Retiré de la liste"
                  onClick={() => onDismissStruggle(i)}
                >
                  <X size={12} />
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}
    </Card>
  )
}
