import { describe, it, expect } from "vitest"
import { stripFigureBlocks, splitBoldSegments, parseMarkdownLines, qcmToLines } from "./docxModel.js"

describe("stripFigureBlocks", () => {
  it("replaces a ```figure``` block with a textual placeholder", () => {
    const input = 'Avant\n```figure\n{"points":[]}\n```\nAprès'
    const result = stripFigureBlocks(input)
    expect(result).not.toContain("```figure")
    expect(result).toContain("Figure géométrique")
    expect(result).toContain("Avant")
    expect(result).toContain("Après")
  })

  it("leaves text without figure blocks untouched", () => {
    expect(stripFigureBlocks("Texte normal")).toBe("Texte normal")
  })
})

describe("splitBoldSegments", () => {
  it("splits **bold** markers into flagged segments, in order", () => {
    expect(splitBoldSegments("Le **théorème de Pythagore** dit que...")).toEqual([
      { text: "Le ", bold: false },
      { text: "théorème de Pythagore", bold: true },
      { text: " dit que...", bold: false },
    ])
  })

  it("returns a single non-bold segment when there is no markdown", () => {
    expect(splitBoldSegments("Rien de gras ici")).toEqual([{ text: "Rien de gras ici", bold: false }])
  })
})

describe("parseMarkdownLines", () => {
  it("classifies headings, bullets, blank lines and plain text", () => {
    const text = "## Titre\nUn paragraphe.\n- Premier point\n\n### Sous-titre"
    expect(parseMarkdownLines(text)).toEqual([
      { type: "heading2", segments: [{ text: "Titre", bold: false }] },
      { type: "text", segments: [{ text: "Un paragraphe.", bold: false }] },
      { type: "bullet", segments: [{ text: "Premier point", bold: false }] },
      { type: "blank", segments: [] },
      { type: "heading3", segments: [{ text: "Sous-titre", bold: false }] },
    ])
  })

  it("replaces figure blocks before splitting into lines", () => {
    const lines = parseMarkdownLines('```figure\n{}\n```')
    expect(lines.some((l) => l.segments.some((s) => s.text.includes("Figure géométrique")))).toBe(true)
  })
})

describe("qcmToLines", () => {
  it("produces a question line, one choice line per option (marking the correct one), and an explication line", () => {
    const questions = [
      {
        question: "Combien font 2+2 ?",
        choix: ["3", "4", "5"],
        reponse_correcte_index: 1,
        explication: "2+2 = 4",
      },
    ]
    const lines = qcmToLines(questions)
    expect(lines[0]).toEqual({ type: "question", segments: [{ text: "1. Combien font 2+2 ?", bold: false }] })
    expect(lines[1]).toEqual({ type: "choice", correct: false, text: "3" })
    expect(lines[2]).toEqual({ type: "choice", correct: true, text: "4" })
    expect(lines[3]).toEqual({ type: "choice", correct: false, text: "5" })
    expect(lines[4]).toEqual({ type: "explication", segments: [{ text: "2+2 = 4", bold: false }] })
  })

  it("handles an empty question list", () => {
    expect(qcmToLines([])).toEqual([])
    expect(qcmToLines(undefined)).toEqual([])
  })
})
