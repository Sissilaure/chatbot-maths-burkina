import React, { useState } from "react"
import { motion } from "framer-motion"
import { PencilRuler, Lightbulb, Eye, EyeOff, Sparkles, Star } from "lucide-react"
import Card from "./ui/Card"
import Button from "./ui/Button"
import Badge from "./ui/Badge"
import MathContent from "./MathContent"
import GeometryFigure from "./GeometryFigure"
import QcmQuestion from "./QcmQuestion"

const STAR_LABELS = {
  1: "QCM d'application",
  2: "Application guidée",
  3: "Notions combinées",
  4: "Situation d'intégration",
}

function StarRating({ level }) {
  return (
    <span className="inline-flex items-center gap-0.5">
      {[1, 2, 3, 4].map((i) => (
        <Star key={i} size={12} className={i <= level ? "fill-primary text-primary" : "text-base-content/25"} />
      ))}
    </span>
  )
}

export default function ExerciseCard({ exercise }) {
  const [indiceShown, setIndiceShown] = useState(false)
  const [solutionShown, setSolutionShown] = useState(false)
  const [qcmAnswers, setQcmAnswers] = useState({})

  const isQcm = Array.isArray(exercise.qcm) && exercise.qcm.length > 0
  const allAnswered = isQcm && exercise.qcm.every((_, i) => qcmAnswers[i] !== undefined)
  const qcmScore = isQcm
    ? exercise.qcm.reduce((acc, q, i) => acc + (qcmAnswers[i] === q.reponse_correcte_index ? 1 : 0), 0)
    : 0

  return (
    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }}>
      <Card glow className="p-5">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-primary">
            <PencilRuler size={18} />
            <span className="font-heading font-semibold">Exercice — {exercise.chapter}</span>
          </div>
          <div className="flex items-center gap-2">
            <Badge variant="neutral">{exercise.class_level}</Badge>
            <Badge variant="primary" title={STAR_LABELS[exercise.difficulty] || ""}>
              <StarRating level={exercise.difficulty} />
            </Badge>
          </div>
        </div>

        <div className="prose-chat max-w-none rounded-xl bg-gradient-to-br from-primary/5 to-secondary/5 p-4">
          <MathContent>{exercise.enonce}</MathContent>
          {exercise.figure && <GeometryFigure spec={exercise.figure} />}
        </div>

        {isQcm ? (
          <div className="mt-4 space-y-3">
            {exercise.qcm.map((q, i) => (
              <QcmQuestion
                key={i}
                index={i}
                question={q.question}
                choices={q.choix}
                correctIndex={q.reponse_correcte_index}
                explication={q.explication}
                selected={qcmAnswers[i]}
                onSelect={(choiceIndex) => setQcmAnswers((prev) => ({ ...prev, [i]: choiceIndex }))}
                revealed={qcmAnswers[i] !== undefined}
              />
            ))}
            {allAnswered && (
              <div className="rounded-xl border border-primary/30 bg-primary/5 px-4 py-2.5 text-sm font-semibold text-primary">
                Score : {qcmScore}/{exercise.qcm.length} bonnes réponses
              </div>
            )}
          </div>
        ) : (
          <>
            {exercise.indices?.length > 0 && (
              <div className="mt-3 space-y-2">
                {indiceShown && (
                  <div className="prose-chat max-w-none rounded-xl border border-warning/30 bg-warning/5 p-3">
                    <span className="mr-1 font-semibold text-warning">Indice :</span>
                    <MathContent>{exercise.indices[0]}</MathContent>
                  </div>
                )}
                <Button variant="soft" size="sm" onClick={() => setIndiceShown((s) => !s)}>
                  <Lightbulb size={14} /> {indiceShown ? "Masquer l'indice" : "Voir l'indice"}
                </Button>
              </div>
            )}

            <div className="mt-4">
              <Button variant={solutionShown ? "outline" : "primary"} size="sm" onClick={() => setSolutionShown((s) => !s)}>
                {solutionShown ? <EyeOff size={14} /> : <Eye size={14} />}
                {solutionShown ? "Masquer la solution" : "Voir la solution détaillée"}
              </Button>

              {solutionShown && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  className="prose-chat mt-3 max-w-none space-y-2 overflow-hidden rounded-xl border border-success/30 bg-success/5 p-4"
                >
                  <MathContent>{exercise.solution}</MathContent>
                  {exercise.reponse_finale && (
                    <div className="mt-2 flex items-center gap-2 rounded-lg bg-success/15 px-3 py-2 font-semibold text-success">
                      <Sparkles size={14} />
                      <MathContent>{exercise.reponse_finale}</MathContent>
                    </div>
                  )}
                </motion.div>
              )}
            </div>
          </>
        )}
      </Card>
    </motion.div>
  )
}
