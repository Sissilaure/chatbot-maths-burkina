import React, { useState } from "react"
import { motion, AnimatePresence } from "framer-motion"
import {
  Sigma, User, Lock, LogIn, UserPlus, ArrowRight, AlertCircle, MessageCircleQuestion, Target, TrendingUp,
} from "lucide-react"
import Button from "./ui/Button"
import { cn } from "../lib/utils"
import { login, register } from "../lib/auth"

const TABS = [
  { id: "login", label: "Connexion", icon: LogIn },
  { id: "register", label: "Inscription", icon: UserPlus },
]

const FEATURES = [
  { icon: MessageCircleQuestion, text: "Pose tes questions à tout moment" },
  { icon: Target, text: "Des conseils taillés pour tes lacunes" },
  { icon: TrendingUp, text: "Progresse à ton rythme, du 6ème à la Terminale" },
]

/** Quelques symboles mathématiques en filigrane, très discrets : une touche « maths » légère
 * plutôt qu'une illustration à décoder — juste de la texture, pas un schéma. */
function FloatingGlyphs() {
  const glyphs = [
    { char: "π", top: "8%", left: "72%", size: "5.5rem", delay: 0, anim: "animate-float-slow" },
    { char: "∞", top: "62%", left: "8%", size: "4rem", delay: 0.4, anim: "animate-float-slower" },
    { char: "√", top: "78%", left: "68%", size: "4.5rem", delay: 0.8, anim: "animate-float-slow" },
    { char: "∑", top: "22%", left: "14%", size: "3.5rem", delay: 1.2, anim: "animate-float-slower" },
  ]
  return (
    <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
      {glyphs.map((g, i) => (
        <span
          key={i}
          className={cn("font-heading absolute font-bold text-white/[0.07]", g.anim)}
          style={{ top: g.top, left: g.left, fontSize: g.size }}
        >
          {g.char}
        </span>
      ))}
    </div>
  )
}

export default function AuthGate({ onAuthenticated, onContinueAsGuest }) {
  const [tab, setTab] = useState("login")
  const [username, setUsername] = useState("")
  const [password, setPassword] = useState("")
  const [confirmPassword, setConfirmPassword] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  function switchTab(next) {
    setTab(next)
    setError("")
    setPassword("")
    setConfirmPassword("")
  }

  async function handleSubmit(e) {
    e.preventDefault()
    setError("")

    if (!username.trim() || !password) {
      setError("Renseigne un nom d'utilisateur et un mot de passe.")
      return
    }
    if (tab === "register" && password.length < 6) {
      setError("Le mot de passe doit contenir au moins 6 caractères.")
      return
    }
    if (tab === "register" && password !== confirmPassword) {
      setError("Les deux mots de passe ne correspondent pas.")
      return
    }

    setLoading(true)
    try {
      const session =
        tab === "login" ? await login(username.trim(), password) : await register(username.trim(), password)
      onAuthenticated(session)
    } catch (err) {
      setError(err.message || "Une erreur est survenue.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="grid min-h-screen bg-base-100 text-base-content lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)]">
      {/* Panneau de marque — masqué sur mobile, où le contenu ci-dessous suffit */}
      <div className="relative hidden overflow-hidden bg-gradient-to-br from-[#062b28] via-primary to-secondary lg:flex lg:flex-col lg:justify-between">
        <FloatingGlyphs />

        <div className="relative z-10 p-10">
          <div className="flex items-center gap-2.5">
            <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-white/15 text-white backdrop-blur-sm">
              <Sigma size={18} />
            </div>
            <span className="font-heading text-lg font-bold tracking-tight text-white">Prof Amira</span>
          </div>
        </div>

        <div className="relative z-10 p-10 pt-0">
          <motion.p
            initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
            className="text-[0.7rem] font-semibold uppercase tracking-[0.2em] text-accent"
          >
            Ton prof infatigable
          </motion.p>
          <motion.p
            initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, delay: 0.08 }}
            className="font-heading mt-2 max-w-sm text-[2rem] font-extrabold leading-[1.1] text-white"
          >
            Progresse en maths,{" "}
            <span className="bg-gradient-to-r from-accent via-white to-secondary bg-clip-text italic text-transparent">
              à ton rythme.
            </span>
          </motion.p>
          <motion.p
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.5, delay: 0.2 }}
            className="mt-3 max-w-xs text-[0.95rem] font-light leading-relaxed text-white/70"
          >
            Un compte pour garder ton historique et recevoir des conseils qui te ressemblent.
          </motion.p>

          <div className="mt-7 flex flex-col gap-3">
            {FEATURES.map((f, i) => (
              <motion.div
                key={f.text}
                initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.4, delay: 0.3 + i * 0.1 }}
                className="flex items-center gap-3"
              >
                <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-white/10 text-accent">
                  <f.icon size={15} />
                </span>
                <span className="text-sm text-white/80">{f.text}</span>
              </motion.div>
            ))}
          </div>
        </div>
      </div>

      {/* Panneau de connexion */}
      <div className="flex items-center justify-center px-5 py-12 sm:px-10">
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4, ease: "easeOut" }}
          className="w-full max-w-sm"
        >
          <div className="mb-8 flex flex-col items-start gap-3 lg:hidden">
            <div className="relative flex h-12 w-12 shrink-0 items-center justify-center">
              <span className="absolute inset-0 rounded-2xl bg-primary/50 motion-safe:animate-pulse-ring" />
              <div className="relative flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-primary via-secondary to-accent text-white shadow-glow">
                <Sigma size={22} />
              </div>
            </div>
            <h1 className="font-heading text-2xl font-extrabold leading-tight">
              Prof <span className="text-gradient motion-safe:animate-shimmer">Amira</span>
            </h1>
          </div>

          <p className="font-heading text-[0.7rem] font-bold uppercase tracking-[0.18em] text-primary">
            {tab === "login" ? "Bon retour" : "Bienvenue"}
          </p>
          <h2 className="font-heading mt-1.5 text-[1.65rem] font-extrabold leading-tight text-base-content">
            {tab === "login" ? "Connecte-toi à ton compte" : "Crée ton compte élève"}
          </h2>
          <p className="mt-2 text-[0.95rem] text-base-content/70">
            {tab === "login"
              ? "Retrouve ton historique et tes conseils personnalisés."
              : "Un nom d'utilisateur, un mot de passe, et c'est parti."}
          </p>

          <div className="mt-6 grid grid-cols-2 gap-1.5 rounded-xl border border-base-300 bg-base-200/50 p-1">
            {TABS.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => switchTab(t.id)}
                className={cn(
                  "flex items-center justify-center gap-1.5 rounded-lg py-2 text-sm font-semibold transition-colors",
                  tab === t.id
                    ? "bg-base-100 text-primary shadow-sm ring-1 ring-base-300"
                    : "text-base-content/55 hover:text-base-content"
                )}
              >
                <t.icon size={15} />
                {t.label}
              </button>
            ))}
          </div>

          <form onSubmit={handleSubmit} className="mt-5 flex flex-col gap-4">
            <AnimatePresence mode="wait">
              <motion.div
                key={tab}
                initial={{ opacity: 0, x: tab === "login" ? -8 : 8 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.15 }}
                className="flex flex-col gap-4"
              >
                <label className="flex flex-col gap-1.5">
                  <span className="text-sm font-semibold text-base-content">Nom d'utilisateur</span>
                  <div className="flex items-center gap-2.5 rounded-xl border border-base-300 bg-base-100 px-3.5 py-3 transition-colors focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/15">
                    <User size={17} className="shrink-0 text-base-content/40" />
                    <input
                      className="w-full bg-transparent text-base font-medium text-base-content outline-none placeholder:font-normal placeholder:text-base-content/35"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      placeholder="ex : fatou_ouedraogo"
                      autoComplete="username"
                    />
                  </div>
                </label>

                <label className="flex flex-col gap-1.5">
                  <span className="text-sm font-semibold text-base-content">Mot de passe</span>
                  <div className="flex items-center gap-2.5 rounded-xl border border-base-300 bg-base-100 px-3.5 py-3 transition-colors focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/15">
                    <Lock size={17} className="shrink-0 text-base-content/40" />
                    <input
                      type="password"
                      className="w-full bg-transparent text-base font-medium text-base-content outline-none placeholder:font-normal placeholder:text-base-content/35"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      autoComplete={tab === "login" ? "current-password" : "new-password"}
                    />
                  </div>
                </label>

                {tab === "register" && (
                  <label className="flex flex-col gap-1.5">
                    <span className="text-sm font-semibold text-base-content">Confirme le mot de passe</span>
                    <div className="flex items-center gap-2.5 rounded-xl border border-base-300 bg-base-100 px-3.5 py-3 transition-colors focus-within:border-primary focus-within:ring-2 focus-within:ring-primary/15">
                      <Lock size={17} className="shrink-0 text-base-content/40" />
                      <input
                        type="password"
                        className="w-full bg-transparent text-base font-medium text-base-content outline-none placeholder:font-normal placeholder:text-base-content/35"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        placeholder="••••••••"
                        autoComplete="new-password"
                      />
                    </div>
                  </label>
                )}
              </motion.div>
            </AnimatePresence>

            {error && (
              <div className="flex items-start gap-2 rounded-xl border border-error/30 bg-error/10 px-3.5 py-2.5 text-sm font-medium text-error">
                <AlertCircle size={16} className="mt-0.5 shrink-0" />
                {error}
              </div>
            )}

            <Button type="submit" variant="primary" size="lg" disabled={loading} className="mt-1 w-full font-bold">
              {loading ? "Un instant..." : tab === "login" ? "Se connecter" : "Créer mon compte"}
            </Button>
          </form>

          <button
            type="button"
            onClick={onContinueAsGuest}
            className="mt-5 flex w-full items-center justify-center gap-1.5 text-sm font-semibold text-base-content/60 hover:text-primary"
          >
            Continuer sans compte <ArrowRight size={14} />
          </button>
        </motion.div>
      </div>
    </div>
  )
}
