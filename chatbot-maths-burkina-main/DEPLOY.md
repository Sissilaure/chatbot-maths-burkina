# Déploiement de test — Railway (backend) + Cloudflare Pages (frontend)

Guide pour déployer une version de test accessible par lien, gratuitement (essai Railway de 30
jours / 5$ de crédit, Cloudflare Pages gratuit sans limite de temps).

Ce que Claude Code a préparé dans le repo : `backend/Dockerfile`, `backend/.dockerignore`. Les
étapes ci-dessous nécessitent tes propres comptes (Railway, Cloudflare) — impossibles à créer à ta
place.

## Pourquoi ces choix

- Railway a un vrai disque persistant (contrairement à Render en gratuit) : les comptes élèves ne
  sont pas perdus à chaque redémarrage.
- Le `Dockerfile` embarque directement `backend/data/documents` et `backend/data/chroma_db` tels
  qu'ils sont sur ton disque en ce moment (déjà indexés avec la classification de chapitres par
  contenu) — pas besoin de refaire les ~20-30 min de ré-indexation sur le serveur.
- Le disque persistant Railway ne sert qu'à la base SQLite des comptes élèves (`app.db`) : il est
  monté sur un sous-dossier dédié pour ne pas écraser les documents/index embarqués dans l'image.

## 1. Backend sur Railway

### Installer et se connecter

```bash
npm install -g @railway/cli
railway login
```

`railway login` ouvre le navigateur pour te connecter avec ton compte Railway (à créer sur
railway.app si tu n'en as pas).

### Créer le projet et déployer

Depuis le dossier `backend/` du projet (important : c'est ce dossier qui sera envoyé tel quel,
donc avec `data/documents` et `data/chroma_db` même s'ils sont dans `.gitignore` — Railway ne
passe pas par GitHub ici) :

```bash
cd backend
railway init
railway up
```

Le premier build prend plusieurs minutes (téléchargement de torch CPU + du modèle
d'embeddings). Les fois suivantes sont plus rapides.

### Ajouter un disque persistant

Dans le dashboard Railway (railway.app → ton projet → ton service) :
1. Clique droit sur le service → **Add Volume** (ou `⌘K` → "New Volume").
2. Monte-le sur `/app/data/db`.

### Variables d'environnement

Toujours dans le dashboard, onglet **Variables** :

| Variable | Valeur |
|---|---|
| `ANTHROPIC_API_KEY` | ta clé API Anthropic (celle de `backend/.env`) |
| `ANTHROPIC_MODEL` | `claude-sonnet-5` |
| `DB_PATH` | `/app/data/db/app.db` |
| `CORS_ORIGINS` | l'URL Cloudflare Pages du frontend (étape 2) — met une valeur temporaire du style `https://placeholder.pages.dev` pour l'instant, à corriger après |

`PORT` est injecté automatiquement par Railway, ne pas le définir toi-même.

### Récupérer l'URL publique

Dashboard → service → **Settings** → **Networking** → **Generate Domain**. Tu obtiens une URL du
style `https://ton-projet.up.railway.app`. Vérifie que ça répond :

```bash
curl https://ton-projet.up.railway.app/api/health
```

## 2. Frontend sur Cloudflare Pages

1. Va sur [pages.cloudflare.com](https://pages.cloudflare.com), connecte ton compte GitHub (ou
   crée un compte Cloudflare si besoin), et connecte le repo de ce projet.
2. Configuration du build :
   - **Dossier racine** : `frontend`
   - **Commande de build** : `npm run build`
   - **Dossier de sortie** : `dist`
3. Variable d'environnement à ajouter (**Settings → Environment variables**) :
   - `VITE_API_URL` = l'URL Railway obtenue à l'étape 1 (ex : `https://ton-projet.up.railway.app`)
4. Déploie. Tu obtiens une URL du style `https://ton-projet.pages.dev`.

## 3. Boucler la boucle : CORS

Retourne dans les variables Railway (étape 1) et remplace `CORS_ORIGINS` par l'URL Cloudflare
Pages réelle obtenue à l'étape 2 (ex : `https://ton-projet.pages.dev`). Ça redéploie
automatiquement le service.

## Vérifications avant de partager le lien

- [ ] `https://ton-projet.up.railway.app/api/health` répond `{"status":"healthy",...}`
- [ ] Le frontend Cloudflare Pages charge bien la liste des classes (preuve que l'appel API + CORS
      fonctionnent)
- [ ] Un nouveau visiteur (navigation privée) tombe bien sur la page de connexion
- [ ] Créer un compte de test, poser une question, générer un exercice, vérifier "voir le cours"
- [ ] Redémarrer le service Railway (Settings → Restart) puis vérifier que le compte de test créé
      juste avant existe toujours (preuve que le disque persistant fonctionne)

## Limites connues de ce déploiement de test

- **Essai Railway limité** : 30 jours ou 5$ de crédit consommé, selon ce qui arrive en premier.
  Au-delà, il faut passer sur un plan payant pour continuer à faire tourner le service en continu.
- **Premier chargement après une période creuse** : si Railway met le service en veille (dépend du
  plan), la première requête relance le modèle d'embeddings (~15-20s, déjà observé en local).
- **Documents ajoutés via l'upload admin après le déploiement** ne survivront pas à un redéploiement
  (ils ne sont écrits que dans la couche image, pas sur le volume persistant) — pour ajouter des
  documents durablement, il faut les remettre dans `backend/data/documents` en local et refaire
  `railway up`.
