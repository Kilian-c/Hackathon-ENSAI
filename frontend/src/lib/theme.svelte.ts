/**
 * theme.svelte.ts : thème de l'interface (clair, sombre ou automatique), choisi par le bouton du pied de page.
 *
 * - Le choix (« auto », « light », « dark ») est gardé dans ce navigateur (localStorage, confort seulement).
 * - Le thème appliqué est posé sur <html data-theme="light|dark"> : les couleurs de styles/tokens.css suivent.
 * - « auto » suit le réglage du système, y compris s'il change pendant que la page est ouverte.
 * - `theme.resolved` est réactif : cssVar (lib/roles.ts) le lit, donc les graphiques Plotly et l'équation,
 *   qui lisent leurs couleurs en JavaScript, se redessinent au changement de thème.
 * index.html applique déjà le thème avant l'affichage (même clé, même règle) pour éviter un flash sombre.
 */

export type ThemePreference = 'auto' | 'light' | 'dark'
export type ResolvedTheme = 'light' | 'dark'

export const THEME_KEY = 'crash-test.theme'

export const THEME_CHOICES: readonly { id: ThemePreference; label: string; icon: string }[] = [
  { id: 'auto', label: 'Auto', icon: '◐' },
  { id: 'light', label: 'Clair', icon: '☀' },
  { id: 'dark', label: 'Sombre', icon: '☾' },
]

/** Valeur lue dans le navigateur : toute autre chose qu'un choix connu vaut « auto ». */
export function parsePreference(raw: string | null | undefined): ThemePreference {
  return raw === 'light' || raw === 'dark' ? raw : 'auto'
}

/** Thème appliqué : le choix explicite, sinon celui du système. */
export function resolveTheme(pref: ThemePreference, systemPrefersLight: boolean): ResolvedTheme {
  if (pref === 'auto') return systemPrefersLight ? 'light' : 'dark'
  return pref
}

function readPreference(): ThemePreference {
  try {
    return parsePreference(globalThis.localStorage?.getItem(THEME_KEY))
  } catch {
    return 'auto'
  }
}

function lightQuery(): MediaQueryList | null {
  try {
    return typeof matchMedia === 'function' ? matchMedia('(prefers-color-scheme: light)') : null
  } catch {
    return null
  }
}

interface ThemeState {
  preference: ThemePreference
  resolved: ResolvedTheme
}

function createState(): ThemeState {
  const state = $state<ThemeState>({ preference: 'auto', resolved: 'dark' })
  return state
}

// Un seul état par page, même si ce module est chargé deux fois : le serveur de développement le fait après
// certaines mises à jour à chaud (changement de branche). Le bouton changeait alors une copie, et les
// graphiques, qui lisaient l'autre, gardaient leurs anciennes couleurs.
const page = globalThis as typeof globalThis & { __crashTestTheme?: { state: ThemeState; started: boolean } }
const shared = (page.__crashTestTheme ??= { state: createState(), started: false })

export const theme = shared.state

function apply(): void {
  theme.resolved = resolveTheme(theme.preference, lightQuery()?.matches ?? false)
  if (typeof document !== 'undefined') document.documentElement.dataset.theme = theme.resolved
}

/** Choix de l'utilisateur : appliqué tout de suite et gardé pour les prochaines visites. */
export function setTheme(pref: ThemePreference): void {
  theme.preference = pref
  try {
    globalThis.localStorage?.setItem(THEME_KEY, pref)
  } catch {
    /* stockage refusé : le choix vaut pour cette visite seulement */
  }
  apply()
}

/** À appeler une fois au démarrage (main.ts). */
export function initTheme(): void {
  if (shared.started) return
  shared.started = true
  theme.preference = readPreference()
  apply()
  lightQuery()?.addEventListener('change', () => {
    if (theme.preference === 'auto') apply()
  })
}
