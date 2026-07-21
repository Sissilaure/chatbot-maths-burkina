import React from "react"
import { motion } from "framer-motion"
import { History, MessageSquare, Trash2, Plus } from "lucide-react"
import Card from "./ui/Card"
import Button from "./ui/Button"
import { cn } from "../lib/utils"

function formatDate(sqliteDatetime) {
  if (!sqliteDatetime) return ""
  const date = new Date(sqliteDatetime.replace(" ", "T") + "Z")
  if (Number.isNaN(date.getTime())) return ""
  const today = new Date()
  const sameDay = date.toDateString() === today.toDateString()
  return sameDay
    ? date.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })
    : date.toLocaleDateString("fr-FR", { day: "2-digit", month: "short" })
}

export default function ConversationList({ conversations, activeConversationId, onSelect, onDelete, onNew }) {
  return (
    <Card className="p-4">
      <div className="mb-2 flex items-center justify-between">
        <label className="font-heading flex items-center gap-2 text-sm font-semibold text-base-content/80">
          <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-primary/15 text-primary">
            <History size={13} />
          </span>
          Historique
        </label>
        <Button variant="ghost" size="icon" onClick={onNew} title="Nouvelle conversation">
          <Plus size={16} />
        </Button>
      </div>

      {conversations.length === 0 ? (
        <p className="text-sm text-base-content/50">Aucune conversation enregistrée pour l'instant.</p>
      ) : (
        <div className="flex max-h-64 flex-col gap-1 overflow-y-auto scrollbar-thin">
          {conversations.map((c) => (
            <motion.div
              key={c.id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className={cn(
                "group flex items-center gap-2 rounded-lg px-2.5 py-2 text-left text-sm transition-colors",
                c.id === activeConversationId ? "bg-primary/10 text-primary" : "hover:bg-base-200"
              )}
            >
              <button onClick={() => onSelect(c.id)} className="flex min-w-0 flex-1 items-center gap-2 text-left">
                <MessageSquare size={14} className="shrink-0 opacity-60" />
                <span className="min-w-0 flex-1 truncate">{c.title || "Discussion libre"}</span>
                <span className="shrink-0 text-xs text-base-content/40">{formatDate(c.updated_at)}</span>
              </button>
              <button
                onClick={() => onDelete(c.id)}
                title="Supprimer cette conversation"
                className="shrink-0 rounded-md p-1 text-base-content/30 opacity-0 transition-opacity hover:bg-error/10 hover:text-error group-hover:opacity-100"
              >
                <Trash2 size={13} />
              </button>
            </motion.div>
          ))}
        </div>
      )}
    </Card>
  )
}
