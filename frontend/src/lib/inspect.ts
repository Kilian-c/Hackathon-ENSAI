/**
 * inspect.ts : l'inspecteur d'observation (cahier, fiche F.6). Fonctions pures, testées dans inspect.test.ts.
 *
 * Le moteur sert, pour les vues `inspect: true`, une série `inspect.<clé>` par grandeur de la méthode
 * principale, dans l'ordre de l'échantillon (points posés à la fin). La fiche n'affiche que ce qui est
 * fourni. Rien n'est propre à une expérience : le seuil de levier vaut 2 × la moyenne des leviers reçus
 * (leur somme est le nombre de coefficients p, donc c'est la règle usuelle 2p/n), le seuil de Cook 4 / n.
 */

import type { EngineState } from './types.gen'
import type { Series, ViewResult } from './views'

export const INSPECT_PREFIX = 'inspect.'

type Num = number | null

export function isInspectSeries(s: Pick<Series, 'slot'>): boolean {
  return s.slot.startsWith(INSPECT_PREFIX)
}

function seriesOf(view: ViewResult, key: string): Series | undefined {
  return view.series.find((s) => s.slot === INSPECT_PREFIX + key)
}

/** Nombre d'observations inspectables de la vue (0 : la vue ne s'inspecte pas). */
export function inspectableCount(view: ViewResult): number {
  return view.series.find(isInspectSeries)?.x?.length ?? 0
}

/** Abscisses des observations, communes à toutes les séries `inspect.*`. */
export function inspectX(view: ViewResult): readonly Num[] | null {
  return view.series.find(isInspectSeries)?.x ?? null
}

/**
 * La série dessinée porte-t-elle les observations de l'échantillon, dans le même ordre ? (nuage : les
 * données ; résidus : les résidus). La Référence est un autre échantillon : elle ne s'inspecte pas.
 */
export function isObservationSeries(view: ViewResult, s: Series): boolean {
  const x = inspectX(view)
  if (!x || isInspectSeries(s) || s.role === 'reference' || !s.x || !s.y) return false
  return s.x.length === x.length && s.x.every((v, i) => v === x[i])
}

export interface Inspection {
  /** Position dans l'échantillon, à partir de 0. */
  index: number
  total: number
  x: Num
  y: Num
  fitted: Num
  resid: Num
  /** Part de l'observation dans la somme des carrés des résidus (entre 0 et 1). */
  ssrShare: Num
  leverage: Num
  leverageLimit: Num
  highLeverage: boolean
  cooks: Num
  cooksLimit: Num
  influential: boolean
}

const finite = (v: Num | undefined): v is number => typeof v === 'number' && Number.isFinite(v)
const at = (s: Series | undefined, i: number): Num => {
  const v = s?.y?.[i]
  return finite(v) ? v : null
}

/** Fiche de l'observation `index`, ou null si la vue ne s'inspecte pas ou si l'indice n'existe plus. */
export function inspectionFor(view: ViewResult, index: number): Inspection | null {
  const total = inspectableCount(view)
  if (!Number.isInteger(index) || index < 0 || index >= total) return null
  const y = at(seriesOf(view, 'y'), index)
  const fitted = at(seriesOf(view, 'y_hat'), index)
  const residSeries = seriesOf(view, 'resid')
  const resid = at(residSeries, index) ?? (y !== null && fitted !== null ? y - fitted : null)

  const squares = (residSeries?.y ?? []).filter(finite).reduce((sum, e) => sum + e * e, 0)
  const ssrShare = resid !== null && squares > 0 ? (resid * resid) / squares : null

  const leverages = (seriesOf(view, 'leverage')?.y ?? []).filter(finite)
  const leverage = at(seriesOf(view, 'leverage'), index)
  const leverageLimit = leverages.length > 0 ? (2 * leverages.reduce((a, b) => a + b, 0)) / leverages.length : null

  const cooks = at(seriesOf(view, 'cooks_d'), index)
  const cooksLimit = seriesOf(view, 'cooks_d') ? 4 / total : null

  const xv = inspectX(view)?.[index]
  return {
    index,
    total,
    x: finite(xv) ? xv : null,
    y,
    fitted,
    resid,
    ssrShare,
    leverage,
    leverageLimit,
    highLeverage: leverage !== null && leverageLimit !== null && leverage > leverageLimit,
    cooks,
    cooksLimit,
    influential: cooks !== null && cooksLimit !== null && cooks > cooksLimit,
  }
}

// --- Clic : quel point est visé ? --------------------------------------------------------------------

/** Cible d'un clic : une observation de l'échantillon, ou un point posé (rang dans extra_points). */
export type PointTarget = { index: number } | { injected: number }

export interface Candidate {
  x: number
  y: number
  target: PointTarget
}

/**
 * Le point le plus proche du clic, à `radius` pixels au plus ; à égalité, le dernier de la liste (dessiné
 * par-dessus). Les triangles « hors cadre » sont posés sur le bord : leur moitié qui dépasse du cadre ne
 * déclenche aucun clic Plotly, d'où cette recherche.
 */
export function nearestTarget(
  candidates: readonly Candidate[],
  project: (x: number, y: number) => readonly [number, number],
  at: readonly [number, number],
  radius: number,
): PointTarget | null {
  let best: PointTarget | null = null
  let bestDistance = radius
  for (const c of candidates) {
    const [px, py] = project(c.x, c.y)
    const distance = Math.hypot(px - at[0], py - at[1])
    if (distance <= bestDistance) [best, bestDistance] = [c.target, distance]
  }
  return best
}

// --- Sélection : quel point est ouvert, et tient-il encore après un nouveau calcul ? ----------------------

export interface Selection {
  index: number
  /** Graine et taille de l'échantillon généré (sans les points posés) au moment du clic. */
  seed: number
  base: number
  /** Rang du point posé (dans EngineState.extra_points), null pour une observation générée. */
  injected: number | null
  /** Coordonnées du point posé, pour fermer la fiche s'il est retiré et qu'un autre prend son rang. */
  point: Record<string, number> | null
}

/** Les points posés sont les dernières observations : position du point posé de rang `rank`. */
export function injectedIndex(total: number, posed: number, rank: number): number {
  return total - posed + rank
}

/** Sélection de l'observation `index`, calculée à partir de l'état qui a produit la vue affichée. */
export function selectionFor(view: ViewResult, state: EngineState, index: number): Selection | null {
  const total = inspectableCount(view)
  if (index < 0 || index >= total) return null
  const base = total - state.extra_points.length
  const injected = index >= base ? index - base : null
  return {
    index,
    seed: state.seed,
    base,
    injected,
    point: injected === null ? null : { ...state.extra_points[injected] },
  }
}

/**
 * La fiche reste-t-elle valable ? Elle se ferme si le tirage ou la taille de l'échantillon changent (le
 * point i n'est plus le même), ou si le point posé a disparu. Une hypothèse ou un paramètre qui garde les
 * mêmes observations la met à jour. Une vue sans inspecteur ne ferme rien.
 */
export function selectionHolds(selection: Selection, view: ViewResult, state: EngineState): boolean {
  const total = inspectableCount(view)
  if (total === 0) return true
  if (state.seed !== selection.seed || total - state.extra_points.length !== selection.base) return false
  if (selection.index >= total) return false
  if (selection.injected === null) return true
  const now = state.extra_points[selection.injected]
  return !!now && JSON.stringify(now) === JSON.stringify(selection.point)
}
