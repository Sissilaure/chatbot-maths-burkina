import React, { useState } from "react"
import { motion } from "framer-motion"
import { ClipboardCheck, CheckCircle2, AlertTriangle } from "lucide-react"
import Card from "./ui/Card"
import Button from "./ui/Button"
import QcmQuestion from "./QcmQuestion"

const PASS_THRESHOLD = 0.8

export default function RemediationQuiz({ data, onSubmitResults }) {
  const questions = data?.questions || []
  const [answers, setAnswers] = useState({})
  const [submitted, setSubmitted] = useState(false)

  const allAnswered = questions.length > 0 && questions.every((_, i) => answers[i] !== undefined)
  const score = questions.reduce((acc, q, i) => acc + (answers[i] === q.reponse_correcte_index ? 1 : 0), 0)
  const ratio = questions.length > 0 ? score / questions.length : 0
  const passed = ratio >= PASS_THRESHOLD

  function handleValidate() {
    setSubmitted(true)
    onSubmitResults?.(
      questions.map((q, i) => ({ notion: q.notion, is_correct: answers[i] === q.reponse_correcte_index }))
    )
  }

  const notionsToReview = submitted
    ? Array.from(
        new Map(
          questions
            .map((q, i) => ({ q, correct: answers[i] === q.reponse_correcte_index }))
            .filter(({ correct }) => !correct)
            .map(({ q }) => [q.notion, q.conseil])
        ).entries()
      )
    : []

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
      <Card glow className="p-5">
        <div className="mb-3 flex items-center gap-2 text-primary">
          <ClipboardCheck size={18} />
          <span className="font-heading font-semibold">Remédiation — {data.chapter}</span>
        </div>
        <p className="mb-4 text-sm text-base-content/60">
          Réponds à ces {questions.length} questions pour vérifier que tu as bien compris le chapitre avant de continuer.
        </p>

        <div className="space-y-3">
          {questions.map((q, i) => (
            <QcmQuestion
              key={i}
              index={i}
              question={q.question}
              choices={q.choix}
              correctIndex={q.reponse_correcte_index}
              explication={q.explication}
              selected={answers[i]}
              onSelect={(choiceIndex) => !submitted && setAnswers((prev) => ({ ...prev, [i]: choiceIndex }))}
              revealed={submitted}
            />
          ))}
        </div>

        {!submitted ? (
          <Button variant="primary" size="md" className="mt-4" disabled={!allAnswered} onClick={handleValidate}>
            Valider mes réponses
          </Button>
        ) : (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            className={`mt-4 space-y-3 rounded-xl border p-4 ${
              passed ? "border-success/30 bg-success/5" : "border-warning/30 bg-warning/5"
            }`}
          >
            <div className={`flex items-center gap-2 font-semibold ${passed ? "text-success" : "text-warning"}`}>
              {passed ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
              Score : {score}/{questions.length} ({Math.round(ratio * 100)}%)
            </div>

            {passed ? (
              <p className="text-sm text-base-content/70">
                Tu as globalement compris le chapitre « {data.chapter} », tu peux continuer sereinement.
              </p>
            ) : (
              <div className="text-sm text-base-content/70">
                <p className="mb-2">Voici les notions à revoir avant de continuer :</p>
                <ul className="list-disc space-y-1 pl-5">
                  {notionsToReview.map(([notion, conseil]) => (
                    <li key={notion}>
                      <strong>{notion}</strong>
                      {conseil && <> — {conseil}</>}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </motion.div>
        )}
      </Card>
    </motion.div>
  )
}
