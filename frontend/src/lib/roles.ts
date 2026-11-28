/**
 * roles.ts : style de chaque rôle de série et de chaque verdict (R3).
 *
 * - Les COULEURS viennent de styles/tokens.css (seule source) : lues ici par cssVar().
 * - Le TRAIT, le MARQUEUR et le LIBELLÉ sont définis ici, car Plotly ne lit pas le CSS.
 * Jamais la couleur seule : chaque rôle a un trait et un marqueur distincts.
 */

import type { MeasureResult, MethodInfo, Series } from './types.gen'

/** Rôle d'affichage d'une série (cahier, annexe E) : celui que le moteur met dans Series.role. */
export type DisplayRole = Series['role']

/** Rôle d'une méthode tel que renvoyé par le moteur dans RunResult.methods[].role. */
export type MethodRole = MethodInfo['role']

/** Verdict d'une mesure, tel que renvoyé par le moteur. */
export type Verdict = MeasureResult['states'][string]

/** Valeurs de `line.dash` comprises par Plotly. */
type PlotlyDash = 'solid' | 'dash' | 'dot' | 'dashdot'

/** Symboles de marqueur Plotly utilisés par Crash-Test. */
type PlotlySymbol = 'circle' | 'diamond' | 'triangle-up' | 'square' | 'circle-open' | 'x' | 'star'

interface RoleSpec {
  label: string
  colorVar: string
  /** null : le rôle n'a pas de trait (points seuls). */
  dash: PlotlyDash | null
  width: number
  /** null : le rôle n'a pas de marqueur (courbe seule). */
  symbol: PlotlySymbol | null
}

const ROLE_SPECS: Record<DisplayRole, RoleSpec> = {
  method:        { label: 'Méthode',       colorVar: '--ct-role-method',        dash: 'solid',   width: 2,   symbol: 'circle' },
  correction:    { label: 'Correction',    colorVar: '--ct-role-correction',    dash: 'solid',   width: 3,   symbol: 'diamond' },
  alternative_1: { label: 'Alternative 1', colorVar: '--ct-role-alternative-1', dash: 'dashdot', width: 2,   symbol: 'triangle-up' },
  alternative_2: { label: 'Alternative 2', colorVar: '--ct-role-alternative-2', dash: 'dot',     width: 2,   symbol: 'square' },
  reference:     { label: 'Référence',     colorVar: '--ct-role-reference',     dash: 'dash',    width: 1.5, symbol: 'circle-open' },
  truth:         { label: 'Vraie valeur',  colorVar: '--ct-role-truth',         dash: 'solid',   width: 1,   symbol: null },
  rupture:       { label: 'Rupture',       colorVar: '--ct-role-rupture',       dash: 'solid',   width: 2,   symbol: 'x' },
  injected:      { label: 'Point ajouté',  colorVar: '--ct-role-injected',      dash: null,      width: 0,   symbol: 'star' },
  data:          { label: 'Observations',  colorVar: '--ct-plot-data',          dash: null,      width: 0,   symbol: 'circle' },
}

interface VerdictSpec {
  label: string
  /** Icône affichée avec le mot : le verdict reste lisible sans la couleur. */
  icon: string
  colorVar: string
}

const VERDICT_SPECS: Record<Verdict, VerdictSpec> = {
  ok:      { label: 'Fiable',  icon: '✓', colorVar: '--ct-verdict-ok' },
  warning: { label: 'Fragile', icon: '!', colorVar: '--ct-verdict-warning' },
  broken:  { label: 'Rompu',   icon: '✕', colorVar: '--ct-verdict-broken' },
}

// --- Lecture des couleurs dans tokens.css ---

import { theme } from './theme.svelte'

const cache = new Map<string, string>()

/** Valeur d'une variable CSS de tokens.css (ex. cssVar('--ct-role-method') -> '#4ea1ff'). */
export function cssVar(name: string): string {
  // Lu à chaque appel : un graphique ou une équation qui appelle cssVar se redessine quand le thème change.
  const key = `${theme.resolved}|${name}`
  const hit = cache.get(key)
  if (hit) return hit
  // Hors navigateur (tests unitaires) : on renvoie le nom de la variable, sans mise en cache.
  if (typeof document === 'undefined') return `var(${name})`
  const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim()
  if (!value) {
    // Variable absente : tokens.css n'est pas chargé ou le nom est faux. On le dit fort en développement.
    if (import.meta.env.DEV) console.error(`Variable CSS introuvable : ${name} (voir styles/tokens.css)`)
    return '#ff00ff'
  }
  cache.set(key, value)
  return value
}

/** À appeler si le thème change (ex. passage en impression) : les couleurs seront relues. */
export function clearColorCache(): void {
  cache.clear()
}

// --- Rôles ---

export function roleLabel(role: DisplayRole): string {
  return ROLE_SPECS[role].label
}

export function roleColor(role: DisplayRole): string {
  return cssVar(ROLE_SPECS[role].colorVar)
}

/** Nom de la variable CSS d'un rôle, pour les composants (style="color: var(...)"). */
export function roleColorVar(role: DisplayRole): string {
  return `var(${ROLE_SPECS[role].colorVar})`
}

/**
 * Style Plotly d'une série selon son rôle : à fusionner dans la trace.
 * `mode` indique ce que la vue dessine : lignes, points, ou les deux.
 */
export function plotlyStyle(
  role: DisplayRole,
  mode: 'lines' | 'markers' | 'lines+markers' = 'lines',
): { mode: string; line?: object; marker?: object } {
  const spec = ROLE_SPECS[role]
  const color = roleColor(role)
  const wantsLine = mode !== 'markers' && spec.dash !== null
  const wantsMarker = mode !== 'lines' && spec.symbol !== null
  // Un rôle sans trait (point ajouté) reste en points, un rôle sans marqueur (vraie valeur) reste en ligne.
  const finalMode = wantsLine && wantsMarker ? 'lines+markers' : wantsLine ? 'lines' : 'markers'
  return {
    mode: finalMode,
    ...(wantsLine && { line: { color, dash: spec.dash, width: spec.width } }),
    ...((wantsMarker || !wantsLine) && {
      marker: {
        color,
        symbol: spec.symbol ?? 'circle',
        size: role === 'injected' ? 12 : 7,
        line: { color, width: 1 },
      },
    }),
  }
}

/**
 * Rôle d'affichage de chaque méthode : les alternatives reçoivent alternative_1 puis
 * alternative_2 dans l'ordre du YAML (qui est l'ordre de RunResult.methods).
 */
export function displayRoles(
  methods: ReadonlyArray<{ id: string; role: MethodRole }>,
): Record<string, DisplayRole> {
  const out: Record<string, DisplayRole> = {}
  let alt = 0
  for (const m of methods) {
    if (m.role === 'alternative') {
      alt += 1
      out[m.id] = alt === 1 ? 'alternative_1' : 'alternative_2'
    } else {
      out[m.id] = m.role
    }
  }
  return out
}

// --- Verdicts ---

export function verdictLabel(v: Verdict): string {
  return VERDICT_SPECS[v].label
}

export function verdictIcon(v: Verdict): string {
  return VERDICT_SPECS[v].icon
}

export function verdictColor(v: Verdict): string {
  return cssVar(VERDICT_SPECS[v].colorVar)
}

export function verdictColorVar(v: Verdict): string {
  return `var(${VERDICT_SPECS[v].colorVar})`
}

/** Liste des rôles, dans l'ordre de la légende. */
export const ALL_ROLES = Object.keys(ROLE_SPECS) as DisplayRole[]
