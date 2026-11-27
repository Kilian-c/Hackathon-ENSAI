/**
 * views.ts : format des vues reçues du moteur, tel que l'interface l'attend (R3).
 *
 * PROPOSITION PROVISOIRE, à aligner avec R1 dans backend/contracts.py (cahier, annexe E).
 * TODO(passation) : remplacer ces types par ceux de types.gen.ts dès qu'il existe.
 *
 * Principe : le moteur résout les `bind` du YAML et renvoie une liste plate de séries prêtes
 * à dessiner. Chaque série dit à quel emplacement (`slot`) elle correspond, de quelle méthode
 * elle vient et quel rôle elle joue. L'interface ne connaît aucun nom de clé propre à un théorème.
 */

import type { MethodRole, Verdict } from './roles'

export type Num = number | null
export type Range = [number, number]

export type ViewType =
  | 'scatter'
  | 'residuals'
  | 'repetitions'
  | 'distribution'
  | 'curves'
  | 'sensitivity'
  | 'validity_domain'
  | 'surface_3d'
  | 'vector_space'
  | 'measures_table'

/**
 * Rôle d'une série : celui de sa méthode, ou bien
 * - reference : même série calculée à l'état sain (Référence, en pointillés) ;
 * - truth     : vraie valeur, solution exacte (générateur) ;
 * - data      : données du générateur, communes à toutes les méthodes (nuage de points).
 */
export type SeriesRole = MethodRole | 'reference' | 'truth' | 'data'

export interface ViewSeries {
  /** Identifiant stable `<vue>.<emplacement>.<methode>` : Plotly s'en sert pour animer proprement. */
  id: string
  /** Emplacement du `bind` (x/y, fit, resid, est, stat, series, truth...). */
  slot: string
  /** Méthode d'origine ; null pour les données du générateur. */
  method: string | null
  role: SeriesRole
  label: string
  /** Calque pas à pas (P2), null sinon. */
  layer?: string | null
  x?: Num[]
  y?: Num[]
  /** Vue Répétitions (intervalles) : bornes et succès par répétition ; `x` porte l'estimation. */
  low?: Num[]
  high?: Num[]
  hit?: boolean[]
  /** Valeur scalaire (vraie valeur d'un paramètre, seuil). */
  value?: Num
}

export interface ViewData {
  id: string
  type: ViewType
  title: string
  /** Vue Répétitions : intervalles ou trajectoires. */
  mode?: 'intervals' | 'paths'
  /** Bornes calculées sur la Référence ; null = automatique. */
  axes: { x?: Range | null; y?: Range | null }
  /** Nombre d'éléments affichés et calculés (100 intervalles sur 500 répétitions). */
  shown: number
  total: number
  clipped: number
  ui?: Record<string, unknown>
  series: ViewSeries[]
}

/** Résultat d'un balayage (POST /api/sweep), pour la vue Sensibilité. Champs : CLAUDE.md, section 8. */
export interface SweepData {
  axes: { target: string; values: (number | string | boolean)[]; labels: string[] }[]
  measure: string
  values: Record<string, Num[]>
  mc_se: Record<string, Num[] | null>
  states: Record<string, (Verdict | null)[]>
  critical: Record<string, { warning_at: Num; broken_at: Num } | null>
  target: Num
  ok_within: Num
  broken_beyond: Num
  direction: 'below' | 'above' | 'both' | null
  current: Record<string, unknown>
}

/** Mise en forme d'une mesure (vient de RunResult.measures.<id>). */
export interface MeasureFormat {
  label: string
  unit?: string
  scale?: number
  decimals?: number
}
