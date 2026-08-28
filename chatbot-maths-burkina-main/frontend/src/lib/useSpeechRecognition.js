import { useCallback, useEffect, useRef, useState } from "react"

const SpeechRecognitionImpl =
  typeof window !== "undefined" ? window.SpeechRecognition || window.webkitSpeechRecognition : null

/** Dictée vocale via l'API Web Speech du navigateur (aucun appel serveur : la transcription se
 * fait côté navigateur/OS, voir la discussion avec l'utilisateur sur les options possibles).
 * Absente de Firefox et capricieuse sur Safari — `supported` permet de masquer le bouton micro
 * plutôt que d'afficher une fonctionnalité cassée. `start(baseText)` reprend le texte déjà présent
 * dans le champ pour que la dictée s'ajoute à la suite plutôt que de l'écraser. */
export function useSpeechRecognition({ onResult, onError, lang = "fr-FR" } = {}) {
  const [listening, setListening] = useState(false)
  const recognitionRef = useRef(null)
  const baseTextRef = useRef("")

  const start = useCallback(
    (currentText = "") => {
      if (!SpeechRecognitionImpl || recognitionRef.current) return

      const recognition = new SpeechRecognitionImpl()
      recognition.lang = lang
      recognition.continuous = true
      recognition.interimResults = true

      baseTextRef.current = currentText && !currentText.endsWith(" ") ? `${currentText} ` : currentText

      recognition.onresult = (event) => {
        let interim = ""
        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript
          if (event.results[i].isFinal) {
            baseTextRef.current += `${transcript} `
          } else {
            interim += transcript
          }
        }
        onResult?.(baseTextRef.current + interim)
      }

      recognition.onerror = (event) => {
        onError?.(event.error)
      }

      recognition.onend = () => {
        recognitionRef.current = null
        setListening(false)
      }

      recognitionRef.current = recognition
      recognition.start()
      setListening(true)
    },
    [lang, onResult, onError]
  )

  const stop = useCallback(() => {
    recognitionRef.current?.stop()
  }, [])

  useEffect(() => () => recognitionRef.current?.stop(), [])

  return { supported: Boolean(SpeechRecognitionImpl), listening, start, stop }
}
