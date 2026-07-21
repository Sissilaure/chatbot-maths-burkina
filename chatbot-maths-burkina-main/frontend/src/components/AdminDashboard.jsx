import React, { useEffect, useMemo, useState } from "react"
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from "recharts"
import { Sigma, Users, ClipboardCheck, TrendingUp, LogOut, Moon, Sun, AlertTriangle } from "lucide-react"
import Card from "./ui/Card"
import Button from "./ui/Button"
import {
  getClasses, getAdminOverview, getAdminSuccessByChapter, getAdminWeakNotions, getAdminTrend, getAdminActivity,
} from "../api.js"

// Couleurs exactes des thèmes DaisyUI de l'appli (tailwind.config.js) : recharts a besoin de
// valeurs hex littérales, donc on ne peut pas se contenter des classes Tailwind ici.
const PALETTES = {
  "chatmaths-light": {
    primary: "#0d9488", secondary: "#0891b2", success: "#16a34a", warning: "#d97706", error: "#dc2626",
    text: "#1f2937", muted: "#64748b", grid: "#e1f1ee", surface: "#ffffff",
  },
  "chatmaths-dark": {
    primary: "#2dd4bf", secondary: "#22d3ee", success: "#4ade80", warning: "#fbbf24", error: "#f87171",
    text: "#e5e7eb", muted: "#94a3b8", grid: "#17302c", surface: "#0b1615",
  },
}

const MONTHS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."]

function formatMonth(month) {
  if (!month) return ""
  const [year, m] = month.split("-")
  return `${MONTHS[parseInt(m, 10) - 1]} ${year}`
}

function statusColor(rate, palette) {
  if (rate >= 75) return palette.success
  if (rate >= 50) return palette.warning
  return palette.error
}

function StatTile({ icon: Icon, label, value, accent }) {
  return (
    <Card className="p-4">
      <div className="mb-2 flex items-center gap-2 text-base-content/60">
        <span className={`flex h-7 w-7 items-center justify-center rounded-lg ${accent}`}>
          <Icon size={14} />
        </span>
        <span className="text-sm font-medium">{label}</span>
      </div>
      <p className="font-heading text-2xl font-bold text-base-content">{value}</p>
    </Card>
  )
}

function ChartTooltip({ active, payload, label, unit = "" }) {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-lg border border-base-300 bg-base-100 px-3 py-2 text-sm shadow-lg">
      <p className="mb-1 font-semibold text-base-content">{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} className="text-base-content/70">
          {p.name} : <span className="font-semibold text-base-content">{Math.round(p.value)}{unit}</span>
        </p>
      ))}
    </div>
  )
}

function EmptyState({ text }) {
  return <p className="py-8 text-center text-sm text-base-content/50">{text}</p>
}

export default function AdminDashboard({ token, username, theme, onToggleTheme, onLogout }) {
  const palette = PALETTES[theme] || PALETTES["chatmaths-light"]

  const [classes, setClasses] = useState([])
  const [classLevel, setClassLevel] = useState("")
  const [overview, setOverview] = useState(null)
  const [chapters, setChapters] = useState([])
  const [weakNotions, setWeakNotions] = useState([])
  const [trend, setTrend] = useState([])
  const [activity, setActivity] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getClasses().then(setClasses).catch(() => {})
  }, [])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    Promise.all([
      getAdminOverview(token),
      getAdminSuccessByChapter(token, classLevel),
      getAdminWeakNotions(token, classLevel),
      getAdminTrend(token, classLevel),
      getAdminActivity(token, classLevel),
    ])
      .then(([ov, ch, wn, tr, act]) => {
        if (cancelled) return
        setOverview(ov)
        setChapters(ch)
        setWeakNotions(wn)
        setTrend(tr.map((t) => ({ ...t, label: formatMonth(t.month) })))
        setActivity(act.map((a) => ({ ...a, label: formatMonth(a.month) })))
      })
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [token, classLevel])

  const chapterData = useMemo(
    () => chapters.map((c) => ({ ...c, label: c.chapter, rate: Math.round(c.success_rate) })),
    [chapters]
  )

  return (
    <div className="min-h-screen bg-base-200 text-base-content">
      <header className="sticky top-0 z-20 flex items-center justify-between border-b border-base-300/60 bg-base-100/80 px-4 py-3 backdrop-blur-md sm:px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary via-secondary to-accent text-white shadow-glow">
            <Sigma size={20} />
          </div>
          <div>
            <h1 className="font-heading text-lg font-extrabold leading-tight">
              Prof <span className="text-gradient">Amira</span> · Tableau de bord
            </h1>
            <p className="text-sm text-base-content/60">Statistiques agrégées, aucune donnée nominative</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className="hidden items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1.5 text-sm font-medium text-primary sm:flex">
            {username}
          </span>
          <Button variant="ghost" size="icon" onClick={onToggleTheme} title="Changer de thème">
            {theme === "chatmaths-dark" ? <Sun size={18} /> : <Moon size={18} />}
          </Button>
          <Button variant="ghost" size="icon" onClick={onLogout} title="Se déconnecter">
            <LogOut size={17} />
          </Button>
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-5 p-4 sm:p-6">
        <div className="flex items-center gap-3">
          <label className="text-sm font-medium text-base-content/70">Classe</label>
          <select
            className="select select-bordered select-sm rounded-lg bg-base-100"
            value={classLevel}
            onChange={(e) => setClassLevel(e.target.value)}
          >
            <option value="">Toutes les classes</option>
            {classes.map((c) => (
              <option key={c.code} value={c.code}>{c.name}</option>
            ))}
          </select>
        </div>

        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatTile
            icon={Users} label="Élèves actifs (30 jours)" accent="bg-primary/15 text-primary"
            value={overview ? overview.active_students : "—"}
          />
          <StatTile
            icon={ClipboardCheck} label="Remédiations complétées" accent="bg-secondary/15 text-secondary"
            value={overview ? overview.remediations_completed : "—"}
          />
          <StatTile
            icon={TrendingUp} label="Taux de réussite global" accent="bg-success/15 text-success"
            value={overview ? `${Math.round(overview.success_rate)}%` : "—"}
          />
          <StatTile
            icon={AlertTriangle} label="Notions distinctes travaillées" accent="bg-accent/15 text-accent"
            value={chapters.length ? chapters.length : "—"}
          />
        </div>

        <Card className="p-5">
          <h2 className="font-heading mb-1 text-base font-semibold">Évolution du taux de réussite</h2>
          <p className="mb-4 text-sm text-base-content/60">Résultats aux QCM de remédiation, par mois</p>
          {!loading && trend.length === 0 ? (
            <EmptyState text="Pas encore assez de données de remédiation pour tracer une tendance." />
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <LineChart data={trend} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
                <CartesianGrid stroke={palette.grid} vertical={false} />
                <XAxis dataKey="label" tick={{ fill: palette.muted, fontSize: 12 }} axisLine={{ stroke: palette.grid }} tickLine={false} />
                <YAxis
                  domain={[0, 100]} tick={{ fill: palette.muted, fontSize: 12 }} axisLine={false} tickLine={false}
                  tickFormatter={(v) => `${v}%`}
                />
                <Tooltip content={<ChartTooltip unit="%" />} />
                <Line
                  type="monotone" dataKey="success_rate" name="Réussite" stroke={palette.primary} strokeWidth={2}
                  dot={{ r: 4, fill: palette.primary, stroke: palette.surface, strokeWidth: 2 }} activeDot={{ r: 6 }}
                />
              </LineChart>
            </ResponsiveContainer>
          )}
        </Card>

        <div className="grid gap-5 lg:grid-cols-2">
          <Card className="p-5">
            <h2 className="font-heading mb-1 text-base font-semibold">Réussite par chapitre</h2>
            <p className="mb-4 text-sm text-base-content/60">Vert ≥ 75% · Orange 50-75% · Rouge &lt; 50%</p>
            {!loading && chapterData.length === 0 ? (
              <EmptyState text="Aucune remédiation complétée pour l'instant." />
            ) : (
              <ResponsiveContainer width="100%" height={Math.max(220, chapterData.length * 34)}>
                <BarChart data={chapterData} layout="vertical" margin={{ top: 0, right: 24, bottom: 0, left: 0 }}>
                  <CartesianGrid stroke={palette.grid} horizontal={false} />
                  <XAxis type="number" domain={[0, 100]} tick={{ fill: palette.muted, fontSize: 12 }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}%`} />
                  <YAxis type="category" dataKey="label" width={110} tick={{ fill: palette.text, fontSize: 12 }} axisLine={false} tickLine={false} />
                  <Tooltip content={<ChartTooltip unit="%" />} />
                  <Bar dataKey="rate" name="Réussite" radius={[0, 4, 4, 0]} maxBarSize={20}>
                    {chapterData.map((c, i) => (
                      <Cell key={i} fill={statusColor(c.rate, palette)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            )}
          </Card>

          <Card className="p-5">
            <h2 className="font-heading mb-1 text-base font-semibold">Notions les plus fragiles</h2>
            <p className="mb-4 text-sm text-base-content/60">Nombre de réponses ratées, toutes classes confondues</p>
            {!loading && weakNotions.length === 0 ? (
              <EmptyState text="Aucune lacune récurrente identifiée pour l'instant." />
            ) : (
              <ResponsiveContainer width="100%" height={Math.max(220, weakNotions.length * 34)}>
                <BarChart data={weakNotions} layout="vertical" margin={{ top: 0, right: 24, bottom: 0, left: 0 }}>
                  <CartesianGrid stroke={palette.grid} horizontal={false} />
                  <XAxis type="number" allowDecimals={false} tick={{ fill: palette.muted, fontSize: 12 }} axisLine={false} tickLine={false} />
                  <YAxis type="category" dataKey="notion" width={140} tick={{ fill: palette.text, fontSize: 12 }} axisLine={false} tickLine={false} />
                  <Tooltip content={<ChartTooltip />} />
                  <Bar dataKey="wrong_count" name="Échecs" fill={palette.warning} radius={[0, 4, 4, 0]} maxBarSize={20} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </Card>
        </div>

        <Card className="p-5">
          <h2 className="font-heading mb-1 text-base font-semibold">Activité</h2>
          <p className="mb-4 text-sm text-base-content/60">Nombre de conversations démarrées, par mois</p>
          {!loading && activity.length === 0 ? (
            <EmptyState text="Aucune conversation enregistrée pour l'instant." />
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={activity} margin={{ top: 8, right: 12, bottom: 0, left: -12 }}>
                <CartesianGrid stroke={palette.grid} vertical={false} />
                <XAxis dataKey="label" tick={{ fill: palette.muted, fontSize: 12 }} axisLine={{ stroke: palette.grid }} tickLine={false} />
                <YAxis allowDecimals={false} tick={{ fill: palette.muted, fontSize: 12 }} axisLine={false} tickLine={false} />
                <Tooltip content={<ChartTooltip />} />
                <Bar dataKey="conversations" name="Conversations" fill={palette.secondary} radius={[4, 4, 0, 0]} maxBarSize={28} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </Card>
      </main>
    </div>
  )
}
