/** Questions suggérées à partir du chapitre choisi. Vivait avant dans Sidebar.jsx ; déplacé ici
 * car les suggestions sont maintenant rendues dans WelcomeCard, pas dans la sidebar (voir
 * RAPPORT_MOBILE.md, §3/§4) — une seule fonction, partagée, plutôt que dupliquée. */
export function buildSuggestions(chapitre) {
  if (!chapitre) return []
  return [
    `Explique-moi simplement le chapitre "${chapitre}"`,
    `Donne-moi un exemple concret sur "${chapitre}"`,
    `Quelles sont les formules importantes de "${chapitre}" ?`,
    `Quelles erreurs faut-il éviter sur "${chapitre}" ?`,
  ]
}
