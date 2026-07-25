/**
 * Modèle intermédiaire, pur (aucune dépendance à la librairie `docx`), entre le texte Markdown/
 * les données de l'application et les primitives Word. Séparé de `docx.js` exprès : la librairie
 * `docx` construit des arbres XML internes non introspectables simplement (voir `TextRun`), donc
 * toute la logique de découpage/interprétation vit ici, testable sans avoir à générer un vrai
 * document Word.
 */

export function stripFigureBlocks(text) {
  return (text || "").replace(/```figure[\s\S]*?```/g, "\n[Figure géométrique — voir dans l'application]\n")
}

/** Découpe une ligne en segments {text, bold}, sur la syntaxe Markdown **gras**. */
export function splitBoldSegments(line) {
  return line
    .split(/(\*\*[^*]+\*\*)/g)
    .filter((part) => part.length > 0)
    .map((part) => {
      const isBold = part.startsWith("**") && part.endsWith("**")
      return { text: isBold ? part.slice(2, -2) : part, bold: isBold }
    })
}

/**
 * Convertit un texte Markdown en une liste de lignes typées : {type: "blank"|"heading2"|
 * "heading3"|"bullet"|"text", segments: [{text, bold}, ...]}. Les blocs ```figure``` sont
 * remplacés par une mention textuelle (pas d'équivalent image natif dans Word).
 */
export function parseMarkdownLines(rawText) {
  const lines = stripFigureBlocks(rawText).split("\n")
  return lines.map((rawLine) => {
    const line = rawLine.trimEnd()
    if (!line.trim()) return { type: "blank", segments: [] }

    const h2 = line.match(/^##\s+(.*)/)
    if (h2) return { type: "heading2", segments: splitBoldSegments(h2[1]) }

    const h3 = line.match(/^###\s+(.*)/)
    if (h3) return { type: "heading3", segments: splitBoldSegments(h3[1]) }

    const bullet = line.match(/^[-*]\s+(.*)/)
    if (bullet) return { type: "bullet", segments: splitBoldSegments(bullet[1]) }

    return { type: "text", segments: splitBoldSegments(line) }
  })
}

/**
 * Convertit une liste de questions QCM (voir generate_remediation/generate_exercise côté backend :
 * {question, choix[], reponse_correcte_index, explication}) en lignes typées pour l'export Word.
 */
export function qcmToLines(questions) {
  const lines = []
  ;(questions || []).forEach((q, i) => {
    lines.push({ type: "question", segments: splitBoldSegments(`${i + 1}. ${q.question || ""}`) })
    ;(q.choix || []).forEach((choice, ci) => {
      lines.push({ type: "choice", correct: ci === q.reponse_correcte_index, text: choice })
    })
    if (q.explication) {
      lines.push({ type: "explication", segments: splitBoldSegments(q.explication) })
    }
  })
  return lines
}
