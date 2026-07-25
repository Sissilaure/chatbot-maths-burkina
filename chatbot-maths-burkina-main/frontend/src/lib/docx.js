/**
 * Exporte la conversation en document Word (.docx), à partir des données des messages
 * (pas d'une capture d'écran comme pour le PDF) : un fichier Word attend du texte réel,
 * sélectionnable et modifiable, pas une image.
 *
 * Limite connue : les formules LaTeX ($...$) et les figures géométriques (blocs ```figure```)
 * ne sont pas des images natives dans Word — le LaTeX apparaît en texte source, et une figure
 * est remplacée par une mention indiquant de la consulter dans l'application.
 *
 * docx est chargé à la demande (dynamic import) pour ne pas alourdir le bundle principal. La
 * logique de découpage Markdown/QCM vit dans docxModel.js (pure, testable sans la librairie docx
 * — voir docxModel.test.js) ; ce fichier se contente de traduire ce modèle en primitives Word.
 */
import { parseMarkdownLines, qcmToLines, splitBoldSegments } from "./docxModel.js"

function segmentsToRuns(TextRun, segments, extraProps = {}) {
  return segments.map(({ text, bold }) => new TextRun({ text, bold, ...extraProps }))
}

function linesToParagraphs(docxLib, lines) {
  const { Paragraph, HeadingLevel, TextRun } = docxLib
  return lines.map((line) => {
    switch (line.type) {
      case "blank":
        return new Paragraph({ text: "" })
      case "heading2":
        return new Paragraph({ children: segmentsToRuns(TextRun, line.segments), heading: HeadingLevel.HEADING_2, spacing: { before: 200, after: 100 } })
      case "heading3":
        return new Paragraph({ children: segmentsToRuns(TextRun, line.segments), heading: HeadingLevel.HEADING_3, spacing: { before: 150, after: 80 } })
      case "bullet":
        return new Paragraph({ children: segmentsToRuns(TextRun, line.segments), bullet: { level: 0 } })
      default:
        return new Paragraph({ children: segmentsToRuns(TextRun, line.segments), spacing: { after: 120 } })
    }
  })
}

function markdownToParagraphs(docxLib, rawText) {
  return linesToParagraphs(docxLib, parseMarkdownLines(rawText))
}

function qcmParagraphs(docxLib, questions) {
  const { Paragraph, TextRun } = docxLib
  return qcmToLines(questions).map((line) => {
    if (line.type === "choice") {
      return new Paragraph({
        children: [new TextRun({ text: `${line.correct ? "✓ " : "– "}${line.text}`, bold: line.correct })],
        indent: { left: 300 },
      })
    }
    if (line.type === "explication") {
      return new Paragraph({
        children: [new TextRun({ text: "Explication : ", italics: true }), ...segmentsToRuns(TextRun, line.segments)],
        spacing: { after: 100 },
      })
    }
    // "question"
    return new Paragraph({ children: segmentsToRuns(TextRun, line.segments), spacing: { before: 140 } })
  })
}

export async function exportMessagesToDocx(messages, { filename = "chatmaths.docx", title = "", subtitle = "" } = {}) {
  const docxLib = await import("docx")
  const { Document, Packer, Paragraph, TextRun, HeadingLevel } = docxLib

  const children = []
  if (title) children.push(new Paragraph({ text: title, heading: HeadingLevel.TITLE }))
  if (subtitle) children.push(new Paragraph({ children: [new TextRun({ text: subtitle, color: "64748B" })], spacing: { after: 300 } }))

  for (const msg of messages) {
    if (msg.type === "user") {
      children.push(
        new Paragraph({ children: [new TextRun({ text: "Élève", bold: true, color: "0D9488" })], spacing: { before: 240, after: 60 } })
      )
      children.push(...markdownToParagraphs(docxLib, msg.text))
    } else if (msg.type === "bot") {
      children.push(
        new Paragraph({ children: [new TextRun({ text: "Prof Amira", bold: true, color: "9333EA" })], spacing: { before: 120, after: 60 } })
      )
      children.push(...markdownToParagraphs(docxLib, msg.text))
    } else if (msg.type === "exercise") {
      const ex = msg.data || {}
      children.push(
        new Paragraph({ text: `Exercice — ${ex.chapter || ""}`, heading: HeadingLevel.HEADING_2, spacing: { before: 240, after: 100 } })
      )
      children.push(...markdownToParagraphs(docxLib, ex.enonce))
      if (Array.isArray(ex.qcm) && ex.qcm.length > 0) {
        children.push(...qcmParagraphs(docxLib, ex.qcm))
      } else {
        if (ex.indices?.length > 0) {
          children.push(new Paragraph({ children: [new TextRun({ text: "Indice", bold: true })], spacing: { before: 100 } }))
          children.push(...markdownToParagraphs(docxLib, ex.indices[0]))
        }
        children.push(new Paragraph({ children: [new TextRun({ text: "Solution", bold: true })], spacing: { before: 100 } }))
        children.push(...markdownToParagraphs(docxLib, ex.solution))
        if (ex.reponse_finale) {
          children.push(
            new Paragraph({
              children: [new TextRun({ text: "Réponse finale : ", bold: true }), ...segmentsToRuns(TextRun, splitBoldSegments(ex.reponse_finale))],
              spacing: { before: 80 },
            })
          )
        }
      }
    } else if (msg.type === "remediation") {
      children.push(new Paragraph({ text: "QCM de remédiation", heading: HeadingLevel.HEADING_2, spacing: { before: 240, after: 100 } }))
      children.push(...qcmParagraphs(docxLib, msg.data?.questions || []))
    }
  }

  const doc = new Document({
    title: title || "Session ChatMaths Burkina",
    description: "Export de conversation — ChatMaths Burkina",
    sections: [{ children }],
  })

  const blob = await Packer.toBlob(doc)
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}
