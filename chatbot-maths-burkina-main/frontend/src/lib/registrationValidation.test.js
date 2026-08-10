import { describe, it, expect } from "vitest"
import { emptyProfileFields, validateProfileFields, isProfileFormComplete } from "./registrationValidation.js"

function completeValues(overrides = {}) {
  return {
    ...emptyProfileFields(),
    classCode: "3ème",
    gender: "F",
    birthYear: "2012",
    isCandidatLibre: false,
    schoolName: "École Test",
    region: "Centre",
    ...overrides,
  }
}

describe("emptyProfileFields", () => {
  it("starts with isCandidatLibre unset (null), not silently false", () => {
    // "choix explicite, pas de valeur par défaut silencieuse" — voir le correctif de spécification.
    expect(emptyProfileFields().isCandidatLibre).toBeNull()
  })
})

describe("validateProfileFields", () => {
  it("accepts a fully completed, non-candidat-libre profile", () => {
    expect(validateProfileFields(completeValues())).toEqual({})
    expect(isProfileFormComplete(completeValues())).toBe(true)
  })

  it("requires classCode, gender and birthYear", () => {
    const errors = validateProfileFields(emptyProfileFields())
    expect(errors.classCode).toBeTruthy()
    expect(errors.gender).toBeTruthy()
    expect(errors.birthYear).toBeTruthy()
  })

  it("no longer accepts 'NSP' as a gender value", () => {
    // Retiré du correctif de spécification : le genre est un choix obligatoire à deux valeurs.
    const errors = validateProfileFields(completeValues({ gender: "NSP" }))
    expect(errors.gender).toBeTruthy()
  })

  it("rejects an out-of-range birth year", () => {
    expect(validateProfileFields(completeValues({ birthYear: "1900" })).birthYear).toBeTruthy()
    expect(validateProfileFields(completeValues({ birthYear: "2099" })).birthYear).toBeTruthy()
  })

  it("requires an explicit choice for isCandidatLibre (null is not a valid answer)", () => {
    const errors = validateProfileFields(completeValues({ isCandidatLibre: null }))
    expect(errors.isCandidatLibre).toBeTruthy()
  })

  it("requires schoolName when isCandidatLibre is false", () => {
    const errors = validateProfileFields(completeValues({ isCandidatLibre: false, schoolName: "" }))
    expect(errors.schoolName).toBeTruthy()
  })

  it("does not require schoolName when isCandidatLibre is true", () => {
    const errors = validateProfileFields(completeValues({ isCandidatLibre: true, schoolName: "" }))
    expect(errors.schoolName).toBeUndefined()
    expect(isProfileFormComplete(completeValues({ isCandidatLibre: true, schoolName: "" }))).toBe(true)
  })

  it("rejects a blank (whitespace-only) schoolName the same way as an empty one", () => {
    const errors = validateProfileFields(completeValues({ schoolName: "   " }))
    expect(errors.schoolName).toBeTruthy()
  })
})
