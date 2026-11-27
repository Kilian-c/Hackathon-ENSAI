/**
 * share.ts : expériences importées (P1). Cahier, section 2.6 et annexe C ; table dans supabase/schema.sql.
 *
 * - Brouillon : le YAML en cours d'édition, gardé dans ce navigateur (localStorage). `?brouillon` l'ouvre
 *   dans le Laboratoire, sans rien enregistrer ailleurs.
 * - Partage : le YAML est enregistré une fois dans Supabase sous un identifiant aléatoire ; `?share=<id>`
 *   l'ouvre pour toute personne qui a le lien. Une ligne enregistrée ne change plus jamais.
 * - Clé d'import : `import-<16 premiers caractères du SHA-256 du contenu>`, la même que le moteur
 *   (backend/api/registry.py) : elle sert d'experiment_id pour lire la spécification et pour /api/sweep.
 *
 * Supabase est appelé par son API REST (pas de dépendance) : VITE_SUPABASE_URL et VITE_SUPABASE_ANON_KEY.
 */

const SUPABASE_URL: string = (import.meta.env.VITE_SUPABASE_URL ?? '').replace(/\/$/, '')
const SUPABASE_KEY: string = import.meta.env.VITE_SUPABASE_ANON_KEY ?? ''
const DRAFT_KEY = 'crash-test:import:brouillon'
const SCHEMA_VERSION = 1
const TIMEOUT_MS = 20_000

export class ShareError extends Error {
  constructor(message: string) {
    super(message)
    this.name = 'ShareError'
  }
}

export function sharingAvailable(): boolean {
  return SUPABASE_URL !== '' && SUPABASE_KEY !== ''
}

async function sha256Hex(text: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text))
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('')
}

export async function importKey(content: string): Promise<string> {
  return `import-${(await sha256Hex(content)).slice(0, 16)}`
}

/** Identifiant de partage : 12 caractères aléatoires (base64url), accepté par la table. */
export function newShareId(): string {
  const bytes = crypto.getRandomValues(new Uint8Array(9))
  return btoa(String.fromCharCode(...bytes)).replace(/\+/g, '-').replace(/\//g, '_')
}

export function isShareId(id: string): boolean {
  return /^[A-Za-z0-9_-]{10,32}$/.test(id)
}

// --- Brouillon local ---

export function saveDraft(content: string): void {
  try {
    localStorage.setItem(DRAFT_KEY, content)
  } catch {
    // Stockage plein ou interdit : le brouillon n'est simplement pas gardé.
  }
}

export function loadDraft(): string | null {
  try {
    return localStorage.getItem(DRAFT_KEY)
  } catch {
    return null
  }
}

// --- Supabase ---

async function supabase(path: string, body: unknown, prefer?: string): Promise<Response> {
  if (!sharingAvailable()) {
    throw new ShareError("Le partage n'est pas configuré sur cette installation (adresse Supabase absente).")
  }
  const headers: Record<string, string> = { apikey: SUPABASE_KEY, 'Content-Type': 'application/json' }
  // Ancienne clé « anon » (JWT) : aussi en Authorization. Nouvelle clé « sb_publishable_… » : apikey seul.
  if (SUPABASE_KEY.startsWith('eyJ')) headers.Authorization = `Bearer ${SUPABASE_KEY}`
  if (prefer) headers.Prefer = prefer
  try {
    return await fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
      method: 'POST',
      headers,
      body: JSON.stringify(body),
      signal: AbortSignal.timeout(TIMEOUT_MS),
    })
  } catch {
    throw new ShareError('Impossible de joindre le service de partage. Vérifiez votre connexion et réessayez.')
  }
}

/** Enregistre le YAML et renvoie son identifiant de partage. */
export async function saveShared(content: string): Promise<string> {
  const id = newShareId()
  const row = { id, schema_version: SCHEMA_VERSION, content, content_hash: await sha256Hex(content) }
  const res = await supabase('shared_experiments', row, 'return=minimal')
  if (!res.ok) {
    console.error('Supabase, enregistrement refusé', res.status, await res.text())
    throw new ShareError(`Le service de partage a refusé l'enregistrement (code ${res.status}).`)
  }
  return id
}

/** Lit un YAML partagé par son identifiant. */
export async function loadShared(id: string): Promise<string> {
  if (!isShareId(id)) throw new ShareError("Ce lien de partage n'est pas valable : son identifiant est mal formé.")
  const res = await supabase('rpc/get_shared_experiment', { p_id: id })
  if (!res.ok) {
    console.error('Supabase, lecture refusée', res.status, await res.text())
    throw new ShareError(`Le service de partage n'a pas répondu correctement (code ${res.status}).`)
  }
  const rows = (await res.json()) as { content: string; schema_version: number }[]
  const row = rows[0]
  if (!row) throw new ShareError("Aucune expérience ne correspond à ce lien. Vérifiez qu'il est complet.")
  if (row.schema_version !== SCHEMA_VERSION) {
    throw new ShareError(`Cette expérience a été partagée pour une autre version du format (${row.schema_version}).`)
  }
  return row.content
}

/** Adresse complète d'un lien de partage (à copier). */
export function shareUrl(id: string): string {
  return `${location.origin}${location.pathname}?share=${encodeURIComponent(id)}&v=1`
}
