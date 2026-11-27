/**
 * views.ts : lecture des vues du moteur (R3).
 *
 * Les TYPES viennent de types.gen.ts (générés depuis backend/contracts.py) : ViewResult, Series,
 * SweepResult... Ce fichier ajoute des accès tolérants aux valeurs absentes (NaN et Infinity
 * arrivent en null) et quelques règles de lecture communes à toutes les vues.
 *
 * Données d'une série (contrat, `Series`) :
 * - points ou ligne (nuage, résidus, courbes) : x, y
 * - intervalles (Répétitions, mode « intervals ») : x (estimation), low, high, hit
 * - distribution : x (valeurs à mettre en histogramme)
 * - valeur scalaire (vraie valeur, seuil) : value
 * - trajectoires (Répétitions, mode « paths ») : paths
 * - matrice (vue heatmap) : paths, une liste par ligne (paths[i][j] = coefficient (i + 1, j + 1))
 */

import type { MeasureResult, Series, SweepResult, ViewResult } from './types.gen'

export type { Series, SweepResult, ViewResult }

export type Num = number | null
export type Range = [number, number]

/** Mise en forme d'une mesure (sous-ensemble de RunResult.measures.<id>). */
export type MeasureFormat = Pick<MeasureResult, 'label'> & Partial<Pick<MeasureResult, 'unit' | 'scale' | 'decimals'>>

type NumKey = 'x' | 'y' | 'low' | 'high'

/** Tableau numérique d'une série (null pour les valeurs absentes ou non finies). */
export function nums(s: Series, key: NumKey): Num[] {
  return (s[key] ?? []).map((v) => (typeof v === 'number' && Number.isFinite(v) ? v : null))
}

/** Succès par répétition (intervalles). */
export function bools(s: Series): boolean[] {
  return (s.hit ?? []).map((v) => v === true)
}

/** Valeur scalaire d'une série, ou null. */
export function scalar(s: Series): Num {
  return typeof s.value === 'number' && Number.isFinite(s.value) ? s.value : null
}

/** Bornes [min, max] d'un axe de la vue, ou null (automatique). */
export function axisRange(view: ViewResult, axis: 'x' | 'y'): Range | null {
  const r = view.axes?.[axis]
  return r && r.length === 2 ? [r[0], r[1]] : null
}

/** Données du générateur (nuage d'observations), communes à toutes les méthodes : style neutre. */
export function isGeneratorData(s: Series): boolean {
  return s.role === 'data'
}
