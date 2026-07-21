import React from "react"
import { motion } from "framer-motion"
import { Sigma, Moon, Sun, LogIn, LogOut, UserCircle2 } from "lucide-react"
import Button from "./ui/Button"

export default function Header({ theme, onToggleTheme, user, onLoginClick, onLogout }) {
  return (
    <motion.header
      initial={{ opacity: 0, y: -12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: "easeOut" }}
      className="sticky top-0 z-20 flex items-center justify-between border-b border-base-300/60 bg-base-100/70 px-4 py-3 backdrop-blur-md sm:px-6"
    >
      <div className="flex items-center gap-3">
        <div className="relative flex h-10 w-10 shrink-0 items-center justify-center">
          <span className="absolute inset-0 rounded-xl bg-primary/50 motion-safe:animate-pulse-ring" />
          <div className="relative flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary via-secondary to-accent text-white shadow-glow">
            <Sigma size={20} />
          </div>
        </div>
        <div>
          <h1 className="font-heading text-lg font-extrabold leading-tight">
            Prof <span className="text-gradient motion-safe:animate-shimmer">Amira</span>
          </h1>
          <p className="text-sm text-base-content/60">Ton copain de maths, toujours prêt à t'aider</p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {user ? (
          <div className="flex items-center gap-1.5">
            <span className="hidden items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1.5 text-sm font-medium text-primary sm:flex">
              <UserCircle2 size={15} />
              {user}
            </span>
            <Button variant="ghost" size="icon" onClick={onLogout} title="Se déconnecter">
              <LogOut size={17} />
            </Button>
          </div>
        ) : (
          <Button variant="outline" size="sm" onClick={onLoginClick}>
            <LogIn size={14} /> Se connecter
          </Button>
        )}

        <Button variant="ghost" size="icon" onClick={onToggleTheme} title="Changer de thème">
          {theme === "chatmaths-dark" ? <Sun size={18} /> : <Moon size={18} />}
        </Button>
      </div>
    </motion.header>
  )
}
