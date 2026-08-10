import React, { useEffect, useState } from "react"
import { GraduationCap, MapPin } from "lucide-react"
import { getClasses } from "../api.js"
import SchoolAutocomplete from "./SchoolAutocomplete.jsx"
import { cn } from "../lib/utils"

// Deux valeurs, choix obligatoire — pas d'option "préfère ne pas répondre" (voir
// backend/main.py::VALID_GENDERS et backend/migrations/003_gender_two_values.sql).
const GENDER_OPTIONS = [
  { value: "F", label: "Féminin" },
  { value: "M", label: "Masculin" },
]

const fieldWrapClass = (hasError) =>
  cn(
    "flex items-center gap-2.5 rounded-xl border bg-base-100 px-3.5 py-3 transition-colors focus-within:ring-2 focus-within:ring-primary/15",
    hasError ? "border-error focus-within:border-error" : "border-base-300 focus-within:border-primary"
  )

/**
 * Fiche d'inscription : classe, genre, année de naissance, statut candidat libre, établissement
 * (masqué si candidat libre), région. Tous obligatoires sauf établissement/région pour un
 * candidat libre (voir main.py::RegisterRequest). Composant purement contrôlé : `values`/`onChange`
 * portent l'état, `errors` les messages par champ (affichés SOUS le champ concerné, pas groupés
 * en haut) — réutilisé tel quel par AuthGate (étape 3 de l'inscription) et par
 * ProfileCompletionGate (comptes migrés).
 */
export default function RegistrationDetails({ values, onChange, errors = {} }) {
  const [classes, setClasses] = useState([])

  useEffect(() => {
    let cancelled = false
    getClasses()
      .then((list) => {
        if (!cancelled) setClasses(list)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [])

  function set(field, value) {
    onChange({ [field]: value })
  }

  function setCandidatLibre(isCandidatLibre) {
    // "Si l'utilisateur avait saisi une école puis coche candidat libre, la saisie est effacée
    // de l'état, pas conservée en arrière-plan" — on vide explicitement schoolName ici plutôt
    // que de simplement masquer le champ.
    onChange({ isCandidatLibre, schoolName: isCandidatLibre ? "" : values.schoolName })
  }

  return (
    <div className="flex flex-col gap-4">
      <label className="flex flex-col gap-1.5">
        <span className="text-sm font-semibold text-base-content">Classe</span>
        <div className={fieldWrapClass(errors.classCode)}>
          <GraduationCap size={17} className="shrink-0 text-base-content/40" />
          <select
            className="w-full bg-transparent text-base font-medium text-base-content outline-none"
            value={values.classCode}
            onChange={(e) => set("classCode", e.target.value)}
          >
            <option value="" disabled>
              Choisis ta classe
            </option>
            {classes.map((c) => (
              <option key={c.code} value={c.code}>
                {c.name}
              </option>
            ))}
          </select>
        </div>
        {errors.classCode && <span className="text-sm font-medium text-error">{errors.classCode}</span>}
      </label>

      <fieldset className="flex flex-col gap-2">
        <legend className="text-sm font-semibold text-base-content">Genre</legend>
        <div className="grid grid-cols-2 gap-2">
          {GENDER_OPTIONS.map((g) => (
            <label
              key={g.value}
              className={cn(
                "flex cursor-pointer items-center justify-center gap-2 rounded-xl border px-3.5 py-2.5 text-sm font-medium transition-colors",
                values.gender === g.value
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-base-300 text-base-content/70 hover:bg-base-200"
              )}
            >
              <input
                type="radio"
                name="gender"
                className="radio radio-sm radio-primary"
                checked={values.gender === g.value}
                onChange={() => set("gender", g.value)}
              />
              {g.label}
            </label>
          ))}
        </div>
        {errors.gender && <span className="text-sm font-medium text-error">{errors.gender}</span>}
      </fieldset>

      <label className="flex flex-col gap-1.5">
        <span className="text-sm font-semibold text-base-content">Année de naissance</span>
        <div className={fieldWrapClass(errors.birthYear)}>
          <input
            type="number"
            inputMode="numeric"
            className="w-full bg-transparent text-base font-medium text-base-content outline-none placeholder:font-normal placeholder:text-base-content/35"
            value={values.birthYear}
            onChange={(e) => set("birthYear", e.target.value)}
            placeholder="ex : 2010"
            min={1950}
            max={2020}
          />
        </div>
        {errors.birthYear && <span className="text-sm font-medium text-error">{errors.birthYear}</span>}
      </label>

      <fieldset className="flex flex-col gap-2">
        <legend className="text-sm font-semibold text-base-content">Es-tu candidat libre ?</legend>
        <div className="grid grid-cols-2 gap-2">
          {[
            { value: false, label: "Non, inscrit(e) dans un établissement" },
            { value: true, label: "Oui, candidat libre" },
          ].map((opt) => (
            <label
              key={String(opt.value)}
              className={cn(
                "flex cursor-pointer items-center gap-2 rounded-xl border px-3.5 py-2.5 text-sm font-medium transition-colors",
                values.isCandidatLibre === opt.value
                  ? "border-primary bg-primary/10 text-primary"
                  : "border-base-300 text-base-content/70 hover:bg-base-200"
              )}
            >
              <input
                type="radio"
                name="isCandidatLibre"
                className="radio radio-sm radio-primary"
                checked={values.isCandidatLibre === opt.value}
                onChange={() => setCandidatLibre(opt.value)}
              />
              {opt.label}
            </label>
          ))}
        </div>
        {errors.isCandidatLibre && <span className="text-sm font-medium text-error">{errors.isCandidatLibre}</span>}
      </fieldset>

      {!values.isCandidatLibre && (
        <SchoolAutocomplete
          value={values.schoolName}
          onChange={(v) => set("schoolName", v)}
          error={errors.schoolName}
        />
      )}

      <label className="flex flex-col gap-1.5">
        <span className="text-sm font-semibold text-base-content">Région (facultatif)</span>
        <div className={fieldWrapClass(false)}>
          <MapPin size={17} className="shrink-0 text-base-content/40" />
          <input
            className="w-full bg-transparent text-base font-medium text-base-content outline-none placeholder:font-normal placeholder:text-base-content/35"
            value={values.region}
            onChange={(e) => set("region", e.target.value)}
            placeholder="ex : Centre"
          />
        </div>
      </label>
    </div>
  )
}
