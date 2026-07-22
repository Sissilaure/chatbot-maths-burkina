import { registerAccount, loginAccount, getMe } from "../api.js"

/**
 * Session de compte élève ou décideur (optionnelle) : le token JWT est stocké dans
 * localStorage et envoyé par les appels API protégés. Un invité n'a simplement pas de token.
 */
const TOKEN_KEY = "chatmaths-auth-token"
const USERNAME_KEY = "chatmaths-auth-username"
const ROLE_KEY = "chatmaths-auth-role"
export const AUTH_CHOICE_KEY = "chatmaths-auth-choice"

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || null
}

export function getStoredUsername() {
  return localStorage.getItem(USERNAME_KEY) || null
}

export function getStoredRole() {
  return localStorage.getItem(ROLE_KEY) || "eleve"
}

function storeSession(token, username, role) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USERNAME_KEY, username)
  localStorage.setItem(ROLE_KEY, role || "eleve")
  localStorage.setItem(AUTH_CHOICE_KEY, "authenticated")
}

export async function register(username, password) {
  const { token, username: confirmedUsername, role } = await registerAccount(username, password)
  storeSession(token, confirmedUsername, role)
  return { username: confirmedUsername, role }
}

export async function login(username, password) {
  const { token, username: confirmedUsername, role } = await loginAccount(username, password)
  storeSession(token, confirmedUsername, role)
  return { username: confirmedUsername, role }
}

export function logout() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USERNAME_KEY)
  localStorage.removeItem(ROLE_KEY)
}

/** Valide le token stocké auprès du backend ; retourne {username, role} ou null. */
export async function restoreSession() {
  const token = getToken()
  if (!token) return null
  try {
    const { username, role } = await getMe(token)
    localStorage.setItem(USERNAME_KEY, username)
    localStorage.setItem(ROLE_KEY, role || "eleve")
    return { username, role }
  } catch {
    logout()
    return null
  }
}
