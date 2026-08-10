/**
 * Validation de la fiche d'inscription (classe/genre/année de naissance/candidat libre/
 * établissement), partagée entre AuthGate.jsx (étape 3 de l'inscription) et
 * ProfileCompletionGate.jsx (comptes migrés qui doivent la compléter à la reconnexion) — pour ne
 * pas dupliquer les règles à deux endroits. Miroir des règles serveur (main.py::RegisterRequest),
 * ce qui permet de désactiver le bouton "Terminer" avant même d'appeler l'API.
 */
const MIN_BIRTH_YEAR = 1950
const MAX_BIRTH_YEAR = 2020
// Deux valeurs seulement, choix obligatoire (pas d'option "préfère ne pas répondre") — voir
// backend/main.py::VALID_GENDERS et la migration backend/migrations/003_gender_two_values.sql.
const VALID_GENDERS = ["F", "M"]

export function emptyProfileFields() {
  return {
    classCode: "",
    gender: "",
    birthYear: "",
    isCandidatLibre: null, // null = pas encore choisi, distinct de false ("choix explicite")
    schoolName: "",
    region: "",
  }
}

export function validateProfileFields(values) {
  const errors = {}

  if (!values.classCode) errors.classCode = "Choisis ta classe."
  if (!values.gender || !VALID_GENDERS.includes(values.gender)) errors.gender = "Choisis une option."

  const year = Number(values.birthYear)
  if (!values.birthYear || !Number.isInteger(year) || year < MIN_BIRTH_YEAR || year > MAX_BIRTH_YEAR) {
    errors.birthYear = `Indique une année entre ${MIN_BIRTH_YEAR} et ${MAX_BIRTH_YEAR}.`
  }

  if (values.isCandidatLibre === null || values.isCandidatLibre === undefined) {
    errors.isCandidatLibre = "Précise si tu es candidat libre."
  } else if (!values.isCandidatLibre && !(values.schoolName && values.schoolName.trim())) {
    errors.schoolName = "Indique ton établissement, ou coche « candidat libre »."
  }

  return errors
}

export function isProfileFormComplete(values) {
  return Object.keys(validateProfileFields(values)).length === 0
}
